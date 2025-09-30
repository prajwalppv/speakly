from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class APIError(BaseModel):
    type: str = Field(..., description="Short machine-readable error label")
    message: str = Field(..., description="Human-readable description of the error")
    details: dict | None = Field(default=None, description="Optional additional context")
    debug: dict | None = Field(default=None, description="Developer-only debug payload")


class AudioUploadResponse(BaseModel):
    status: str = Field(default="received")
    file_name: str
    file_path: Path
    session_id: int | None = None
    received_at: datetime
    session_status: str
    transcription_id: int | None = None
    transcription_status: str | None = None
    developer_message: str | None = None


class TranscriptionResponse(BaseModel):
    id: int
    status: str
    text: str | None
    provider: str
    provider_job_id: str | None
    error: str | None
    metadata: dict | None
    duration_ms: int | None
    channel_count: int | None
    created_at: datetime
    updated_at: datetime


class SpeakerSegmentResponse(BaseModel):
    id: int
    speaker_label: str | None
    start_ms: int
    end_ms: int
    confidence: float | None
    is_pj: bool
    channel_index: int | None
    speaker_profile: str | None


class TodoResponse(BaseModel):
    id: int
    title: str
    due_hint: str | None
    confidence: float | None
    status: str
    source_start_ms: int | None
    source_end_ms: int | None
    source_excerpt: str | None
    created_at: datetime
    updated_at: datetime


class SummaryResponse(BaseModel):
    id: int
    model: str
    text: str | None
    status: str
    updated_at: datetime


class SessionResponse(BaseModel):
    id: int
    status: str
    audio_path: Path | None
    last_error: str | None
    last_transcribed_at: datetime | None
    has_pj: bool
    todo_count: int
    created_at: datetime
    updated_at: datetime
    transcriptions: list[TranscriptionResponse]
    speaker_segments: list[SpeakerSegmentResponse]
    summary: SummaryResponse | None
    todos: list[TodoResponse]


class ElevenLabsWebhookTranscription(BaseModel):
    transcription_id: str | None = None
    status: str | None = None
    text: str | None = None
    language_code: str | None = None
    language_probability: float | None = None
    words: list[dict] | None = None
    channel_index: int | None = None
    additional_formats: dict | None = None


class ElevenLabsWebhookData(BaseModel):
    request_id: str | None = None
    transcription: ElevenLabsWebhookTranscription | None = None
    webhook_metadata: dict | None = None


class ElevenLabsWebhookPayload(BaseModel):
    type: str
    event_timestamp: int | None = None
    data: ElevenLabsWebhookData

    @property
    def provider_reference(self) -> str | None:
        transcription = self.data.transcription
        if transcription and transcription.transcription_id:
            return transcription.transcription_id
        return self.data.request_id

    @property
    def status(self) -> str:
        transcription = self.data.transcription
        if transcription and transcription.status:
            return transcription.status
        if self.type.endswith("failed"):
            return "error"
        return "completed"

    @property
    def text(self) -> str | None:
        transcription = self.data.transcription
        return transcription.text if transcription else None

    @property
    def metadata(self) -> dict | None:
        if self.data.webhook_metadata:
            return self.data.webhook_metadata
        transcription = self.data.transcription
        if transcription:
            return {
                key: value
                for key, value in transcription.model_dump(exclude_none=True).items()
                if key not in {"text"}
            }
        return None


__all__ = [
    "APIError",
    "AudioUploadResponse",
    "TranscriptionResponse",
    "SpeakerSegmentResponse",
    "TodoResponse",
    "SummaryResponse",
    "SessionResponse",
    "ElevenLabsWebhookPayload",
]
