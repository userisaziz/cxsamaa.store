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

    # --- Sync variants for use inside Celery tasks ---

    @abstractmethod
    def upload_sync(self, file_data: bytes, destination: str) -> str:
        """Synchronous upload for Celery workers."""

    @abstractmethod
    def download_sync(self, source: str) -> bytes:
        """Synchronous download for Celery workers."""

    @abstractmethod
    def delete_sync(self, path: str) -> None:
        """Synchronous delete for Celery workers."""
