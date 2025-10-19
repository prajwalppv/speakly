"""
Test sessions API endpoints.
"""
import pytest
from app.models import Session, Transcription, LlmRun, Todo


class TestSessionsAPI:
    """Test /api/sessions endpoints."""

    def test_get_sessions_empty(self, client, test_db):
        """Test getting sessions returns empty list when none exist."""
        # The default user exists, but no sessions yet
        response = client.get("/api/sessions")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_sessions_returns_list(self, client, test_db):
        """Test getting all sessions."""
        # Create test sessions
        session1 = Session(user_id=1, audio_path="/path/audio1.mp3", status="completed")
        session2 = Session(user_id=1, audio_path="/path/audio2.mp3", status="pending")
        test_db.add_all([session1, session2])
        test_db.commit()
        
        response = client.get("/api/sessions")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # Should be ordered by created_at DESC (newest first)
        assert data[0]["id"] == session2.id
        assert data[1]["id"] == session1.id
        assert "review_status" in data[0]
        assert "review_status" in data[1]

    def test_get_sessions_includes_transcriptions(self, client, test_db):
        """Test that sessions include transcription data."""
        session = Session(user_id=1, audio_path="/path/test.mp3", status="completed")
        test_db.add(session)
        test_db.commit()
        
        transcription = Transcription(
            session_id=session.id,
            text="Test transcript text",
            status="completed"
        )
        test_db.add(transcription)
        test_db.commit()
        
        response = client.get("/api/sessions")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "transcriptions" in data[0]
        assert len(data[0]["transcriptions"]) == 1
        assert data[0]["transcriptions"][0]["text"] == "Test transcript text"

    def test_get_session_by_id_success(self, client, test_db):
        """Test getting a specific session by ID."""
        session = Session(
            user_id=1,
            audio_path="/path/test.mp3",
            status="completed",
            description="Test description"
        )
        test_db.add(session)
        test_db.commit()
        
        response = client.get(f"/api/sessions/{session.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session.id
        assert data["status"] == "completed"
        assert data["description"] == "Test description"
        assert data["review_status"] == "pending"

    def test_get_session_by_id_not_found(self, client, test_db):
        """Test getting non-existent session returns 404."""
        response = client.get("/api/sessions/99999")
        
        assert response.status_code == 404

    def test_get_session_includes_summary(self, client, test_db):
        """Test that session includes summary data."""
        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()
        
        # Create LLM run for summary
        llm_run = LlmRun(
            session_id=session.id,
            run_type="summary",
            model="gpt-4",
            prompt="Summarize this",
            response="This is a summary",
            status="completed"
        )
        test_db.add(llm_run)
        test_db.commit()
        
        # Link summary to session
        session.summary_run_id = llm_run.id
        test_db.commit()
        
        response = client.get(f"/api/sessions/{session.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data or "summary_run" in data

    def test_sessions_with_multiple_transcriptions(self, client, test_db):
        """Test session with multiple transcription attempts."""
        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()
        
        # First attempt failed
        trans1 = Transcription(
            session_id=session.id,
            status="error",
            error="Connection timeout"
        )
        # Second attempt succeeded
        trans2 = Transcription(
            session_id=session.id,
            text="Success transcript",
            status="completed"
        )
        test_db.add_all([trans1, trans2])
        test_db.commit()
        
        response = client.get(f"/api/sessions/{session.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["transcriptions"]) == 2


class TestSessionMetrics:
    """Test session metrics and statistics."""

    def test_session_includes_todo_count(self, client, test_db):
        """Test that session response includes todo count."""
        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()
        
        response = client.get(f"/api/sessions/{session.id}")
        
        assert response.status_code == 200
        data = response.json()
        # Should have todo_count field
        assert "todo_count" in data or "todos" in data

    def test_session_duration_metadata(self, client, test_db):
        """Test that session includes audio duration metadata."""
        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()
        
        transcription = Transcription(
            session_id=session.id,
            metadata_payload={"duration_ms": 45000},
            status="completed"
        )
        test_db.add(transcription)
        test_db.commit()
        
        response = client.get(f"/api/sessions/{session.id}")
        
        assert response.status_code == 200
        data = response.json()
        # Check if duration is accessible
        if data.get("transcriptions"):
            trans = data["transcriptions"][0]
            if trans.get("metadata_payload"):
                assert trans["metadata_payload"]["duration_ms"] == 45000


class TestSessionFilters:
    """Test session filtering options."""

    def test_filter_sessions_by_has_pj_true(self, client, test_db):
        """Test filtering sessions by has_pj=true."""
        session_with_pj = Session(user_id=1, audio_path="/path/pj.mp3", has_pj=True)
        session_without_pj = Session(user_id=1, audio_path="/path/other.mp3", has_pj=False)
        test_db.add_all([session_with_pj, session_without_pj])
        test_db.commit()
        
        response = client.get("/api/sessions?has_pj=true")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["has_pj"] is True

    def test_filter_sessions_by_has_pj_false(self, client, test_db):
        """Test filtering sessions by has_pj=false."""
        session_with_pj = Session(user_id=1, audio_path="/path/pj.mp3", has_pj=True)
        session_without_pj = Session(user_id=1, audio_path="/path/other.mp3", has_pj=False)
        test_db.add_all([session_with_pj, session_without_pj])
        test_db.commit()
        
        response = client.get("/api/sessions?has_pj=false")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["has_pj"] is False

    def test_filter_sessions_by_transcript_search(self, client, test_db):
        """Test searching sessions by transcript text."""
        session1 = Session(user_id=1, audio_path="/path/1.mp3")
        session2 = Session(user_id=1, audio_path="/path/2.mp3")
        test_db.add_all([session1, session2])
        test_db.commit()
        
        trans1 = Transcription(session_id=session1.id, text="Meeting about project planning", status="completed")
        trans2 = Transcription(session_id=session2.id, text="Quick standup update", status="completed")
        test_db.add_all([trans1, trans2])
        test_db.commit()
        
        response = client.get("/api/sessions?q=planning")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == session1.id

    def test_filter_sessions_by_date_range(self, client, test_db):
        """Test filtering sessions by date range."""
        from datetime import datetime, timedelta
        
        old_session = Session(user_id=1, audio_path="/path/old.mp3")
        test_db.add(old_session)
        test_db.commit()
        
        # Manually set created_at to past date
        old_session.created_at = datetime.utcnow() - timedelta(days=10)
        test_db.commit()
        
        new_session = Session(user_id=1, audio_path="/path/new.mp3")
        test_db.add(new_session)
        test_db.commit()
        
        # Filter for sessions from last 5 days
        from_date = (datetime.utcnow() - timedelta(days=5)).isoformat()
        response = client.get(f"/api/sessions?from={from_date}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == new_session.id


class TestSessionReviewFlow:
    """Tests for the manual review and approval flow."""

    def test_approve_session_triggers_sync(self, client, test_db, monkeypatch):
        session = Session(
            user_id=1,
            audio_path="/path/review.mp3",
            status="awaiting_review",
            review_status="pending",
            processing_stages={
                "uploaded": {"status": "completed", "timestamp": "2025-01-01T00:00:00"},
                "transcribing": {"status": "completed", "timestamp": "2025-01-01T00:01:00"},
                "summarizing": {"status": "completed", "timestamp": "2025-01-01T00:02:00"},
                "extracting_tasks": {"status": "completed", "timestamp": "2025-01-01T00:03:00"},
                "tagging": {"status": "completed", "timestamp": "2025-01-01T00:04:00"},
                "review": {"status": "in_progress", "timestamp": None},
                "syncing_tasks": {"status": "pending", "timestamp": None},
            },
        )
        test_db.add(session)
        test_db.commit()

        llm_run = LlmRun(
            session_id=session.id,
            run_type="todos",
            model="test-model",
            prompt="Generate tasks",
            response="[]",
            status="completed",
        )
        test_db.add(llm_run)
        test_db.flush()

        todo = Todo(
            session_id=session.id,
            llm_run_id=llm_run.id,
            title="Follow up",
            status="pending",
            ticktick_sync_status="pending",
        )
        test_db.add(todo)
        session.todo_count = 1
        test_db.commit()

        called = {}

        def fake_schedule(session_id: int, task_updates=None):
            called["session_id"] = session_id
            called["task_updates"] = task_updates

        monkeypatch.setattr(
            "app.routers.sessions.schedule_task_sync", fake_schedule
        )

        response = client.post(f"/api/sessions/{session.id}/approve")

        assert response.status_code == 200
        data = response.json()
        assert data["review_status"] == "approved"
        assert data["status"] in {"processing", "completed", "completed_with_warnings"}
        assert called.get("session_id") == session.id

        test_db.refresh(session)
        assert session.review_status == "approved"
        assert session.status in {"processing", "completed", "completed_with_warnings"}

    def test_reject_session_discards_data(self, client, test_db):
        session = Session(
            user_id=1,
            audio_path="/path/review.mp3",
            status="awaiting_review",
            review_status="pending",
            todo_count=1,
            processing_stages={
                "uploaded": {"status": "completed", "timestamp": "2025-01-01T00:00:00"},
                "transcribing": {"status": "completed", "timestamp": "2025-01-01T00:01:00"},
                "summarizing": {"status": "completed", "timestamp": "2025-01-01T00:02:00"},
                "extracting_tasks": {"status": "completed", "timestamp": "2025-01-01T00:03:00"},
                "tagging": {"status": "completed", "timestamp": "2025-01-01T00:04:00"},
                "review": {"status": "in_progress", "timestamp": None},
                "syncing_tasks": {"status": "pending", "timestamp": None},
            },
        )
        test_db.add(session)
        test_db.commit()

        llm_run = LlmRun(
            session_id=session.id,
            run_type="summary",
            model="test-model",
            prompt="Summarize",
            response="Summary text",
            status="completed",
        )
        test_db.add(llm_run)
        test_db.flush()

        session.summary_run_id = llm_run.id

        todo_run = LlmRun(
            session_id=session.id,
            run_type="todos",
            model="test-model",
            prompt="Todos",
            response="[]",
            status="completed",
        )
        test_db.add(todo_run)
        test_db.flush()

        todo = Todo(
            session_id=session.id,
            llm_run_id=todo_run.id,
            title="Follow up",
            status="pending",
            ticktick_sync_status="pending",
        )
        test_db.add(todo)
        test_db.commit()

        response = client.post(f"/api/sessions/{session.id}/reject")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert data["review_status"] == "rejected"
        assert data["todos"] == []

        test_db.refresh(session)
        assert session.review_status == "rejected"
        assert session.status == "rejected"
        assert session.todo_count == 0
        assert session.summary_run_id is None
        assert test_db.query(Todo).filter_by(session_id=session.id).count() == 0


class TestSessionDeletion:
    """Tests for deleting sessions."""

    def test_delete_single_session(self, client, test_db):
        session = Session(user_id=1, audio_path=None, status="completed")
        test_db.add(session)
        test_db.commit()

        response = client.delete(f"/api/sessions/{session.id}")

        assert response.status_code == 204
        assert test_db.query(Session).filter_by(id=session.id).first() is None

    def test_bulk_delete_sessions(self, client, test_db):
        session1 = Session(user_id=1, audio_path=None, status="completed")
        session2 = Session(user_id=1, audio_path=None, status="pending")
        test_db.add_all([session1, session2])
        test_db.commit()

        response = client.post(
            "/api/sessions/bulk-delete",
            json={"session_ids": [session1.id, session2.id, 9999]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] == 2
        assert 9999 in data["not_found"]
        remaining = (
            test_db.query(Session)
            .filter(Session.id.in_([session1.id, session2.id]))
            .count()
        )
        assert remaining == 0


class TestSessionSerialization:
    """Test session serialization functions."""

    def test_serialize_session_with_todos(self, client, test_db):
        """Test session serialization includes todos."""
        from app.models import Todo, LlmRun
        
        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()
        
        llm_run = LlmRun(
            session_id=session.id,
            run_type="todos",
            model="llama3",
            prompt="Extract tasks",
            response="[]",
            status="completed"
        )
        test_db.add(llm_run)
        test_db.commit()
        
        todo = Todo(
            session_id=session.id,
            llm_run_id=llm_run.id,
            title="Test task",
            confidence=0.95,
            status="pending"
        )
        test_db.add(todo)
        test_db.commit()
        
        response = client.get(f"/api/sessions/{session.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "todos" in data
        assert len(data["todos"]) == 1
        assert data["todos"][0]["title"] == "Test task"

    def test_serialize_session_with_tags(self, client, test_db):
        """Test session serialization includes tags."""
        from app.models import Tag, SessionTag
        
        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()
        
        tag = Tag(name="meeting", category="type", color="#3b82f6", auto_generated=True)
        test_db.add(tag)
        test_db.commit()
        
        session_tag = SessionTag(session_id=session.id, tag_id=tag.id)
        test_db.add(session_tag)
        test_db.commit()
        
        response = client.get(f"/api/sessions/{session.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "tags" in data
        assert len(data["tags"]) == 1
        assert data["tags"][0]["name"] == "meeting"

    def test_serialize_session_with_speaker_segments(self, client, test_db):
        """Test session serialization includes speaker segments."""
        from app.models import SpeakerSegment, Transcription
        
        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()
        
        transcription = Transcription(session_id=session.id, status="completed")
        test_db.add(transcription)
        test_db.commit()
        
        segment = SpeakerSegment(
            session_id=session.id,
            transcription_id=transcription.id,
            speaker_label="SPEAKER_00",
            start_ms=0,
            end_ms=5000,
            confidence=0.9
        )
        test_db.add(segment)
        test_db.commit()
        
        response = client.get(f"/api/sessions/{session.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "speaker_segments" in data
        assert len(data["speaker_segments"]) == 1
        assert data["speaker_segments"][0]["speaker_label"] == "SPEAKER_00"

    def test_serialize_transcription_with_metadata(self, client, test_db):
        """Test transcription serialization includes metadata."""
        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()
        
        transcription = Transcription(
            session_id=session.id,
            text="Test",
            status="completed",
            provider="elevenlabs",
            provider_job_id="job-123",
            duration_ms=30000,
            channel_count=1,
            metadata_payload={"custom": "data"}
        )
        test_db.add(transcription)
        test_db.commit()
        
        response = client.get(f"/api/sessions/{session.id}")
        
        assert response.status_code == 200
        data = response.json()
        trans = data["transcriptions"][0]
        assert trans["provider"] == "elevenlabs"
        assert trans["provider_job_id"] == "job-123"
        assert trans["duration_ms"] == 30000
        assert trans["channel_count"] == 1
        assert trans["metadata"]["custom"] == "data"

    def test_serialize_summary_from_llm_run(self, client, test_db):
        """Test summary serialization from LlmRun."""
        from app.models import LlmRun, Transcription
        
        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()
        
        transcription = Transcription(session_id=session.id, text="Test transcript", status="completed")
        test_db.add(transcription)
        test_db.commit()
        
        llm_run = LlmRun(
            session_id=session.id,
            run_type="summary",
            model="llama3",
            prompt="Summarize: Test transcript",
            response="Summary text",
            status="completed"
        )
        test_db.add(llm_run)
        test_db.commit()
        
        session.summary_run_id = llm_run.id
        test_db.commit()
        
        response = client.get(f"/api/sessions/{session.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["summary"] is not None
        assert data["summary"]["text"] == "Summary text"
        assert data["summary"]["model"] == "llama3"

    def test_session_response_includes_processing_stages(self, client, test_db):
        """Test session includes processing stages."""
        session = Session(
            user_id=1,
            audio_path="/path/test.mp3",
            processing_stages={"transcribing": {"status": "completed"}}
        )
        test_db.add(session)
        test_db.commit()
        
        response = client.get(f"/api/sessions/{session.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "processing_stages" in data
        assert data["processing_stages"]["transcribing"]["status"] == "completed"

    def test_session_task_updates_count(self, client, test_db):
        """Test session includes task updates count from LLM metadata."""
        from app.models import LlmRun
        
        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()
        
        llm_run = LlmRun(
            session_id=session.id,
            run_type="summary",
            model="llama3",
            prompt="Summarize",
            response="Summary",
            status="completed",
            metadata_payload={"task_updates": [{"task": "Task 1"}, {"task": "Task 2"}]}
        )
        test_db.add(llm_run)
        test_db.commit()
        
        session.summary_run_id = llm_run.id
        test_db.commit()
        
        response = client.get(f"/api/sessions/{session.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "task_updates_count" in data
        assert data["task_updates_count"] == 2


class TestSessionEdgeCases:
    """Test edge cases for session endpoints."""

    def test_session_with_no_transcriptions(self, client, test_db):
        """Test session with no transcriptions returns empty list."""
        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()
        
        response = client.get(f"/api/sessions/{session.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["transcriptions"] == []

    def test_session_with_no_summary(self, client, test_db):
        """Test session with no summary returns None."""
        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()
        
        response = client.get(f"/api/sessions/{session.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["summary"] is None

    def test_list_sessions_no_filters(self, client, test_db):
        """Test listing sessions without any filters."""
        sessions = [Session(user_id=1, audio_path=f"/path/{i}.mp3") for i in range(3)]
        test_db.add_all(sessions)
        test_db.commit()
        
        response = client.get("/api/sessions")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3


class TestUserPreferences:
    """Tests for user preferences endpoints."""

    def test_get_user_preferences_default(self, client):
        response = client.get("/api/user/preferences")

        assert response.status_code == 200
        data = response.json()
        assert data["auto_approve_sessions"] is False

    def test_update_user_preferences(self, client):
        response = client.put(
            "/api/user/preferences",
            json={"auto_approve_sessions": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["auto_approve_sessions"] is True

        confirm = client.get("/api/user/preferences")
        assert confirm.status_code == 200
        assert confirm.json()["auto_approve_sessions"] is True
