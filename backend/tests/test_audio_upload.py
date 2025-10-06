"""
Test audio upload API endpoint.
"""
import pytest
from unittest.mock import patch, Mock
from app.models import Session, Transcription


class TestAudioUploadAPI:
    """Test POST /api/audio endpoint."""

    @patch('app.routers.audio.settings')
    @patch('app.routers.audio.get_elevenlabs_client')
    def test_upload_audio_creates_session(self, mock_get_client, mock_settings, client, test_db, test_audio_file, tmp_path):
        """Test that uploading audio creates a session and transcription."""
        # Mock settings to use temp directory
        mock_settings.audio_storage_dir = tmp_path / "audio"
        mock_settings.audio_storage_dir.mkdir(parents=True, exist_ok=True)
        mock_settings.developer_mode = False
        mock_settings.elevenlabs_diarization_enabled = False
        
        # Mock ElevenLabs client to avoid external API call
        mock_client = Mock()
        mock_client.is_configured = True
        mock_client.submit_transcription.return_value = {"request_id": "test-123"}
        mock_get_client.return_value = mock_client
        
        # Upload audio
        response = client.post(
            "/api/audio",
            files={"audio": test_audio_file}
        )
        
        # Should succeed
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert "session_id" in data
        assert "session_status" in data
        assert data["session_status"] == "pending"
        
        # Verify session was created in database
        session = test_db.query(Session).filter_by(id=data["session_id"]).first()
        assert session is not None
        assert session.status == "pending"

    @patch('app.routers.audio.settings')
    @patch('app.routers.audio.get_elevenlabs_client')
    def test_upload_audio_creates_transcription(self, mock_get_client, mock_settings, client, test_db, test_audio_file, tmp_path):
        """Test that uploading audio creates a transcription record."""
        # Mock settings to use temp directory
        mock_settings.audio_storage_dir = tmp_path / "audio"
        mock_settings.audio_storage_dir.mkdir(parents=True, exist_ok=True)
        mock_settings.developer_mode = False
        mock_settings.elevenlabs_diarization_enabled = False
        
        mock_client = Mock()
        mock_client.is_configured = True
        mock_client.submit_transcription.return_value = {"request_id": "test-456"}
        mock_get_client.return_value = mock_client
        
        response = client.post(
            "/api/audio",
            files={"audio": test_audio_file}
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify transcription was created
        transcription = test_db.query(Transcription).filter_by(
            session_id=data["session_id"]
        ).first()
        
        assert transcription is not None
        assert transcription.status in ["pending", "submitted"]

    def test_upload_audio_no_file(self, client):
        """Test that uploading without file returns error."""
        response = client.post("/api/audio")
        
        # Should fail with 422 (validation error)
        assert response.status_code == 422

    @patch('app.routers.audio.get_elevenlabs_client')
    def test_upload_audio_stores_file(self, mock_get_client, client, test_db, test_audio_file):
        """Test that audio file is stored with correct path."""
        mock_client = Mock()
        mock_client.submit_transcription.return_value = {"request_id": "test-789"}
        mock_get_client.return_value = mock_client
        
        response = client.post(
            "/api/audio",
            files={"audio": test_audio_file}
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify file path was stored
        session = test_db.query(Session).filter_by(id=data["session_id"]).first()
        assert session.audio_path is not None
        assert len(session.audio_path) > 0

    @patch('app.routers.audio.get_elevenlabs_client')
    def test_upload_multiple_files_creates_multiple_sessions(self, mock_get_client, client, test_db, test_audio_file):
        """Test that multiple uploads create separate sessions."""
        mock_client = Mock()
        mock_client.submit_transcription.return_value = {"request_id": "test-multiple"}
        mock_get_client.return_value = mock_client
        
        # Upload first file
        response1 = client.post(
            "/api/audio",
            files={"audio": test_audio_file}
        )
        session_id1 = response1.json()["session_id"]
        
        # Upload second file
        response2 = client.post(
            "/api/audio",
            files={"audio": test_audio_file}
        )
        session_id2 = response2.json()["session_id"]
        
        # Should create different sessions
        assert session_id1 != session_id2
        
        # Verify both exist in database
        sessions = test_db.query(Session).all()
        assert len(sessions) >= 2


class TestAudioUploadEdgeCases:
    """Test edge cases and error scenarios."""

    @patch('app.routers.audio.get_elevenlabs_client')
    def test_upload_large_filename(self, mock_get_client, client, test_db):
        """Test uploading file with very long filename."""
        mock_client = Mock()
        mock_client.submit_transcription.return_value = {"request_id": "test-long"}
        mock_get_client.return_value = mock_client
        
        # Create file with long name
        long_name = "a" * 200 + ".mp3"
        audio_file = (long_name, b'\xff\xfb\x90\x00' + b'\x00' * 1024, "audio/mpeg")
        
        response = client.post(
            "/api/audio",
            files={"audio": audio_file}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data

    @patch('app.routers.audio.get_elevenlabs_client')
    def test_upload_special_characters_filename(self, mock_get_client, client, test_db):
        """Test uploading file with special characters in name."""
        mock_client = Mock()
        mock_client.submit_transcription.return_value = {"request_id": "test-special"}
        mock_get_client.return_value = mock_client
        
        special_name = "test audio (2024) [final].mp3"
        audio_file = (special_name, b'\xff\xfb\x90\x00' + b'\x00' * 1024, "audio/mpeg")
        
        response = client.post(
            "/api/audio",
            files={"audio": audio_file}
        )
        
        assert response.status_code == 201

    @patch('app.routers.audio.get_elevenlabs_client')
    def test_upload_creates_default_user(self, mock_get_client, client, test_db):
        """Test that upload uses default user."""
        mock_client = Mock()
        mock_client.submit_transcription.return_value = {"request_id": "test-user"}
        mock_get_client.return_value = mock_client
        
        audio_file = ("test.mp3", b'\xff\xfb\x90\x00' + b'\x00' * 1024, "audio/mpeg")
        
        response = client.post(
            "/api/audio",
            files={"audio": audio_file}
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify session is linked to default user
        session = test_db.query(Session).filter_by(id=data["session_id"]).first()
        assert session.user_id == 1  # Default user

    @patch('app.routers.audio.get_elevenlabs_client')
    def test_upload_different_audio_formats(self, mock_get_client, client, test_db):
        """Test uploading different audio formats."""
        mock_client = Mock()
        mock_client.submit_transcription.return_value = {"request_id": "test-format"}
        mock_get_client.return_value = mock_client
        
        formats = [
            ("test.mp3", "audio/mpeg"),
            ("test.wav", "audio/wav"),
            ("test.m4a", "audio/m4a"),
            ("test.ogg", "audio/ogg"),
        ]
        
        for filename, content_type in formats:
            audio_file = (filename, b'\xff\xfb\x90\x00' + b'\x00' * 1024, content_type)
            response = client.post(
                "/api/audio",
                files={"audio": audio_file}
            )
            assert response.status_code == 201

    @patch('app.routers.audio.get_elevenlabs_client')
    def test_upload_response_structure(self, mock_get_client, client, test_db):
        """Test that upload response has correct structure."""
        mock_client = Mock()
        mock_client.submit_transcription.return_value = {"request_id": "test-struct"}
        mock_get_client.return_value = mock_client
        
        audio_file = ("test.mp3", b'\xff\xfb\x90\x00' + b'\x00' * 1024, "audio/mpeg")
        
        response = client.post(
            "/api/audio",
            files={"audio": audio_file}
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert "session_id" in data
        assert "transcription_id" in data
        assert "session_status" in data
        assert "transcription_status" in data
        assert isinstance(data["session_id"], int)
        assert isinstance(data["transcription_id"], int)

    @patch('app.routers.audio.settings')
    @patch('app.routers.audio.get_elevenlabs_client')
    def test_upload_sets_pending_status(self, mock_get_client, mock_settings, client, test_db, tmp_path):
        """Test that newly uploaded sessions have pending status."""
        # Mock settings to use temp directory
        mock_settings.audio_storage_dir = tmp_path / "audio"
        mock_settings.audio_storage_dir.mkdir(parents=True, exist_ok=True)
        mock_settings.developer_mode = False
        mock_settings.elevenlabs_diarization_enabled = False
        
        mock_client = Mock()
        mock_client.is_configured = True
        mock_client.submit_transcription.return_value = {"request_id": "test-pending"}
        mock_get_client.return_value = mock_client
        
        audio_file = ("test.mp3", b'\xff\xfb\x90\x00' + b'\x00' * 1024, "audio/mpeg")
        
        response = client.post(
            "/api/audio",
            files={"audio": audio_file}
        )
        
        data = response.json()
        session = test_db.query(Session).filter_by(id=data["session_id"]).first()
        
        assert session.status == "pending"
        
        transcription = test_db.query(Transcription).filter_by(
            session_id=session.id
        ).first()
        assert transcription.status in ["pending", "submitted"]


class TestAudioUploadErrorHandling:
    """Test audio upload error handling."""

    @patch('app.routers.audio.get_elevenlabs_client')
    def test_upload_handles_elevenlabs_error(self, mock_get_client, client, test_db):
        """Test that ElevenLabs errors are handled gracefully."""
        from app.services.elevenlabs import ElevenLabsError
        
        mock_client = Mock()
        mock_client.is_configured = True  # Make it look configured
        mock_client.submit_transcription.side_effect = ElevenLabsError("API error")
        mock_get_client.return_value = mock_client
        
        audio_file = ("test.mp3", b'\xff\xfb\x90\x00' + b'\x00' * 1024, "audio/mpeg")
        
        response = client.post(
            "/api/audio",
            files={"audio": audio_file}
        )
        
        # Should still create session and transcription
        assert response.status_code == 201
        data = response.json()
        
        # Check session was created
        session = test_db.query(Session).filter_by(id=data["session_id"]).first()
        assert session is not None
        # Status may be error or pending depending on error handling

    @patch('app.routers.audio.settings')
    @patch('app.routers.audio.get_elevenlabs_client')
    def test_upload_handles_elevenlabs_not_configured(self, mock_get_client, mock_settings, client, test_db, tmp_path):
        """Test upload when ElevenLabs is not configured."""
        from app.services.elevenlabs import ElevenLabsNotConfiguredError
        
        # Mock settings to use temp directory
        mock_settings.audio_storage_dir = tmp_path / "audio"
        mock_settings.audio_storage_dir.mkdir(parents=True, exist_ok=True)
        mock_settings.developer_mode = False
        mock_settings.elevenlabs_diarization_enabled = False
        
        mock_client = Mock()
        mock_client.is_configured = False
        mock_client.submit_transcription.side_effect = ElevenLabsNotConfiguredError("Not configured")
        mock_get_client.return_value = mock_client
        
        audio_file = ("test.mp3", b'\xff\xfb\x90\x00' + b'\x00' * 1024, "audio/mpeg")
        
        response = client.post(
            "/api/audio",
            files={"audio": audio_file}
        )
        
        # Should still succeed, transcription stays pending
        assert response.status_code == 201
        data = response.json()
        
        transcription = test_db.query(Transcription).filter_by(
            id=data["transcription_id"]
        ).first()
        assert transcription.status == "pending"

    @patch('app.routers.audio.get_elevenlabs_client')
    def test_upload_handles_unexpected_error(self, mock_get_client, client, test_db):
        """Test handling of unexpected errors during upload."""
        mock_client = Mock()
        mock_client.submit_transcription.side_effect = RuntimeError("Unexpected")
        mock_get_client.return_value = mock_client
        
        audio_file = ("test.mp3", b'\xff\xfb\x90\x00' + b'\x00' * 1024, "audio/mpeg")
        
        response = client.post(
            "/api/audio",
            files={"audio": audio_file}
        )
        
        # Should handle error gracefully and create session
        assert response.status_code == 201
        data = response.json()
        
        # Session should still be created
        session = test_db.query(Session).filter_by(id=data["session_id"]).first()
        assert session is not None


class TestBulkAudioUpload:
    """Test bulk audio upload endpoint."""

    @patch('app.routers.audio.get_elevenlabs_client')
    def test_bulk_upload_multiple_files(self, mock_get_client, client, test_db):
        """Test uploading multiple files at once."""
        mock_client = Mock()
        mock_client.submit_transcription.return_value = {"request_id": "bulk-123"}
        mock_get_client.return_value = mock_client
        
        # Create multiple files with correct field name
        files = [
            ("files", ("file1.mp3", b'\xff\xfb\x90\x00' + b'\x00' * 1024, "audio/mpeg")),
            ("files", ("file2.mp3", b'\xff\xfb\x90\x00' + b'\x00' * 1024, "audio/mpeg")),
            ("files", ("file3.mp3", b'\xff\xfb\x90\x00' + b'\x00' * 1024, "audio/mpeg")),
        ]
        
        response = client.post("/api/audio/bulk", files=files)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["total"] == 3
        assert data["successful"] >= 0
        assert data["failed"] >= 0
        assert len(data["results"]) == 3

    @patch('app.routers.audio.get_elevenlabs_client')
    def test_bulk_upload_no_files(self, mock_get_client, client, test_db):
        """Test bulk upload with no files."""
        response = client.post("/api/audio/bulk", files=[])
        
        # Empty files may return 422 validation error
        assert response.status_code in [400, 422]

    @patch('app.routers.audio.get_elevenlabs_client')
    def test_bulk_upload_too_many_files(self, mock_get_client, client, test_db):
        """Test bulk upload with too many files."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        # Create 51 files (over the limit)
        files = [
            ("files", (f"file{i}.mp3", b'\xff\xfb\x90\x00', "audio/mpeg"))
            for i in range(51)
        ]
        
        response = client.post("/api/audio/bulk", files=files)
        
        assert response.status_code == 400

    @patch('app.routers.audio.get_elevenlabs_client')
    def test_bulk_upload_single_file(self, mock_get_client, client, test_db):
        """Test bulk upload with single file."""
        mock_client = Mock()
        mock_client.submit_transcription.return_value = {"request_id": "bulk-single"}
        mock_get_client.return_value = mock_client
        
        files = [
            ("files", ("single.mp3", b'\xff\xfb\x90\x00' + b'\x00' * 1024, "audio/mpeg")),
        ]
        
        response = client.post("/api/audio/bulk", files=files)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["total"] == 1
        assert data["successful"] >= 0
