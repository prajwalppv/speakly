from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session, joinedload

from ..auth import get_current_user
from ..config import settings
from ..database import get_session
from ..models import LlmRun
from ..models import Session as SessionModel
from ..models import SessionTag, SpeakerProfile, SpeakerSegment
from ..models import Todo as TodoModel
from ..models import Transcription as TranscriptionModel
from ..models import User
from ..schemas import (
    SessionBulkDeleteRequest,
    SessionBulkDeleteResponse,
    SessionResponse,
    SpeakerSegmentResponse,
    SummaryResponse,
    TagResponse,
    TodoResponse,
    TranscriptionResponse,
)
from ..services.task_sync_service import schedule_task_sync

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _serialize_transcription(model: TranscriptionModel) -> TranscriptionResponse:
    return TranscriptionResponse(
        id=model.id,
        status=model.status,
        text=model.text,
        provider=model.provider,
        provider_job_id=model.provider_job_id,
        error=model.error,
        metadata=model.metadata_payload,
        duration_ms=model.duration_ms,
        channel_count=model.channel_count,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _serialize_segment(model: SpeakerSegment) -> SpeakerSegmentResponse:
    return SpeakerSegmentResponse(
        id=model.id,
        speaker_label=model.speaker_label,
        start_ms=model.start_ms,
        end_ms=model.end_ms,
        confidence=model.confidence,
        is_pj=model.is_pj,
        channel_index=model.channel_index,
        speaker_profile=model.speaker_profile.name if model.speaker_profile else None,
    )


def _serialize_summary(model: SessionModel) -> SummaryResponse | None:
    run = model.summary_run
    if not run:
        return None
    return SummaryResponse(
        id=run.id,
        model=run.model,
        text=run.response,
        status=run.status,
        updated_at=run.updated_at,
    )


def _serialize_todo(model: TodoModel) -> TodoResponse:
    return TodoResponse(
        id=model.id,
        title=model.title,
        due_hint=model.due_hint,
        confidence=model.confidence,
        status=model.status,
        source_start_ms=model.source_start_ms,
        source_end_ms=model.source_end_ms,
        source_excerpt=model.source_excerpt,
        ticktick_sync_status=model.ticktick_sync_status,
        ticktick_task_id=model.ticktick_task_id,
        ticktick_synced_at=model.ticktick_synced_at,
        ticktick_sync_error=model.ticktick_sync_error,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _serialize_tag(session_tag: SessionTag) -> TagResponse:
    tag = session_tag.tag
    return TagResponse(
        id=tag.id,
        name=tag.name,
        category=tag.category,
        color=tag.color,
        auto_generated=tag.auto_generated,
        usage_count=0,  # Not calculated per-session
        created_at=tag.created_at,
    )


def _serialize_session(model: SessionModel) -> SessionResponse:
    # Count task updates from LLM run metadata
    task_updates_count = 0
    if model.summary_run and model.summary_run.metadata_payload:
        task_updates = model.summary_run.metadata_payload.get("task_updates", [])
        task_updates_count = len(task_updates) if task_updates else 0

    return SessionResponse(
        id=model.id,
        status=model.status,
        review_status=model.review_status,
        description=model.description,
        audio_path=model.audio_path,
        last_error=model.last_error,
        last_transcribed_at=model.last_transcribed_at,
        reviewed_at=model.reviewed_at,
        has_pj=model.has_pj,
        todo_count=model.todo_count,
        task_updates_count=task_updates_count,
        processing_stages=model.processing_stages,
        created_at=model.created_at,
        updated_at=model.updated_at,
        transcriptions=[_serialize_transcription(t) for t in model.transcriptions],
        speaker_segments=[_serialize_segment(s) for s in model.speaker_segments],
        summary=_serialize_summary(model),
        todos=[_serialize_todo(todo) for todo in model.todos],
        tags=[_serialize_tag(st) for st in model.session_tags],
    )


def _get_session_with_details(
    db: Session, session_id: int, user_id: int
) -> SessionModel | None:
    return (
        db.query(SessionModel)
        .options(
            joinedload(SessionModel.transcriptions),
            joinedload(SessionModel.speaker_segments).joinedload(
                SpeakerSegment.speaker_profile
            ),
            joinedload(SessionModel.todos),
            joinedload(SessionModel.summary_run),
            joinedload(SessionModel.session_tags).joinedload(SessionTag.tag),
        )
        .filter(
            SessionModel.id == session_id,
            SessionModel.user_id == user_id,
        )
        .one_or_none()
    )


def _get_latest_task_updates(db: Session, session_id: int) -> list[dict]:
    latest_run = (
        db.query(LlmRun)
        .filter(
            LlmRun.session_id == session_id,
            LlmRun.run_type == "todos",
            LlmRun.status == "completed",
        )
        .order_by(LlmRun.created_at.desc())
        .first()
    )
    if not latest_run or not latest_run.metadata_payload:
        return []
    updates = latest_run.metadata_payload.get("task_updates")
    if isinstance(updates, list):
        return updates
    return []


def _delete_session_record(session: SessionModel, db: Session) -> None:
    """Delete a session and related resources."""
    # Attempt to remove synced TickTick tasks before deleting
    todos = list(session.todos)
    if todos:
        try:
            from ..services.task_sync_service import task_sync_service

            for todo in todos:
                if todo.ticktick_task_id and todo.ticktick_project_id:
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(
                                task_sync_service.delete_from_ticktick(
                                    todo.ticktick_task_id,
                                    todo.ticktick_project_id,
                                )
                            )
                        finally:
                            loop.close()
                    except Exception as exc:
                        logger.warning(
                            "Failed to delete TickTick task during session cleanup",
                            extra={
                                "extra_data": {
                                    "session_id": session.id,
                                    "todo_id": todo.id,
                                    "error": str(exc),
                                }
                            },
                        )
        finally:
            asyncio.set_event_loop(None)

    # Delete stored audio if it still exists
    if session.audio_path:
        try:
            audio_path = Path(session.audio_path)
            if audio_path.exists():
                audio_path.unlink()
                logger.info(
                    "Deleted audio file while removing session",
                    extra={
                        "extra_data": {
                            "session_id": session.id,
                            "path": session.audio_path,
                        }
                    },
                )
        except Exception as exc:  # pragma: no cover - best effort cleanup
            logger.warning(
                "Failed to delete audio file during session cleanup",
                extra={
                    "extra_data": {
                        "session_id": session.id,
                        "path": session.audio_path,
                        "error": str(exc),
                    }
                },
            )

    db.delete(session)


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    has_pj: bool | None = Query(default=None),
    speaker: str | None = Query(
        default=None, description="Filter by speaker label or profile"
    ),
    q: str | None = Query(default=None, description="Search transcript text"),
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> list[SessionResponse]:
    # Filter by authenticated user
    speaker_query = (
        db.query(SessionModel)
        .filter(SessionModel.user_id == current_user.id)
        .options(
            joinedload(SessionModel.transcriptions),
            joinedload(SessionModel.speaker_segments).joinedload(
                SpeakerSegment.speaker_profile
            ),
            joinedload(SessionModel.todos),
            joinedload(SessionModel.summary_run),
            joinedload(SessionModel.session_tags).joinedload(SessionTag.tag),
        )
    )

    if has_pj is not None:
        speaker_query = speaker_query.filter(SessionModel.has_pj == has_pj)

    if speaker:
        norm = speaker.strip().lower()
        if norm in settings.pj_voice_tag_set:
            speaker_query = speaker_query.filter(SessionModel.has_pj.is_(True))
        else:
            speaker_query = (
                speaker_query.join(SessionModel.speaker_segments)
                .join(SpeakerSegment.speaker_profile, isouter=True)
                .filter(
                    (SpeakerSegment.speaker_label.ilike(f"%{speaker}%"))
                    | (SpeakerProfile.name.ilike(f"%{speaker}%"))
                )
            )

    if q:
        speaker_query = speaker_query.join(SessionModel.transcriptions).filter(
            TranscriptionModel.text.ilike(f"%{q}%")
        )

    if from_date:
        speaker_query = speaker_query.filter(SessionModel.created_at >= from_date)
    if to_date:
        speaker_query = speaker_query.filter(SessionModel.created_at <= to_date)

    sessions = speaker_query.order_by(SessionModel.created_at.desc()).all()

    # When joins are applied (e.g. speaker filter) duplicates can be returned; de-dupe by id.
    unique_sessions: list[SessionModel] = []
    seen_ids: set[int] = set()
    for session in sessions:
        if session.id not in seen_ids:
            unique_sessions.append(session)
            seen_ids.add(session.id)

    return [_serialize_session(session) for session in unique_sessions]


@router.get("/{session_id}", response_model=SessionResponse)
def get_session_detail(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> SessionResponse:
    session = _get_session_with_details(db, session_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return _serialize_session(session)


@router.delete("/{session_id}", status_code=204)
def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Response:
    session = _get_session_with_details(db, session_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    _delete_session_record(session, db)
    db.commit()
    return Response(status_code=204)


@router.post("/bulk-delete", response_model=SessionBulkDeleteResponse)
def bulk_delete_sessions(
    payload: SessionBulkDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> SessionBulkDeleteResponse:
    if not payload.session_ids:
        return SessionBulkDeleteResponse(deleted=0, not_found=[])

    sessions = (
        db.query(SessionModel)
        .options(
            joinedload(SessionModel.todos),
        )
        .filter(
            SessionModel.user_id == current_user.id,
            SessionModel.id.in_(payload.session_ids),
        )
        .all()
    )

    found_ids = {session.id for session in sessions}
    for session in sessions:
        _delete_session_record(session, db)
    db.commit()

    not_found = [sid for sid in payload.session_ids if sid not in found_ids]
    return SessionBulkDeleteResponse(deleted=len(found_ids), not_found=not_found)


@router.post("/{session_id}/approve", response_model=SessionResponse)
def approve_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> SessionResponse:
    session = _get_session_with_details(db, session_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != "awaiting_review":
        raise HTTPException(
            status_code=400,
            detail="Session is not awaiting review",
        )

    task_updates = _get_latest_task_updates(db, session.id)
    unsynced_todos = [
        todo
        for todo in session.todos
        if (todo.ticktick_sync_status or "pending") in {"pending", "error"}
    ]
    has_tasks_to_sync = bool(unsynced_todos or task_updates)

    session.review_status = "approved"
    session.reviewed_at = datetime.utcnow()

    if session.processing_stages:
        stages = session.processing_stages.copy()
        stages["review"] = {
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
        }
        stages["syncing_tasks"] = {
            "status": "in_progress" if has_tasks_to_sync else "completed",
            "timestamp": datetime.utcnow().isoformat(),
        }
        session.processing_stages = stages

    if has_tasks_to_sync:
        session.status = "processing"
    else:
        session.status = (
            "completed_with_warnings" if session.last_error else "completed"
        )

    db.commit()

    if has_tasks_to_sync:
        schedule_task_sync(session.id, task_updates=task_updates)
        db.expire_all()

    updated = _get_session_with_details(db, session_id, current_user.id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Session not found after approval")
    return _serialize_session(updated)


@router.post("/{session_id}/reject", response_model=SessionResponse)
def reject_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> SessionResponse:
    session = _get_session_with_details(db, session_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != "awaiting_review":
        raise HTTPException(
            status_code=400,
            detail="Only sessions awaiting review can be rejected",
        )

    session.review_status = "rejected"
    session.reviewed_at = datetime.utcnow()
    session.status = "rejected"
    session.todo_count = 0
    session.last_error = None

    # Remove pending todos and summary artifacts before discarding
    for todo in list(session.todos):
        db.delete(todo)

    if session.summary_run:
        db.delete(session.summary_run)
        session.summary_run = None
        session.summary_run_id = None

    for session_tag in list(session.session_tags):
        db.delete(session_tag)

    if session.processing_stages:
        stages = session.processing_stages.copy()
        stages["review"] = {
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
        }
        stages["syncing_tasks"] = {
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
        }
        session.processing_stages = stages

    db.commit()

    updated = _get_session_with_details(db, session_id, current_user.id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Session not found after rejection")
    return _serialize_session(updated)


@router.post("/{session_id}/retry", status_code=202)
def retry_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict[str, str]:
    """
    Retry processing for a failed session.

    Args:
        session_id: ID of session to retry
        db: Database session

    Returns:
        Status message

    Raises:
        HTTPException: 404 if session not found
    """
    session = (
        db.query(SessionModel)
        .filter(
            SessionModel.id == session_id,
            SessionModel.user_id == current_user.id,  # Ensure user owns this session
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Clear error and reset to pending
    session.last_error = None
    session.status = "pending"

    # Find failed transcriptions
    failed_transcriptions = [t for t in session.transcriptions if t.status == "error"]

    for transcription in failed_transcriptions:
        transcription.status = "pending"
        transcription.error = None

    db.commit()

    # Re-trigger processing (would call services in production)
    logger.info(
        f"Retrying session {session_id}",
        extra={
            "session_id": session_id,
            "transcription_count": len(failed_transcriptions),
        },
    )

    return {
        "message": f"Session {session_id} queued for retry",
        "transcriptions_reset": len(failed_transcriptions),
    }


@router.post("/{session_id}/regenerate", status_code=202)
def regenerate_summary_and_tasks(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict[str, str]:
    """
    Regenerate summary and tasks from the current transcript.

    Useful after editing a transcript to get fresh AI insights.

    Args:
        session_id: ID of session to regenerate
        db: Database session

    Returns:
        Status message

    Raises:
        HTTPException: 404 if session not found, 400 if no transcript available
    """
    import asyncio
    import threading

    from ..services.llm import _run_summary_and_todos

    logger.info(
        f"🔄 REGENERATE ENDPOINT CALLED for session {session_id}",
        extra={"session_id": session_id},
    )

    session = (
        db.query(SessionModel)
        .filter(
            SessionModel.id == session_id,
            SessionModel.user_id == current_user.id,  # Ensure user owns this session
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check if we have a transcript to work with
    transcription = session.transcriptions[0] if session.transcriptions else None
    if not transcription or not transcription.text:
        raise HTTPException(
            status_code=400, detail="No transcript available to regenerate from"
        )

    # Clear old tasks (delete from TickTick if synced)
    from ..services.task_sync_service import task_sync_service

    old_todos = session.todos[:]
    for todo in old_todos:
        # Delete from TickTick if synced
        if todo.ticktick_task_id and todo.ticktick_project_id:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(
                        task_sync_service.delete_from_ticktick(
                            todo.ticktick_task_id, todo.ticktick_project_id
                        )
                    )
                finally:
                    loop.close()
            except Exception as e:
                logger.warning(
                    f"Failed to delete task {todo.ticktick_task_id} from TickTick: {e}"
                )

        db.delete(todo)

    # Clear old summary/LLM run
    if session.summary_run:
        db.delete(session.summary_run)
        session.summary_run_id = None

    # Clear old tags
    from ..models import SessionTag

    db.query(SessionTag).filter(SessionTag.session_id == session_id).delete()

    # Reset session status for re-processing
    session.status = "processing"
    session.todo_count = 0
    session.last_error = None  # Clear any previous errors
    session.review_status = "pending"
    session.reviewed_at = None

    # Reset ALL processing stages to pending (fresh start)
    session.processing_stages = {
        "uploaded": {
            "status": "completed",
            "timestamp": session.created_at.isoformat(),
        },
        "transcribing": {
            "status": "completed",
            "timestamp": (
                session.last_transcribed_at.isoformat()
                if session.last_transcribed_at
                else None
            ),
        },
        "diarizing": {"status": "pending", "timestamp": None},
        "summarizing": {"status": "pending", "timestamp": None},
        "extracting_tasks": {"status": "pending", "timestamp": None},
        "tagging": {"status": "pending", "timestamp": None},
        "review": {"status": "pending", "timestamp": None},
        "syncing_tasks": {"status": "pending", "timestamp": None},
    }

    db.commit()

    logger.info(
        f"Cleared {len(old_todos)} old tasks and summary for session {session_id}",
        extra={"session_id": session_id, "tasks_cleared": len(old_todos)},
    )

    # Run LLM processing in background thread
    def run_processing():
        # Need to get transcription_id
        _run_summary_and_todos(session_id, transcription.id)

    thread = threading.Thread(target=run_processing, daemon=True)
    thread.start()

    logger.info(
        f"Regenerating summary and tasks for session {session_id}",
        extra={"session_id": session_id},
    )

    return {
        "message": f"Regeneration started for session {session_id}",
        "status": "processing",
    }


logger = logging.getLogger(__name__)
