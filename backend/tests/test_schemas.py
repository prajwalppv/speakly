"""
Test Pydantic schemas and validation.
"""
import pytest
from datetime import datetime
from pathlib import Path
from pydantic import ValidationError


class TestSessionSchemas:
    """Test Session-related schemas."""

    def test_session_response_schema(self):
        """Test SessionResponse schema validation."""
        from app.schemas import SessionResponse
        
        data = {
            "id": 1,
            "status": "completed",
            "description": None,
            "audio_path": Path("/path/test.mp3"),
            "last_error": None,
            "last_transcribed_at": None,
            "has_pj": False,
            "todo_count": 0,
            "task_updates_count": 0,
            "processing_stages": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "transcriptions": [],
            "speaker_segments": [],
            "summary": None,
            "todos": [],
            "tags": []
        }
        
        session = SessionResponse(**data)
        assert session.id == 1
        assert session.status == "completed"
        assert session.has_pj is False

    def test_session_response_with_description(self):
        """Test SessionResponse with optional description."""
        from app.schemas import SessionResponse
        
        data = {
            "id": 1,
            "status": "pending",
            "description": "Test meeting",
            "audio_path": Path("/path/test.mp3"),
            "last_error": None,
            "last_transcribed_at": None,
            "has_pj": True,
            "todo_count": 3,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "transcriptions": [],
            "speaker_segments": [],
            "summary": None,
            "todos": [],
            "tags": []
        }
        
        session = SessionResponse(**data)
        assert session.description == "Test meeting"
        assert session.has_pj is True
        assert session.todo_count == 3


