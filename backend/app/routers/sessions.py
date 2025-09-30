from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from ..config import settings
from ..database import get_session
from ..models import Session as SessionModel
from ..models import SpeakerProfile, SpeakerSegment
from ..models import Todo as TodoModel
from ..models import Transcription as TranscriptionModel
from ..schemas import (
    SessionResponse,
    SpeakerSegmentResponse,
    SummaryResponse,
    TodoResponse,
    TranscriptionResponse,
)

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
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _serialize_session(model: SessionModel) -> SessionResponse:
    return SessionResponse(
        id=model.id,
        status=model.status,
        audio_path=model.audio_path,
        last_error=model.last_error,
        last_transcribed_at=model.last_transcribed_at,
        has_pj=model.has_pj,
        todo_count=model.todo_count,
        created_at=model.created_at,
        updated_at=model.updated_at,
        transcriptions=[_serialize_transcription(t) for t in model.transcriptions],
        speaker_segments=[_serialize_segment(s) for s in model.speaker_segments],
        summary=_serialize_summary(model),
        todos=[_serialize_todo(todo) for todo in model.todos],
    )


@router.get("", response_model=list[SessionResponse])
def list_sessions(
    has_pj: bool | None = Query(default=None),
    speaker: str | None = Query(default=None, description="Filter by speaker label or profile"),
    q: str | None = Query(default=None, description="Search transcript text"),
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
    db: Session = Depends(get_session),
) -> list[SessionResponse]:
    speaker_query = db.query(SessionModel).options(
        joinedload(SessionModel.transcriptions),
        joinedload(SessionModel.speaker_segments).joinedload(SpeakerSegment.speaker_profile),
        joinedload(SessionModel.todos),
        joinedload(SessionModel.summary_run),
    )

    if has_pj is not None:
        speaker_query = speaker_query.filter(SessionModel.has_pj == has_pj)

    if speaker:
        norm = speaker.strip().lower()
        if norm in settings.pj_voice_tag_set:
            speaker_query = speaker_query.filter(SessionModel.has_pj.is_(True))
        else:
            speaker_query = speaker_query.join(SessionModel.speaker_segments).join(
                SpeakerSegment.speaker_profile, isouter=True
            ).filter(
                (SpeakerSegment.speaker_label.ilike(f"%{speaker}%"))
                | (SpeakerProfile.name.ilike(f"%{speaker}%"))
            )

    if q:
        speaker_query = speaker_query.join(SessionModel.transcriptions).filter(
            TranscriptionModel.text.ilike(f"%{q}%")
        )

    if from_date:
        speaker_query = speaker_query.filter(SessionModel.created_at >= from_date)
    if to_date:
        speaker_query = speaker_query.filter(SessionModel.created_at <= to_date)

    sessions = (
        speaker_query.distinct().order_by(SessionModel.created_at.desc()).all()
    )
    return [_serialize_session(session) for session in sessions]


@router.get("/{session_id}", response_model=SessionResponse)
def get_session_detail(
    session_id: int,
    db: Session = Depends(get_session),
) -> SessionResponse:
    session = (
        db.query(SessionModel)
        .options(
            joinedload(SessionModel.transcriptions),
            joinedload(SessionModel.speaker_segments).joinedload(
                SpeakerSegment.speaker_profile
            ),
            joinedload(SessionModel.todos),
            joinedload(SessionModel.summary_run),
        )
        .filter_by(id=session_id)
        .one_or_none()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return _serialize_session(session)
