"""Shared test fixtures and configuration for all test modules."""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from src.main import app
from src.database import get_db
from src.models.user import User, UserRole


@pytest.fixture
def mock_db():
    """Mock async database session for API tests."""
    mock = AsyncMock()
    # Default return values for common query patterns
    mock.execute.return_value = MagicMock()
    mock.execute.return_value.scalar_one_or_none.return_value = None
    mock.execute.return_value.scalar.return_value = None
    mock.execute.return_value.scalars.return_value.all.return_value = []
    mock.execute.return_value.all.return_value = []
    return mock


@pytest.fixture
def test_client(mock_db):
    """Test client with mocked database dependency."""
    def override_get_db():
        yield mock_db
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    
    # Cleanup: remove dependency override
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user():
    """Create sample user object for authentication tests."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.full_name = "Test User"
    user.role = UserRole.SALESPERSON
    user.brand_id = uuid.uuid4()
    user.store_id = uuid.uuid4()
    user.password_hash = "$2b$12$LQvRlCUmKJz.0XyRz3qWGOvBvQ8xYz9kR0pLmN2oQ3rS4tU5vW6x"
    user.is_active = True
    return user


@pytest.fixture
def sample_recording():
    """Create sample recording object."""
    from src.models.recording import Recording, RecordingStatus
    
    recording = MagicMock(spec=Recording)
    recording.id = uuid.uuid4()
    recording.salesperson_id = uuid.uuid4()
    recording.status = RecordingStatus.COMPLETED
    recording.format = "mp3"
    recording.duration_seconds = 1800.0
    recording.file_size = 5242880  # 5MB
    recording.uploaded_at = "2024-01-15T10:30:00"
    recording.processed_at = "2024-01-15T10:35:00"
    recording.error_message = None
    return recording


@pytest.fixture
def sample_conversation():
    """Create sample conversation object."""
    from src.models.conversation import Conversation
    
    conversation = MagicMock(spec=Conversation)
    conversation.id = uuid.uuid4()
    conversation.recording_id = uuid.uuid4()
    conversation.start_time = 0.0
    conversation.end_time = 300.0
    conversation.segment_count = 15
    return conversation
