from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class APIError(BaseModel):
    type: str = Field(..., description="Short machine-readable error label")
    message: str = Field(..., description="Human-readable description of the error")
    details: dict | None = Field(default=None, description="Optional additional context")


class AudioUploadResponse(BaseModel):
    status: str = Field(default="received")
    file_name: str
    file_path: Path
    session_id: int | None = None
    received_at: datetime


__all__ = ["APIError", "AudioUploadResponse"]
