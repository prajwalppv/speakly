from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_session
from ..models import Session as SessionModel
from ..models import Transcription as TranscriptionModel
from ..schemas import SessionResponse, TranscriptionResponse

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
        created_at=model.created_at,
        updated_at=model.updated_at,
        transcriptions=[_serialize_transcription(t) for t in model.transcriptions],
    )


@router.get("", response_model=list[SessionResponse])
def list_sessions(db: Session = Depends(get_session)) -> list[SessionResponse]:
    sessions = db.query(SessionModel).order_by(SessionModel.created_at.desc()).all()
    return [_serialize_session(session) for session in sessions]


@router.get("/{session_id}", response_model=SessionResponse)
def get_session_detail(
    session_id: int,
    db: Session = Depends(get_session),
) -> SessionResponse:
    session = db.query(SessionModel).filter_by(id=session_id).one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return _serialize_session(session)
