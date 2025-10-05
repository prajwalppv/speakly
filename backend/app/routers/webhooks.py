from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_session
from ..models import Session as SessionModel
from ..models import Transcription as TranscriptionModel
from ..schemas import ElevenLabsWebhookPayload
from ..services import persist_speaker_segments, schedule_summary_and_todos

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


def verify_signature(provided: str | None, payload: bytes) -> bool:
    secret = settings.elevenlabs_webhook_secret
    if not secret or not provided:
        return True
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    _, _, signature_value = provided.partition("=")
    candidate = signature_value or provided
    return hmac.compare_digest(expected, candidate)


@router.post("/elevenlabs", name="elevenlabs_webhook", status_code=status.HTTP_204_NO_CONTENT)
async def elevenlabs_webhook(
    request: Request,
    payload: ElevenLabsWebhookPayload,
    signature: str | None = Header(default=None, alias="X-ELEVENLABS-SIGNATURE"),
    db: Session = Depends(get_session),
) -> Response:
    raw_body = await request.body()
    if not verify_signature(signature, raw_body):
        logger.warning("Invalid ElevenLabs webhook signature")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    provider_reference = payload.provider_reference
    transcription = None
    if provider_reference:
        transcription = (
            db.query(TranscriptionModel)
            .filter_by(provider_job_id=str(provider_reference))
            .one_or_none()
        )

    metadata_payload = payload.metadata or {}

    if transcription is None and metadata_payload:
        transcription_id = metadata_payload.get("transcription_id")
        if transcription_id is not None:
            transcription = (
                db.query(TranscriptionModel)
                .filter_by(id=int(transcription_id))
                .one_or_none()
            )

    if transcription is None:
        logger.error(
            "Webhook received for unknown transcription",
            extra={
                "extra_data": {
                    "provider_reference": provider_reference,
                    "metadata": payload.metadata,
                }
            },
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found")

    session = (
        db.query(SessionModel)
        .filter_by(id=transcription.session_id)
        .one()
    )

    normalized_status = payload.status.lower()

    transcription_data = payload.data.transcription
    if transcription_data and transcription_data.transcription_id:
        transcription.provider_job_id = (
            transcription.provider_job_id or transcription_data.transcription_id
        )

    if transcription_data and transcription_data.words and settings.elevenlabs_diarization_enabled:
        try:
            persist_speaker_segments(
                db,
                session,
                transcription,
                transcription_data.words,
            )
        except Exception:  # pragma: no cover - diagnostic protection
            logger.exception("Failed to persist speaker segments")

        if transcription_data.words:
            last_end = max(
                (word.get("end") or 0.0) for word in transcription_data.words
            )
            transcription.duration_ms = int(last_end * 1000)

    incoming_metadata = payload.metadata or transcription_data.model_dump(exclude_none=True) if transcription_data else {}
    if incoming_metadata:
        existing_metadata = transcription.metadata_payload or {}
        merged_metadata = {**existing_metadata, **incoming_metadata}
        transcription.metadata_payload = merged_metadata

    if normalized_status in {"completed", "success", "finished"}:
        transcription.status = "completed"
        transcription.text = payload.text
        transcription.error = None
        # Set status to 'processing' not 'completed' - LLM tasks still need to run
        session.status = "processing"
        session.last_error = None
        
        # Update processing stages
        from datetime import datetime
        if session.processing_stages:
            stages = session.processing_stages.copy()
            stages["transcribing"] = {"status": "completed", "timestamp": datetime.utcnow().isoformat()}
            if transcription_data and transcription_data.words:
                stages["diarizing"] = {"status": "completed", "timestamp": datetime.utcnow().isoformat()}
            session.processing_stages = stages
        session.last_transcribed_at = datetime.utcnow()
    elif normalized_status in {"failed", "error"}:
        transcription.status = "error"
        transcription.error = payload.text or "Transcription failed"
        session.status = "error"
        session.last_error = transcription.error
    else:
        transcription.status = normalized_status
        transcription.text = payload.text

    db.add(transcription)
    db.add(session)
    db.commit()
    
    # Delete audio file after successful transcription (privacy + storage savings)
    if transcription.status == "completed" and session.audio_path:
        from pathlib import Path
        try:
            audio_path = Path(session.audio_path)
            if audio_path.exists():
                audio_path.unlink()
                logger.info(
                    f"Deleted audio file after transcription: {session.audio_path}",
                    extra={"extra_data": {"session_id": session.id}}
                )
                # Clear the path in database since file is deleted
                session.audio_path = None
                db.commit()
        except Exception as e:
            logger.warning(
                f"Failed to delete audio file: {e}",
                extra={"extra_data": {"session_id": session.id, "path": session.audio_path}}
            )

    logger.info(
        "Processed ElevenLabs webhook",
        extra={
            "extra_data": {
                "transcription_id": transcription.id,
                "session_id": session.id,
                "status": transcription.status,
            }
        },
    )

    if transcription.status == "completed":
        asyncio.create_task(
            schedule_summary_and_todos(session.id, transcription.id)
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
