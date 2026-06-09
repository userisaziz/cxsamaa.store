from pathlib import Path

from src.config import settings
from src.storage.base import StorageBackend


class LocalStorage(StorageBackend):
    def __init__(self):
        self.base_dir = Path(settings.local_upload_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    # --- Async methods (used by FastAPI) ---

    async def upload(self, file_data: bytes, destination: str) -> str:
        return self.upload_sync(file_data, destination)

    async def download(self, source: str) -> bytes:
        return self.download_sync(source)

    async def delete(self, path: str) -> None:
        self.delete_sync(path)

    async def get_signed_url(self, path: str, expires_in: int = 900) -> str:
        return str(self.base_dir / path)

    # --- Sync methods (used by Celery workers) ---

    def upload_sync(self, file_data: bytes, destination: str) -> str:
        file_path = self.base_dir / destination
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(file_data)
        return destination

    def download_sync(self, source: str) -> bytes:
        file_path = self.base_dir / source
        return file_path.read_bytes()

    def delete_sync(self, path: str) -> None:
        file_path = self.base_dir / path
        if file_path.exists():
            file_path.unlink()


def get_storage() -> StorageBackend:
    """Factory function to get the configured storage backend."""
    if settings.storage_backend == "local":
        return LocalStorage()
    # Future: add S3Storage()
    raise ValueError(f"Unknown storage backend: {settings.storage_backend}")
