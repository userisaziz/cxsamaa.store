"""Cloudflare R2 storage backend using boto3 (S3-compatible API).

R2 provides S3-compatible object storage with no egress fees.
This backend uses boto3 with a custom endpoint URL pointing to R2.
"""
import logging
from io import BytesIO

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from src.config import settings
from src.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class R2Storage(StorageBackend):
    """Cloudflare R2 storage backend."""

    def __init__(self):
        self.bucket = settings.r2_bucket
        self.public_url = settings.r2_public_url.rstrip("/") if settings.r2_public_url else None

        # R2 uses S3-compatible API with a custom endpoint
        endpoint_url = (
            f"https://{settings.r2_account_id}.r2.cloudflarestorage.com"
        )

        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",  # R2 uses "auto" as region
            config=BotoConfig(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=10,
                read_timeout=60,
            ),
        )

    # --- Async methods (used by FastAPI) ---

    async def upload(self, file_data: bytes, destination: str) -> str:
        return self.upload_sync(file_data, destination)

    async def download(self, source: str) -> bytes:
        return self.download_sync(source)

    async def delete(self, path: str) -> None:
        self.delete_sync(path)

    async def get_signed_url(self, path: str, expires_in: int = 900) -> str:
        """Generate a pre-signed URL for temporary access."""
        if self.public_url:
            # If bucket has public access, return direct URL
            return f"{self.public_url}/{path}"

        # Generate pre-signed URL for private buckets
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": path},
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            logger.error("Failed to generate signed URL for %s: %s", path, e)
            raise

    # --- Sync methods (used by Celery workers) ---

    def upload_sync(self, file_data: bytes, destination: str) -> str:
        """Upload file to R2 and return the storage key."""
        try:
            # Guess content type from extension
            content_type = self._guess_content_type(destination)

            self.client.put_object(
                Bucket=self.bucket,
                Key=destination,
                Body=file_data,
                ContentType=content_type,
            )

            logger.info("Uploaded %d bytes to R2: %s", len(file_data), destination)

            # Return the storage key (not a URL)
            return destination

        except ClientError as e:
            logger.error("Failed to upload to R2 %s: %s", destination, e)
            raise

    def download_sync(self, source: str) -> bytes:
        """Download file from R2 and return bytes."""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=source)
            data = response["Body"].read()
            logger.debug("Downloaded %d bytes from R2: %s", len(data), source)
            return data

        except ClientError as e:
            logger.error("Failed to download from R2 %s: %s", source, e)
            raise

    def delete_sync(self, path: str) -> None:
        """Delete file from R2."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=path)
            logger.info("Deleted from R2: %s", path)

        except ClientError as e:
            logger.warning("Failed to delete from R2 %s: %s", path, e)
            # Don't raise — delete is idempotent, log and continue

    def get_signed_url_sync(self, path: str, expires_in: int = 900) -> str:
        """Sync variant of get_signed_url for Celery workers."""
        if self.public_url:
            return f"{self.public_url}/{path}"

        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": path},
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            logger.error("Failed to generate signed URL for %s: %s", path, e)
            raise

    # --- Helpers ---

    def _guess_content_type(self, key: str) -> str:
        """Guess content type from file extension."""
        ext = key.rsplit(".", 1)[-1].lower() if "." in key else ""
        content_types = {
            "wav": "audio/wav",
            "mp3": "audio/mpeg",
            "m4a": "audio/mp4",
            "ogg": "audio/ogg",
            "flac": "audio/flac",
            "json": "application/json",
            "txt": "text/plain",
        }
        return content_types.get(ext, "application/octet-stream")
