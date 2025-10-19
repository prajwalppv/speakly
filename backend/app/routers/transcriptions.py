"""
Transcription management endpoints.

Provides APIs for editing transcriptions and viewing edit history.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_session
from ..models import Transcription, TranscriptionEdit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/transcriptions", tags=["transcriptions"])


# Request/Response schemas
class EditTranscriptionRequest(BaseModel):
    text: str
    user_id: int = 1  # Default user for now
    notes: str | None = None


class TranscriptionEditResponse(BaseModel):
    id: int
    transcription_id: int
    user_id: int
    previous_text: str
    new_text: str
    edit_type: str
    notes: str | None
    created_at: str
    updated_at: str


class TranscriptionResponse(BaseModel):
    id: int
    text: str | None
    status: str
    edit_count: int
    last_edited_at: str | None


@router.put("/{transcription_id}", response_model=TranscriptionResponse)
def edit_transcription(
    transcription_id: int,
    request: EditTranscriptionRequest,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """
    Edit a transcription and save to history.

    Args:
        transcription_id: ID of transcription to edit
        request: Edit request with new text
        db: Database session

    Returns:
        Updated transcription data

    Raises:
        HTTPException: 404 if transcription not found
    """
    transcription = (
        db.query(Transcription).filter(Transcription.id == transcription_id).first()
    )

    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcription {transcription_id} not found",
        )

    # Save edit to history
    edit = TranscriptionEdit(
        transcription_id=transcription_id,
        user_id=request.user_id,
        previous_text=transcription.text or "",
        new_text=request.text,
        edit_type="manual",
        notes=request.notes,
    )
    db.add(edit)

    # Update transcription
    transcription.text = request.text
    db.commit()
    db.refresh(transcription)

    logger.info(
        f"Transcription {transcription_id} edited by user {request.user_id}",
        extra={
            "transcription_id": transcription_id,
            "user_id": request.user_id,
            "edit_length": len(request.text),
        },
    )

    # Get edit count and last edit time
    edits = (
        db.query(TranscriptionEdit)
        .filter(TranscriptionEdit.transcription_id == transcription_id)
        .order_by(TranscriptionEdit.created_at.desc())
        .all()
    )

    return {
        "id": transcription.id,
        "text": transcription.text,
        "status": transcription.status,
        "edit_count": len(edits),
        "last_edited_at": edits[0].created_at.isoformat() if edits else None,
    }


@router.get(
    "/{transcription_id}/history", response_model=list[TranscriptionEditResponse]
)
def get_edit_history(
    transcription_id: int,
    db: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    """
    Get edit history for a transcription.

    Args:
        transcription_id: ID of transcription
        db: Database session

    Returns:
        List of edits in reverse chronological order

    Raises:
        HTTPException: 404 if transcription not found
    """
    transcription = (
        db.query(Transcription).filter(Transcription.id == transcription_id).first()
    )

    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcription {transcription_id} not found",
        )

    edits = (
        db.query(TranscriptionEdit)
        .filter(TranscriptionEdit.transcription_id == transcription_id)
        .order_by(TranscriptionEdit.created_at.desc())
        .all()
    )

    return [
        {
            "id": edit.id,
            "transcription_id": edit.transcription_id,
            "user_id": edit.user_id,
            "previous_text": edit.previous_text,
            "new_text": edit.new_text,
            "edit_type": edit.edit_type,
            "notes": edit.notes,
            "created_at": edit.created_at.isoformat(),
            "updated_at": edit.updated_at.isoformat(),
        }
        for edit in edits
    ]
