from __future__ import annotations

import asyncio
import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import settings
from ..database import SessionLocal, get_session
from ..models import Session as SessionModel
from ..models import Transcription as TranscriptionModel
from ..models import User
from ..schemas import AudioUploadResponse
from ..services import SttError, SttNotConfiguredError, SttService
from ..services import get_elevenlabs_client as _legacy_get_elevenlabs_client
from ..services import get_stt_service, schedule_summary_and_todos
from ..services.audio_cleanup import delete_session_audio_file

router = APIRouter(prefix="/api", tags=["audio"])
logger = logging.getLogger(__name__)


def get_elevenlabs_client():
    """Legacy compatibility wrapper for tests expecting ElevenLabs client injection."""
    return _legacy_get_elevenlabs_client()


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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
    stt_service: SttService = Depends(get_stt_service),
) -> AudioUploadResponse:
    if not audio.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    storage_dir = ensure_storage_dir()
    file_extension = Path(audio.filename).suffix or ".wav"
    unique_name = f"{uuid.uuid4().hex}{file_extension}"
    stored_path = storage_dir / unique_name

    with stored_path.open("wb") as destination:
        shutil.copyfileobj(audio.file, destination)

    user = current_user  # Use authenticated user from Clerk

    # Initialize processing stages for progress tracking
    from datetime import datetime

    processing_stages = {
        "uploaded": {"status": "completed", "timestamp": datetime.utcnow().isoformat()},
        "transcribing": {"status": "pending", "timestamp": None},
        "diarizing": {"status": "pending", "timestamp": None},
        "summarizing": {"status": "pending", "timestamp": None},
        "extracting_tasks": {"status": "pending", "timestamp": None},
        "tagging": {"status": "pending", "timestamp": None},
        "review": {"status": "pending", "timestamp": None},
        "syncing_tasks": {"status": "pending", "timestamp": None},
    }

    session_record = SessionModel(
        user_id=user.id,
        audio_path=str(stored_path),
        status="pending",
        processing_stages=processing_stages,
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

    developer_message: str | None = None

    try:
        submission = stt_service.submit_transcription(
            audio_path=stored_path,
            webhook_url=webhook_url,
            metadata=submission_metadata,
        )
    except SttNotConfiguredError:
        logger.info("STT service not configured; transcription remains pending.")
        transcription.metadata_payload = submission_metadata
        developer_message = (
            "STT provider not configured; transcription pending locally."
        )
    except SttError as exc:
        logger.exception("Failed to submit audio for transcription")
        session_record.status = "error"
        session_record.last_error = str(exc)
        transcription.status = "error"
        transcription.error = str(exc)
        transcription.metadata_payload = submission_metadata
        developer_message = str(exc)
    except Exception as exc:  # Catch any unexpected errors
        logger.exception("Unexpected error during STT submission")
        session_record.status = "error"
        session_record.last_error = f"Unexpected error: {exc}"
        transcription.status = "error"
        transcription.error = f"Unexpected error: {exc}"
        transcription.metadata_payload = submission_metadata
        developer_message = f"Unexpected error: {exc}"
    else:  # pragma: no branch - executed when integration succeeds
        # Check if this is a synchronous response (e.g., from Groq)
        is_sync = submission.get("is_sync", False)

        if is_sync:
            # Handle synchronous transcription (Groq Whisper)
            transcription_text = submission.get("transcription_text", "")
            transcription.text = transcription_text
            transcription.status = "completed"
            transcription.provider = submission.get("provider", "unknown")
            transcription.metadata_payload = submission
            session_record.status = "processing"
            session_record.last_transcribed_at = datetime.utcnow()

            logger.info(
                f"Synchronous transcription completed ({submission.get('provider')})",
                extra={
                    "extra_data": {
                        "session_id": session_record.id,
                        "transcription_id": transcription.id,
                        "provider": submission.get("provider"),
                        "text_length": len(transcription_text),
                    }
                },
            )

            # Update processing stages
            processing_stages["transcribing"] = {
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
            }
            processing_stages["diarizing"] = {
                "status": (
                    "completed" if not stt_service.supports_diarization() else "skipped"
                ),
                "timestamp": datetime.utcnow().isoformat(),
            }
            session_record.processing_stages = processing_stages
            delete_session_audio_file(session_record)

            developer_message = f"Sync transcription via {submission.get('provider')}: {len(transcription_text)} chars"
        else:
            # Handle asynchronous transcription (ElevenLabs, Mock)
            logger.info(
                f"Async transcription submitted ({submission.get('provider')})",
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
            transcription.provider = submission.get("provider", "unknown")
            transcription.metadata_payload = submission
            transcription.status = "submitted"
            session_record.status = "awaiting_transcription"
            if settings.developer_mode:
                developer_message = (
                    f"Submission request_id={submission.get('request_id')}"
                )

    db.add(session_record)
    db.add(transcription)
    db.commit()
    db.refresh(session_record)
    db.refresh(transcription)

    session_status = session_record.status
    transcription_status = transcription.status

    # For synchronous transcriptions, trigger LLM processing immediately
    if transcription.status == "completed" and transcription.text:
        asyncio.create_task(
            schedule_summary_and_todos(session_record.id, transcription.id)
        )
        logger.info("Scheduled LLM processing for synchronous transcription")

    # In developer mode, trigger mock webhook immediately for async providers
    if settings.developer_mode and transcription.status == "submitted":
        asyncio.create_task(_trigger_mock_webhook(session_record.id, transcription.id))
        logger.info("Developer mode: scheduled mock webhook trigger")

    return AudioUploadResponse(
        file_name=audio.filename,
        file_path=stored_path,
        session_id=session_record.id,
        received_at=datetime.utcnow(),
        session_status=session_status,
        transcription_id=transcription.id,
        transcription_status=transcription_status,
        developer_message=developer_message if settings.developer_mode else None,
    )


async def _trigger_mock_webhook(session_id: int, transcription_id: int) -> None:
    """Simulate a webhook callback from ElevenLabs in developer mode."""
    await asyncio.sleep(2)  # Simulate processing delay

    MOCK_TRANSCRIPT = "Get estimates for car fixing, compare the estimates, share it, uh, with Ms. Whitney and, um, get the money transferred. Important tasks."

    with SessionLocal() as db:
        session = db.query(SessionModel).filter_by(id=session_id).one_or_none()
        transcription = (
            db.query(TranscriptionModel).filter_by(id=transcription_id).one_or_none()
        )

        if not session or not transcription:
            logger.warning(
                f"Mock webhook: session or transcription not found (session_id={session_id}, transcription_id={transcription_id})"
            )
            return

        transcription.status = "completed"
        transcription.text = MOCK_TRANSCRIPT
        transcription.error = None
        # Set status to 'processing' not 'completed' - LLM tasks still need to run
        session.status = "processing"
        session.last_error = None
        session.last_transcribed_at = datetime.utcnow()

        delete_session_audio_file(session)

        db.add(transcription)
        db.add(session)
        db.commit()

        logger.info(
            "Mock webhook processed",
            extra={
                "extra_data": {
                    "transcription_id": transcription.id,
                    "session_id": session.id,
                    "status": transcription.status,
                }
            },
        )

    # Trigger summarization and todo extraction
    await schedule_summary_and_todos(session_id, transcription_id)


class BulkUploadResult(BaseModel):
    """Result for a single file in bulk upload."""

    success: bool
    file_name: str
    session_id: int | None = None
    error: str | None = None


class BulkUploadResponse(BaseModel):
    """Response for bulk upload request."""

    total: int
    successful: int
    failed: int
    results: list[BulkUploadResult]


def _extract_timestamp_from_filename(filename: str) -> datetime | None:
    """
    Extract timestamp from filename patterns like:
    - recording_20240102_103045.wav
    - 2024-01-02_10-30-45.m4a
    - voice_note_20240102103045.mp3
    - R20250825234203.WAV (voice recorder format)
    """
    import re

    # Pattern 1: R followed by YYYYMMDDHHMMSS (voice recorder format)
    # Example: R20250825234203.WAV
    pattern1 = r"[Rr](\d{14})"
    match = re.search(pattern1, filename)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y%m%d%H%M%S")
        except ValueError:
            pass

    # Pattern 2: YYYYMMDD_HHMMSS
    pattern2 = r"(\d{8})_(\d{6})"
    match = re.search(pattern2, filename)
    if match:
        try:
            date_str = match.group(1)
            time_str = match.group(2)
            return datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
        except ValueError:
            pass

    # Pattern 3: YYYY-MM-DD_HH-MM-SS
    pattern3 = r"(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})"
    match = re.search(pattern3, filename)
    if match:
        try:
            date_str = match.group(1).replace("-", "")
            time_str = match.group(2).replace("-", "")
            return datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
        except ValueError:
            pass

    # Pattern 4: YYYYMMDDHHMMSS (no separators, no prefix)
    pattern4 = r"(\d{14})"
    match = re.search(pattern4, filename)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y%m%d%H%M%S")
        except ValueError:
            pass

    return None


def _sort_files_by_timestamp(files: list[UploadFile]) -> list[UploadFile]:
    """
    Sort files by timestamp (earliest first).
    Tries to extract timestamp from filename, falls back to original order.
    """
    files_with_timestamps: list[tuple[UploadFile, datetime | None]] = []

    for file in files:
        timestamp = None
        if file.filename:
            timestamp = _extract_timestamp_from_filename(file.filename)

        files_with_timestamps.append((file, timestamp))

    # Sort: files with timestamps first (sorted by timestamp), then files without
    files_with_ts = [(f, ts) for f, ts in files_with_timestamps if ts is not None]
    files_without_ts = [(f, ts) for f, ts in files_with_timestamps if ts is None]

    # Sort files with timestamps by timestamp (earliest first)
    files_with_ts.sort(key=lambda x: x[1])  # type: ignore

    # Combine: timestamped files first (in order), then others (original order)
    sorted_files = [f for f, _ in files_with_ts] + [f for f, _ in files_without_ts]

    return sorted_files


@router.post("/audio/bulk", response_model=BulkUploadResponse, status_code=201)
async def upload_audio_bulk(
    request: Request,
    files: list[UploadFile] = File(..., description="Multiple audio files to upload"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
    stt_service: SttService = Depends(get_stt_service),
) -> BulkUploadResponse:
    """
    Upload multiple audio files at once.
    Files are processed in timestamp order (earliest first) to maintain context.
    Timestamp is inferred from filename patterns like: recording_20240102_103045.wav
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    if len(files) > 50:  # Reasonable limit
        raise HTTPException(
            status_code=400, detail="Maximum 50 files allowed per request"
        )

    # Sort files by timestamp (earliest first) for proper task context
    sorted_files = _sort_files_by_timestamp(files)

    logger.info(
        f"Bulk upload: processing {len(sorted_files)} files in timestamp order",
        extra={
            "extra_data": {
                "file_count": len(sorted_files),
                "filenames": [f.filename for f in sorted_files],
            }
        },
    )

    storage_dir = ensure_storage_dir()
    user = current_user  # Use authenticated user from Clerk

    results: list[BulkUploadResult] = []
    successful = 0
    failed = 0

    for audio in sorted_files:
        try:
            if not audio.filename:
                results.append(
                    BulkUploadResult(
                        success=False, file_name="unknown", error="Missing filename"
                    )
                )
                failed += 1
                continue

            # Save file
            file_extension = Path(audio.filename).suffix or ".wav"
            unique_name = f"{uuid.uuid4().hex}{file_extension}"
            stored_path = storage_dir / unique_name

            with stored_path.open("wb") as destination:
                shutil.copyfileobj(audio.file, destination)

            # Initialize processing stages for progress tracking
            from datetime import datetime

            processing_stages = {
                "uploaded": {
                    "status": "completed",
                    "timestamp": datetime.utcnow().isoformat(),
                },
                "transcribing": {"status": "pending", "timestamp": None},
                "diarizing": {"status": "pending", "timestamp": None},
                "summarizing": {"status": "pending", "timestamp": None},
                "extracting_tasks": {"status": "pending", "timestamp": None},
                "tagging": {"status": "pending", "timestamp": None},
                "review": {"status": "pending", "timestamp": None},
                "syncing_tasks": {"status": "pending", "timestamp": None},
            }

            # Create session
            session_record = SessionModel(
                user_id=user.id,
                audio_path=str(stored_path),
                status="pending",
                processing_stages=processing_stages,
            )
            db.add(session_record)
            db.flush()

            # Create transcription
            transcription = TranscriptionModel(
                session_id=session_record.id, status="pending"
            )
            db.add(transcription)
            db.flush()

            # Submit to STT provider
            try:
                webhook_url = str(request.url_for("elevenlabs_webhook"))
                metadata = {
                    "session_id": session_record.id,
                    "transcription_id": transcription.id,
                }

                submission = stt_service.submit_transcription(
                    audio_path=stored_path,
                    webhook_url=webhook_url,
                    metadata=metadata,
                )

                # Handle synchronous vs asynchronous transcription
                is_sync = submission.get("is_sync", False)

                if is_sync:
                    # Synchronous transcription (Groq)
                    transcription.text = submission.get("transcription_text", "")
                    transcription.status = "completed"
                    transcription.provider = submission.get("provider", "unknown")
                    session_record.status = "processing"
                    session_record.last_transcribed_at = datetime.utcnow()

                    # Update processing stages
                    processing_stages["transcribing"] = {
                        "status": "completed",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    processing_stages["diarizing"] = {
                        "status": (
                            "completed"
                            if not stt_service.supports_diarization()
                            else "skipped"
                        ),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    session_record.processing_stages = processing_stages
                    delete_session_audio_file(session_record)

                    # Trigger LLM processing
                    db.commit()
                    db.refresh(session_record)
                    db.refresh(transcription)
                    asyncio.create_task(
                        schedule_summary_and_todos(session_record.id, transcription.id)
                    )
                else:
                    # Asynchronous transcription (ElevenLabs, Mock)
                    transcription.provider_job_id = submission.get("request_id")
                    transcription.provider = submission.get("provider", "unknown")
                    transcription.status = "submitted"
                    session_record.status = "processing"

                    # For mock/dev mode, trigger webhook
                    if settings.developer_mode:
                        asyncio.create_task(
                            _trigger_mock_webhook(session_record.id, transcription.id)
                        )

            except (SttNotConfiguredError, SttError) as e:
                transcription.status = "error"
                transcription.error = str(e)
                session_record.status = "error"
                session_record.last_error = str(e)

            db.commit()
            db.refresh(session_record)

            results.append(
                BulkUploadResult(
                    success=True, file_name=audio.filename, session_id=session_record.id
                )
            )
            successful += 1

        except Exception as e:
            logger.exception(
                f"Failed to process file {audio.filename if audio else 'unknown'}"
            )
            results.append(
                BulkUploadResult(
                    success=False,
                    file_name=audio.filename if audio and audio.filename else "unknown",
                    error=str(e),
                )
            )
            failed += 1

    logger.info(
        f"Bulk upload completed: {successful} successful, {failed} failed out of {len(files)} files",
        extra={"successful": successful, "failed": failed, "total": len(files)},
    )

    return BulkUploadResponse(
        total=len(files), successful=successful, failed=failed, results=results
    )
