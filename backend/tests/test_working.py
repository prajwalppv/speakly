"""
Working tests that match actual database schema.
"""
import pytest
from app.models import User, Session, Transcription, Tag


class TestBasicModels:
    """Test basic model functionality."""

    def test_create_user(self, test_db):
        """Test creating a user."""
        user = User(name="testuser")
        test_db.add(user)
        test_db.commit()
        
        assert user.id is not None
        assert user.name == "testuser"
        assert user.created_at is not None

    def test_create_session(self, test_db):
        """Test creating a session."""
        session = Session(
            user_id=1,
            audio_path="/path/to/audio.mp3",
            status="pending"
        )
        test_db.add(session)
        test_db.commit()
        
        assert session.id is not None
        assert session.status == "pending"

    def test_create_transcription(self, test_db):
        """Test creating a transcription."""
        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()
        
        transcription = Transcription(
            session_id=session.id,
            provider="elevenlabs",
            text="Test transcript"
        )
        test_db.add(transcription)
        test_db.commit()
        
        assert transcription.id is not None
        assert transcription.text == "Test transcript"

    def test_session_transcription_relationship(self, test_db):
        """Test session to transcription relationship."""
        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()
        
        transcription = Transcription(
            session_id=session.id,
            text="Test",
            status="completed"
        )
        test_db.add(transcription)
        test_db.commit()
        
        test_db.refresh(session)
        assert len(session.transcriptions) == 1

    def test_create_tag(self, test_db):
        """Test creating a tag."""
        tag = Tag(
            name="meeting",
            category="event",
            color="#3b82f6"
        )
        test_db.add(tag)
        test_db.commit()
        
        assert tag.id is not None
        assert tag.name == "meeting"

    def test_transcription_metadata(self, test_db):
        """Test storing JSON metadata."""
        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()
        
        metadata = {"duration_ms": 30000, "language": "en"}
        transcription = Transcription(
            session_id=session.id,
            metadata_payload=metadata
        )
        test_db.add(transcription)
        test_db.commit()
        
        test_db.refresh(transcription)
        assert transcription.metadata_payload["duration_ms"] == 30000
