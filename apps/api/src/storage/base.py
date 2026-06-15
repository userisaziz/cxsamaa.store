from abc import ABC, abstractmethod


class StorageBackend(ABC):
    @abstractmethod
    async def upload(self, file_data: bytes, destination: str) -> str:
        """Upload file and return URL/path."""

    @abstractmethod
    async def download(self, source: str) -> bytes:
        """Download file and return bytes."""

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete file."""

    @abstractmethod
    async def get_signed_url(self, path: str, expires_in: int = 900) -> str:
        """Generate time-limited access URL (15 min default)."""

    @abstractmethod
    async def generate_presigned_upload_url(self, key: str, content_type: str, expires_in: int = 3600) -> str:
        """Generate pre-signed PUT URL for direct browser-to-storage upload."""

    # --- Sync variants for use inside Celery tasks ---

    @abstractmethod
    def upload_sync(self, file_data: bytes, destination: str) -> str:
        """Synchronous upload for Celery workers."""

    @abstractmethod
    def download_sync(self, source: str) -> bytes:
        """Synchronous download for Celery workers."""

    def download_file_sync(self, source: str, dest_path: str) -> None:
        """Stream download directly to disk (O(1) memory).

        Optional: backends that support streaming (R2/boto3) should override.
        Default raises NotImplementedError — callers must check hasattr().
        """
        raise NotImplementedError("download_file_sync not supported by this backend")

    @abstractmethod
    def delete_sync(self, path: str) -> None:
        """Synchronous delete for Celery workers."""

    @abstractmethod
    def generate_presigned_upload_url_sync(self, key: str, content_type: str, expires_in: int = 3600) -> str:
        """Synchronous presigned URL generation for API endpoints."""
