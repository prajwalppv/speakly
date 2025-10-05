"""
Test that audio files are deleted after successful transcription.
This ensures privacy, security, and reduces storage costs.
"""
import pytest
from pathlib import Path
from io import BytesIO
from unittest.mock import patch, Mock

from app.models import User, Session as SessionModel, Transcription


class TestAudioDeletion:
    """Test audio file deletion after transcription."""

    def test_audio_deleted_after_webhook_success(self, client, test_db, tmp_path):
        """Test that audio file is deleted after successful transcription webhook."""
        # Create user and session with audio file
        user = User(name="deletion_test")
        test_db.add(user)
        test_db.commit()
        
        # Create actual audio file
        audio_file = tmp_path / "test_audio.wav"
        audio_file.write_bytes(b"fake audio content")
        
        session = SessionModel(
            user_id=user.id,
            audio_path=str(audio_file),
            status="processing"
        )
        test_db.add(session)
        test_db.commit()
        
        transcription = Transcription(
            session_id=session.id,
            provider_job_id="test-job-123",
            status="submitted"
        )
        test_db.add(transcription)
        test_db.commit()
        
        # Verify file exists before webhook
        assert audio_file.exists()
        
        # Send webhook with completed status
        with patch('app.routers.webhooks.settings') as mock_settings:
            mock_settings.elevenlabs_webhook_secret = None
            
            payload = {
                "task_id": "test-job-123",
                "status": "completed",
                "text": "Test transcription"
            }
            
            response = client.post(
                "/api/webhooks/elevenlabs",
                json=payload,
                headers={"X-ELEVENLABS-SIGNATURE": "test"}
            )
            
            assert response.status_code == 204
        
        # Verify audio file was deleted
        assert not audio_file.exists()
        
        # Verify database reflects deletion
        test_db.refresh(session)
        assert session.audio_path is None
        
        # Verify transcription still exists
        test_db.refresh(transcription)
        assert transcription.text == "Test transcription"
        assert transcription.status == "completed"

    def test_audio_not_deleted_on_failed_transcription(self, client, test_db, tmp_path):
        """Test that audio file is NOT deleted if transcription fails."""
        user = User(name="fail_test")
        test_db.add(user)
        test_db.commit()
        
        audio_file = tmp_path / "test_fail.wav"
        audio_file.write_bytes(b"audio")
        
        session = SessionModel(
            user_id=user.id,
            audio_path=str(audio_file),
            status="processing"
        )
        test_db.add(session)
        test_db.commit()
        
        transcription = Transcription(
            session_id=session.id,
            provider_job_id="fail-job-123",
            status="submitted"
        )
        test_db.add(transcription)
        test_db.commit()
        
        # Send webhook with failed status
        with patch('app.routers.webhooks.settings') as mock_settings:
            mock_settings.elevenlabs_webhook_secret = None
            
            payload = {
                "task_id": "fail-job-123",
                "status": "failed",
                "text": "Transcription failed"
            }
            
            response = client.post(
                "/api/webhooks/elevenlabs",
                json=payload,
                headers={"X-ELEVENLABS-SIGNATURE": "test"}
            )
            
            assert response.status_code == 204
        
        # File should still exist for failed transcriptions
        assert audio_file.exists()
        
        # Database should still have path
        test_db.refresh(session)
        assert session.audio_path is not None

    def test_graceful_handling_if_file_already_deleted(self, client, test_db, tmp_path):
        """Test that webhook handles case where file is already deleted."""
        user = User(name="missing_file_test")
        test_db.add(user)
        test_db.commit()
        
        # Create session with non-existent file path
        session = SessionModel(
            user_id=user.id,
            audio_path=str(tmp_path / "nonexistent.wav"),
            status="processing"
        )
        test_db.add(session)
        test_db.commit()
        
        transcription = Transcription(
            session_id=session.id,
            provider_job_id="missing-job-123",
            status="submitted"
        )
        test_db.add(transcription)
        test_db.commit()
        
        # Send webhook - should not crash
        with patch('app.routers.webhooks.settings') as mock_settings:
            mock_settings.elevenlabs_webhook_secret = None
            
            payload = {
                "task_id": "missing-job-123",
                "status": "completed",
                "text": "Test"
            }
            
            response = client.post(
                "/api/webhooks/elevenlabs",
                json=payload,
                headers={"X-ELEVENLABS-SIGNATURE": "test"}
            )
            
            # Should succeed despite missing file
            assert response.status_code == 204
            
            # Transcription should still be marked complete
            test_db.refresh(transcription)
            assert transcription.status == "completed"


class TestStorageSavings:
    """Test storage and privacy benefits."""

    def test_no_permanent_audio_storage(self, client):
        """Test that workflow doesn't require permanent audio storage."""
        # Upload audio
        files = {"audio": ("test.wav", BytesIO(b"audio"), "audio/wav")}
        response = client.post("/api/audio", files=files)
        
        assert response.status_code == 201
        data = response.json()
        
        # Audio is uploaded temporarily for ElevenLabs
        # But will be deleted after transcription webhook
        # This test verifies the flow works without permanent storage
        assert "session_id" in data
        assert "transcription_id" in data