class TestTranscriptionSchemas:
    """Test Transcription-related schemas."""

    def test_transcription_response_schema(self):
        """Test TranscriptionResponse schema."""
        from app.schemas import TranscriptionResponse
        
        data = {
            "id": 1,
            "status": "completed",
            "text": "Test transcript",
            "provider": "elevenlabs",
            "provider_job_id": "job-123",
            "error": None,
            "metadata": None,
            "duration_ms": None,
            "channel_count": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        transcription = TranscriptionResponse(**data)
        assert transcription.text == "Test transcript"
        assert transcription.provider == "elevenlabs"

    def test_transcription_with_metadata(self):
        """Test transcription with metadata payload."""
        from app.schemas import TranscriptionResponse
        
        metadata = {"duration_ms": 30000, "language": "en"}
        
        data = {
            "id": 1,
            "status": "completed",
            "text": "Test",
            "provider": "elevenlabs",
            "provider_job_id": None,
            "error": None,
            "metadata": metadata,
            "duration_ms": 30000,
            "channel_count": 2,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        transcription = TranscriptionResponse(**data)
        assert transcription.metadata["duration_ms"] == 30000
        assert transcription.duration_ms == 30000

    def test_transcription_with_error(self):
        """Test transcription with error field."""
        from app.schemas import TranscriptionResponse
        
        data = {
            "id": 1,
            "status": "error",
            "text": None,
            "provider": "elevenlabs",
            "provider_job_id": "job-456",
            "error": "Connection timeout",
            "metadata": None,
            "duration_ms": None,
            "channel_count": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        transcription = TranscriptionResponse(**data)
        assert transcription.error == "Connection timeout"
        assert transcription.status == "error"


class TestAudioUploadSchemas:
    """Test audio upload schemas."""

    def test_audio_upload_response(self):
        """Test AudioUploadResponse schema."""
        from app.schemas import AudioUploadResponse
        
        data = {
            "status": "received",
            "file_name": "test.mp3",
            "file_path": Path("/path/test.mp3"),
            "session_id": 1,
            "received_at": datetime.utcnow(),
            "session_status": "pending",
            "transcription_id": 1,
            "transcription_status": "submitted",
            "developer_message": None
        }
        
        response = AudioUploadResponse(**data)
        assert response.session_id == 1
        assert response.transcription_id == 1
        assert response.file_name == "test.mp3"

    def test_audio_upload_response_with_developer_message(self):
        """Test AudioUploadResponse with developer message."""
        from app.schemas import AudioUploadResponse
        
        data = {
            "status": "received",
            "file_name": "test.mp3",
            "file_path": Path("/path/test.mp3"),
            "session_id": 1,
            "received_at": datetime.utcnow(),
            "session_status": "pending",
            "transcription_id": 1,
            "transcription_status": "submitted",
            "developer_message": "Upload successful in dev mode"
        }
        
        response = AudioUploadResponse(**data)
        assert response.developer_message == "Upload successful in dev mode"


class TestTodoSchemas:
    """Test Todo-related schemas."""

    def test_todo_response_schema(self):
        """Test TodoResponse schema."""
        from app.schemas import TodoResponse
        
        data = {
            "id": 1,
            "title": "Test task",
            "due_hint": None,
            "confidence": 0.95,
            "status": "pending",
            "source_start_ms": None,
            "source_end_ms": None,
            "source_excerpt": None,
            "ticktick_sync_status": "pending",
            "ticktick_task_id": None,
            "ticktick_synced_at": None,
            "ticktick_sync_error": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        todo = TodoResponse(**data)
        assert todo.title == "Test task"
        assert todo.confidence == 0.95
        assert todo.ticktick_sync_status == "pending"

    def test_todo_with_due_hint(self):
        """Test todo with due_hint field."""
        from app.schemas import TodoResponse
        
        data = {
            "id": 1,
            "title": "Call tomorrow",
            "due_hint": "tomorrow at 2pm",
            "confidence": 0.88,
            "status": "pending",
            "source_start_ms": 1000,
            "source_end_ms": 5000,
            "source_excerpt": "need to call tomorrow at 2pm",
            "ticktick_sync_status": "pending",
            "ticktick_task_id": None,
            "ticktick_synced_at": None,
            "ticktick_sync_error": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        todo = TodoResponse(**data)
        assert todo.due_hint == "tomorrow at 2pm"
        assert todo.source_excerpt == "need to call tomorrow at 2pm"

    def test_todo_with_ticktick_sync(self):
        """Test todo with TickTick sync fields."""
        from app.schemas import TodoResponse
        
        synced_at = datetime.utcnow()
        
        data = {
            "id": 1,
            "title": "Synced task",
            "due_hint": None,
            "confidence": 0.9,
            "status": "pending",
            "source_start_ms": None,
            "source_end_ms": None,
            "source_excerpt": None,
            "ticktick_sync_status": "synced",
            "ticktick_task_id": "tt-123",
            "ticktick_synced_at": synced_at,
            "ticktick_sync_error": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        todo = TodoResponse(**data)
        assert todo.ticktick_task_id == "tt-123"
        assert todo.ticktick_sync_status == "synced"
        assert todo.ticktick_synced_at == synced_at


class TestTagSchemas:
    """Test Tag-related schemas."""

    def test_tag_response_schema(self):
        """Test TagResponse schema."""
        from app.schemas import TagResponse
        
        data = {
            "id": 1,
            "name": "meeting",
            "category": "event",
            "color": "#3b82f6",
            "auto_generated": False,
            "usage_count": 5,
            "created_at": datetime.utcnow()
        }
        
        tag = TagResponse(**data)
        assert tag.name == "meeting"
        assert tag.color == "#3b82f6"
        assert tag.usage_count == 5

    def test_tag_auto_generated_field(self):
        """Test tag with auto_generated field."""
        from app.schemas import TagResponse
        
        data = {
            "id": 1,
            "name": "auto-tag",
            "category": "ai",
            "color": "#ff0000",
            "auto_generated": True,
            "usage_count": 0,
            "created_at": datetime.utcnow()
        }
        
        tag = TagResponse(**data)
        assert tag.auto_generated is True

    def test_tag_create_schema(self):
        """Test TagCreate schema for creating custom tags."""
        from app.schemas import TagCreate
        
        tag_data = {
            "name": "custom-tag",
            "category": "work",
            "color": "#00ff00"
        }
        
        tag = TagCreate(**tag_data)
        assert tag.name == "custom-tag"
        assert tag.category == "work"


class TestSpeakerSchemas:
    """Test Speaker-related schemas."""

    def test_speaker_segment_response(self):
        """Test SpeakerSegmentResponse schema."""
        from app.schemas import SpeakerSegmentResponse
        
        data = {
            "id": 1,
            "speaker_label": "Speaker 1",
            "start_ms": 0,
            "end_ms": 5000,
            "confidence": 0.92,
            "is_pj": True,
            "channel_index": 0,
            "speaker_profile": "PJ"
        }
        
        segment = SpeakerSegmentResponse(**data)
        assert segment.speaker_label == "Speaker 1"
        assert segment.is_pj is True
        assert segment.confidence == 0.92


class TestErrorSchemas:
    """Test error response schemas."""

    def test_api_error_schema(self):
        """Test APIError schema."""
        from app.schemas import APIError
        
        error = APIError(
            type="not_found",
            message="Resource not found"
        )
        
        assert error.type == "not_found"
        assert error.message == "Resource not found"

    def test_api_error_with_details(self):
        """Test APIError with optional details."""
        from app.schemas import APIError
        
        details = {"resource_id": 123, "resource_type": "session"}
        error = APIError(
            type="not_found",
            message="Session not found",
            details=details
        )
        
        assert error.details["resource_id"] == 123

    def test_api_error_with_debug_info(self):
        """Test APIError with debug information."""
        from app.schemas import APIError
        
        debug = {"stack_trace": "line 42", "request_id": "abc123"}
        error = APIError(
            type="internal_error",
            message="Something went wrong",
            debug=debug
        )
        
        assert error.debug["request_id"] == "abc123"


class TestSchemaValidation:
    """Test schema validation rules."""

    def test_invalid_session_missing_required(self):
        """Test that missing required fields raise validation error."""
        from app.schemas import SessionResponse
        
        with pytest.raises(ValidationError):
            # Missing many required fields
            SessionResponse(id=1, status="pending")

    def test_confidence_range_validation(self):
        """Test that confidence values are within valid range."""
        from app.schemas import TodoResponse
        
        data = {
            "id": 1,
            "title": "Task",
            "confidence": 0.95,
            "status": "pending",
            "ticktick_sync_status": "pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        todo = TodoResponse(**data)
        assert 0 <= todo.confidence <= 1

    def test_datetime_fields_parsing(self):
        """Test that datetime fields parse correctly."""
        from app.schemas import SessionResponse
        
        now = datetime.utcnow()
        data = {
            "id": 1,
            "status": "pending",
            "description": None,
            "audio_path": None,
            "last_error": None,
            "last_transcribed_at": now,
            "has_pj": False,
            "todo_count": 0,
            "created_at": now,
            "updated_at": now,
            "transcriptions": [],
            "speaker_segments": [],
            "summary": None,
            "todos": [],
            "tags": []
        }
        
        session = SessionResponse(**data)
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)
        assert session.last_transcribed_at == now

    def test_tag_name_validation(self):
        """Test that tag names are validated."""
        from app.schemas import TagCreate
        
        # Valid tag
        tag = TagCreate(name="valid-tag")
        assert tag.name == "valid-tag"
        
        # Invalid: empty name should fail
        with pytest.raises(ValidationError):
            TagCreate(name="")

    def test_path_field_handling(self):
        """Test that Path fields are handled correctly."""
        from app.schemas import AudioUploadResponse
        
        data = {
            "file_name": "test.mp3",
            "file_path": "/storage/audio/test.mp3",  # String path
            "received_at": datetime.utcnow(),
            "session_status": "pending"
        }
        
        response = AudioUploadResponse(**data)
        assert isinstance(response.file_path, Path)
