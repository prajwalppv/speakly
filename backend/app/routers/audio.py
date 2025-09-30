from __future__ import annotations

import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_session
from ..models import Session as SessionModel
from ..models import User
from ..schemas import AudioUploadResponse

router = APIRouter(prefix="/api", tags=["audio"])


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
    audio: Annotated[UploadFile, File(description="Audio file to upload")],
    db: Session = Depends(get_session),
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
    session_record = SessionModel(user_id=user.id, audio_path=str(stored_path))
    db.add(session_record)
    db.commit()
    db.refresh(session_record)

    return AudioUploadResponse(
        file_name=audio.filename,
        file_path=stored_path,
        session_id=session_record.id,
        received_at=datetime.utcnow(),
    )
