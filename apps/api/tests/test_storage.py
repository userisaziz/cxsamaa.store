"""Tests for storage layer — local file storage."""
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Tests: Local Storage
# ---------------------------------------------------------------------------

class TestLocalStorage:
    def test_storage_initialization(self):
        """LocalStorage initializes with settings base directory."""
        from src.storage.local import LocalStorage
        from pathlib import Path
        
        storage = LocalStorage()
        assert isinstance(storage.base_dir, Path)
    
    def test_storage_upload_sync(self):
        """LocalStorage uploads files synchronously."""
        from src.storage.local import LocalStorage
        import tempfile
        from unittest.mock import patch
        
        with patch('src.storage.local.settings.local_upload_dir', tempfile.mkdtemp()):
            storage = LocalStorage()
            test_data = b"fake audio data"
            destination = "rec-123/audio.wav"
            
            result = storage.upload_sync(test_data, destination)
            assert result == destination
    
    def test_storage_download_sync(self):
        """LocalStorage downloads files synchronously."""
        from src.storage.local import LocalStorage
        import tempfile
        from unittest.mock import patch
        
        with patch('src.storage.local.settings.local_upload_dir', tempfile.mkdtemp()):
            storage = LocalStorage()
            test_data = b"audio content"
            destination = "rec-456/test.wav"
            
            # Upload first
            storage.upload_sync(test_data, destination)
            
            # Download
            content = storage.download_sync(destination)
            assert content == test_data
    
    def test_storage_delete_sync(self):
        """LocalStorage deletes files synchronously."""
        from src.storage.local import LocalStorage
        import tempfile
        from unittest.mock import patch
        from pathlib import Path
        
        with patch('src.storage.local.settings.local_upload_dir', tempfile.mkdtemp()) as tmpdir:
            storage = LocalStorage()
            destination = "rec-789/to-delete.wav"
            
            # Upload file
            storage.upload_sync(b"data", destination)
            
            # Verify exists
            file_path = Path(tmpdir) / destination
            assert file_path.exists()
            
            # Delete
            storage.delete_sync(destination)
            assert not file_path.exists()
    
    def test_storage_get_signed_url(self):
        """LocalStorage returns local file path as signed URL."""
        from src.storage.local import LocalStorage
        import tempfile
        from unittest.mock import patch
        
        with patch('src.storage.local.settings.local_upload_dir', tempfile.mkdtemp()):
            storage = LocalStorage()
            path = "rec-123/audio.wav"
            
            signed_url = storage.get_signed_url(path)
            assert "rec-123" in signed_url
            assert "audio.wav" in signed_url
    
    def test_storage_async_upload(self):
        """LocalStorage async upload delegates to sync."""
        import asyncio
        from src.storage.local import LocalStorage
        import tempfile
        from unittest.mock import patch
        
        async def run_test():
            with patch('src.storage.local.settings.local_upload_dir', tempfile.mkdtemp()):
                storage = LocalStorage()
                result = await storage.upload(b"data", "rec-async/test.wav")
                assert result == "rec-async/test.wav"
        
        asyncio.run(run_test())
    
    def test_storage_async_download(self):
        """LocalStorage async download delegates to sync."""
        import asyncio
        from src.storage.local import LocalStorage
        import tempfile
        from unittest.mock import patch
        
        async def run_test():
            with patch('src.storage.local.settings.local_upload_dir', tempfile.mkdtemp()):
                storage = LocalStorage()
                await storage.upload(b"data", "rec-dl/test.wav")
                content = await storage.download("rec-dl/test.wav")
                assert content == b"data"
        
        asyncio.run(run_test())


# ---------------------------------------------------------------------------
# Tests: Storage Integration
# ---------------------------------------------------------------------------

class TestStorageIntegration:
    def test_storage_used_in_preprocessing(self):
        """Preprocessing worker uses storage layer."""
        import src.workers.preprocessing as preprocessing_module
        
        # Verify storage import
        assert hasattr(preprocessing_module, 'get_storage')
    
    def test_storage_factory_pattern(self):
        """Storage uses factory pattern for instantiation."""
        from src.storage.local import get_storage
        import tempfile
        from unittest.mock import patch
        
        with patch('src.storage.local.settings.storage_backend', 'local'):
            with patch('src.storage.local.settings.local_upload_dir', tempfile.mkdtemp()):
                storage = get_storage()
                assert storage is not None
    
    def test_storage_base_dir_is_pathlib(self):
        """Storage base directory uses pathlib.Path."""
        from src.storage.local import LocalStorage
        from pathlib import Path
        import tempfile
        from unittest.mock import patch
        
        with patch('src.storage.local.settings.local_upload_dir', tempfile.mkdtemp()):
            storage = LocalStorage()
            assert isinstance(storage.base_dir, Path)


# ---------------------------------------------------------------------------
# Tests: Storage Edge Cases
# ---------------------------------------------------------------------------

class TestStorageEdgeCases:
    def test_storage_empty_file(self):
        """Storage handles empty files."""
        from src.storage.local import LocalStorage
        import tempfile
        from unittest.mock import patch
        
        with patch('src.storage.local.settings.local_upload_dir', tempfile.mkdtemp()):
            storage = LocalStorage()
            
            storage.upload_sync(b"", "rec-empty/empty.wav")
            content = storage.download_sync("rec-empty/empty.wav")
            assert content == b""
    
    def test_storage_large_file(self):
        """Storage handles large files."""
        from src.storage.local import LocalStorage
        import tempfile
        from unittest.mock import patch
        
        with patch('src.storage.local.settings.local_upload_dir', tempfile.mkdtemp()):
            storage = LocalStorage()
            
            # 1MB of data
            large_data = b"x" * (1024 * 1024)
            storage.upload_sync(large_data, "rec-large/large.wav")
            
            content = storage.download_sync("rec-large/large.wav")
            assert len(content) == 1024 * 1024
    
    def test_storage_uuid_filenames(self):
        """Storage handles UUID-style filenames."""
        from src.storage.local import LocalStorage
        import tempfile
        from unittest.mock import patch
        
        with patch('src.storage.local.settings.local_upload_dir', tempfile.mkdtemp()):
            storage = LocalStorage()
            
            recording_id = str(uuid.uuid4())
            destination = f"{recording_id}/audio.wav"
            storage.upload_sync(b"data", destination)
            
            content = storage.download_sync(destination)
            assert content == b"data"
    
    def test_storage_unicode_content(self):
        """Storage handles unicode content."""
        from src.storage.local import LocalStorage
        import tempfile
        from unittest.mock import patch
        
        with patch('src.storage.local.settings.local_upload_dir', tempfile.mkdtemp()):
            storage = LocalStorage()
            
            unicode_data = "Hello 世界 🌍".encode('utf-8')
            storage.upload_sync(unicode_data, "rec-unicode/data.txt")
            
            content = storage.download_sync("rec-unicode/data.txt")
            assert content == unicode_data
