"""
Comprehensive test suite for audio router endpoints.
Testing all uncovered lines for maximum coverage.
"""
import pytest
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture
def test_audio_file():
    """Create a test audio file."""
    content = b"fake audio data"
    return ("test.wav", BytesIO(content), "audio/wav")


class TestEnsureStorageDir:
    """Test ensure_storage_dir function."""

    @patch('app.routers.audio.settings')
    def test_creates_directory(self, mock_settings, tmp_path):
        """Test storage directory creation."""
        from app.routers.audio import ensure_storage_dir
        
        storage_path = tmp_path / "audio"
        mock_settings.audio_storage_dir = storage_path
        
        result = ensure_storage_dir()
        
        assert result == storage_path
        assert storage_path.exists()


class TestGetOrCreateDefaultUser:
    """Test get_or_create_default_user function."""

    def test_creates_default_user(self, test_db):
        """Test creating default user when it doesn't exist."""
        from app.routers.audio import get_or_create_default_user
        from app.models import User
        
        user = get_or_create_default_user(test_db)
        
        assert user.name == "default"
        assert user.id is not None
        
        # Verify it's in database
        db_user = test_db.query(User).filter_by(name="default").one()
        assert db_user.id == user.id

    def test_returns_existing_default_user(self, test_db):
        """Test returns existing default user."""
        from app.routers.audio import get_or_create_default_user
        
        # Create user first time
        user1 = get_or_create_default_user(test_db)
        
        # Call again, should return same user
        user2 = get_or_create_default_user(test_db)
        
        assert user1.id == user2.id


class TestUploadAudioEndpoint:
    """Test POST /api/audio endpoint."""

    @patch('app.routers.audio.get_elevenlabs_client')
    @patch('app.routers.audio.settings')
    def test_upload_audio_success(self, mock_settings, mock_client_fn, client, tmp_path):
        """Test successful upload."""
        mock_settings.audio_storage_dir = tmp_path / "audio"
        mock_settings.developer_mode = False
        
        mock_client = Mock()
        mock_client.submit_transcription.return_value = {"request_id": "123"}
        mock_client_fn.return_value = mock_client
        
        files = {"audio": ("test.wav", BytesIO(b"audio data"), "audio/wav")}
        response = client.post("/api/audio", files=files)
        
        assert response.status_code == 201
        data = response.json()
        assert data["session_id"] is not None

    @patch('app.routers.audio.get_elevenlabs_client')
    @patch('app.routers.audio.settings')
    def test_upload_audio_elevenlabs_not_configured(self, mock_settings, mock_client_fn, client, tmp_path):
        """Test upload when ElevenLabs not configured."""
        from app.services.elevenlabs import ElevenLabsNotConfiguredError
        
        mock_settings.audio_storage_dir = tmp_path / "audio"
        mock_settings.developer_mode = True
        
        mock_client = Mock()
        mock_client.submit_transcription.side_effect = ElevenLabsNotConfiguredError()
        mock_client_fn.return_value = mock_client
        
        files = {"audio": ("test.wav", BytesIO(b"audio data"), "audio/wav")}
        response = client.post("/api/audio", files=files)
        
        assert response.status_code == 201
        data = response.json()
        assert data["transcription_status"] == "pending"
        assert "not configured" in (data.get("developer_message") or "")





class TestBulkUploadEndpoint:
    """Test POST /api/audio/bulk endpoint."""


    @patch('app.routers.audio.settings')
    def test_bulk_upload_too_many_files(self, mock_settings, client):
        """Test bulk upload exceeds limit."""
        mock_settings.audio_storage_dir = Path("/tmp/audio")
        
        # Create 51 fake files
        files = [("files", ("test{}.wav".format(i), BytesIO(b"data"), "audio/wav")) for i in range(51)]
        response = client.post("/api/audio/bulk", files=files)
        
        assert response.status_code == 400
        assert "50 files" in response.text







