from __future__ import annotations

import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_session
from ..models import Session as SessionModel
from ..models import Transcription as TranscriptionModel
from ..models import User
from ..schemas import AudioUploadResponse
from ..services import (
    ElevenLabsClient,
    ElevenLabsError,
    ElevenLabsNotConfiguredError,
    get_elevenlabs_client,
)

router = APIRouter(prefix="/api", tags=["audio"])
logger = logging.getLogger(__name__)


def ensure_storage_dir() -> Path:
    settings.audio_storage_dir.mkdir(parents=True, exist_ok=True)
    return settings.audio_storage_dir


def get_or_create_default_user(db: Session) -> User:
    user = db.query(User).filter_by(name="default").one_or_none()
    if user is None:
        user = User(name="default")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@router.post("/audio", response_model=AudioUploadResponse, status_code=201)
async def upload_audio(
    request: Request,
    audio: Annotated[UploadFile, File(description="Audio file to upload")],
    db: Session = Depends(get_session),
    elevenlabs_client: ElevenLabsClient = Depends(get_elevenlabs_client),
) -> AudioUploadResponse:
    if not audio.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    storage_dir = ensure_storage_dir()
    file_extension = Path(audio.filename).suffix or ".wav"
    unique_name = f"{uuid.uuid4().hex}{file_extension}"
    stored_path = storage_dir / unique_name

    with stored_path.open("wb") as destination:
        shutil.copyfileobj(audio.file, destination)

    user = get_or_create_default_user(db)
    session_record = SessionModel(
        user_id=user.id,
        audio_path=str(stored_path),
        status="pending",
    )
    db.add(session_record)
    db.flush()

    transcription = TranscriptionModel(session_id=session_record.id, status="pending")
    db.add(transcription)
    db.commit()
    db.refresh(session_record)
    db.refresh(transcription)

    session_status = session_record.status
    transcription_status = transcription.status

    webhook_url = str(request.url_for("elevenlabs_webhook"))
    submission_metadata = {
        "session_id": session_record.id,
        "transcription_id": transcription.id,
    }

    try:
        submission = elevenlabs_client.submit_transcription(
            audio_path=stored_path,
            webhook_url=webhook_url,
            metadata=submission_metadata,
        )
    except ElevenLabsNotConfiguredError:
        logger.info("ElevenLabs client is not configured; transcription remains pending.")
        transcription.metadata_payload = submission_metadata
    except ElevenLabsError as exc:
        logger.exception("Failed to submit audio for transcription")
        session_record.status = "error"
        session_record.last_error = str(exc)
        transcription.status = "error"
        transcription.error = str(exc)
        transcription.metadata_payload = submission_metadata
    else:  # pragma: no branch - executed when integration succeeds
        logger.info(
            "ElevenLabs submission accepted",
            extra={
                "extra_data": {
                    "session_id": session_record.id,
                    "transcription_id": transcription.id,
                    "submission": submission,
                }
            },
        )
        provider_job_id = (
            submission.get("task_id")
            or submission.get("id")
            or submission.get("request_id")
        )
        if provider_job_id:
            transcription.provider_job_id = str(provider_job_id)
        transcription.metadata_payload = submission
        transcription.status = "submitted"
        session_record.status = "awaiting_transcription"

    db.add(session_record)
    db.add(transcription)
    db.commit()
    db.refresh(session_record)
    db.refresh(transcription)

    session_status = session_record.status
    transcription_status = transcription.status

    return AudioUploadResponse(
        file_name=audio.filename,
        file_path=stored_path,
        session_id=session_record.id,
        received_at=datetime.utcnow(),
        session_status=session_status,
        transcription_id=transcription.id,
        transcription_status=transcription_status,
    )
