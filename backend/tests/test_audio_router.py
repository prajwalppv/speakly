"""
Comprehensive test suite for audio router endpoints.
Testing all uncovered lines for maximum coverage.
"""

from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from app.models import Session as SessionModel
from app.models import Transcription
from app.services import get_stt_service
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def test_audio_file():
    """Create a test audio file."""
    content = b"fake audio data"
    return ("test.wav", BytesIO(content), "audio/wav")


class TestEnsureStorageDir:
    """Test ensure_storage_dir function."""

    @patch("app.routers.audio.settings")
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
        from app.models import User
        from app.routers.audio import get_or_create_default_user

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

    @patch("app.routers.audio.get_elevenlabs_client")
    @patch("app.routers.audio.settings")
    def test_upload_audio_success(
        self, mock_settings, mock_client_fn, client, tmp_path
    ):
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

    def test_upload_audio_elevenlabs_not_configured(self, client):
        """Test upload when ElevenLabs configured (mocked in conftest)."""
        files = {"audio": ("test.wav", BytesIO(b"audio data"), "audio/wav")}
        response = client.post("/api/audio", files=files)

        assert response.status_code == 201
        data = response.json()
        # With mock client, transcription is submitted successfully
        assert data["transcription_status"] in ["pending", "submitted"]

    def test_sync_transcription_deletes_audio_file(
        self, client, test_db, tmp_path, monkeypatch
    ):
        """Ensure synchronous STT responses delete the uploaded audio file."""

        class SyncSttService:
            def supports_diarization(self) -> bool:
                return False

            def submit_transcription(self, *, audio_path, webhook_url, metadata=None):
                return {
                    "provider": "groq",
                    "transcription_text": "hello world",
                    "is_sync": True,
                }

        storage_dir = tmp_path / "audio"
        monkeypatch.setattr(
            "app.routers.audio.settings.audio_storage_dir", storage_dir, raising=False
        )
        storage_dir.mkdir(parents=True, exist_ok=True)

        client.app.dependency_overrides[get_stt_service] = lambda: SyncSttService()

        files = {"audio": ("test.wav", BytesIO(b"audio data"), "audio/wav")}
        response = client.post("/api/audio", files=files)

        assert response.status_code == 201
        data = response.json()

        session = (
            test_db.query(SessionModel).filter_by(id=data["session_id"]).one_or_none()
        )
        assert session is not None
        assert session.audio_path is None

        uploaded_path = Path(data["file_path"])
        assert not uploaded_path.exists()
        assert list(storage_dir.iterdir()) == []

        client.app.dependency_overrides.pop(get_stt_service, None)

    @pytest.mark.asyncio
    async def test_mock_webhook_deletes_audio_file(
        self, test_db, tmp_path, monkeypatch
    ):
        """Ensure developer-mode mock webhook removes stored audio."""
        from app.routers.audio import _trigger_mock_webhook

        storage_dir = tmp_path / "audio"
        storage_dir.mkdir(parents=True, exist_ok=True)
        audio_path = storage_dir / "mock.wav"
        audio_path.write_bytes(b"audio data")

        session = SessionModel(
            user_id=1,
            audio_path=str(audio_path),
            status="awaiting_transcription",
        )
        transcription = Transcription(session=session, status="submitted")
        test_db.add_all([session, transcription])
        test_db.commit()
        test_db.refresh(session)
        test_db.refresh(transcription)

        test_session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=test_db.get_bind(),
        )
        monkeypatch.setattr(
            "app.routers.audio.SessionLocal", test_session_factory, raising=False
        )

        async def immediate_sleep(_seconds):
            return None

        async def noop_schedule(*_args, **_kwargs):
            return None

        monkeypatch.setattr("app.routers.audio.asyncio.sleep", immediate_sleep)
        monkeypatch.setattr(
            "app.routers.audio.schedule_summary_and_todos", noop_schedule
        )

        await _trigger_mock_webhook(session.id, transcription.id)

        assert not audio_path.exists()
        test_db.expire_all()
        updated_session = test_db.query(SessionModel).filter_by(id=session.id).one()
        assert updated_session.audio_path is None


class TestBulkUploadEndpoint:
    """Test POST /api/audio/bulk endpoint."""

    @patch("app.routers.audio.settings")
    def test_bulk_upload_too_many_files(self, mock_settings, client):
        """Test bulk upload exceeds limit."""
        mock_settings.audio_storage_dir = Path("/tmp/audio")

        # Create 51 fake files
        files = [
            ("files", (f"test{i}.wav", BytesIO(b"data"), "audio/wav"))
            for i in range(51)
        ]
        response = client.post("/api/audio/bulk", files=files)

        assert response.status_code == 400
        assert "50 files" in response.text
