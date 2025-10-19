from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ConfigDict

from .models import ReportCadence, ReportStatus


# Base model with proper datetime serialization (always UTC with 'Z')
class UTCBaseModel(BaseModel):
    """Base model that serializes datetime fields with UTC indicator."""
    
    model_config = ConfigDict(
        json_schema_extra={},
        ser_json_timedelta='iso8601',
    )
    
    def model_dump(self, **kwargs):
        """Override to add 'Z' to datetime fields."""
        data = super().model_dump(**kwargs)
        # Add 'Z' suffix to any datetime strings
        for key, value in data.items():
            if isinstance(value, str) and 'T' in value and not value.endswith('Z'):
                # This is likely an ISO datetime without timezone
                data[key] = value + 'Z'
        return data


class APIError(UTCBaseModel):
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


class TranscriptionResponse(UTCBaseModel):
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


class TaskUpdateInfo(BaseModel):
    """Information about a task update from voice note."""
    title: str
    status: str
    notes: str | None
    confidence: float
    source_excerpt: str | None
    matched_task_id: str | None = None
    matched_title: str | None = None
    match_score: int | None = None
    match_quality: str | None = None
    auto_updated: bool = False


class TodoResponse(UTCBaseModel):
    id: int
    title: str
    due_hint: str | None = None
    confidence: float | None = None
    status: str
    source_start_ms: int | None = None
    source_end_ms: int | None = None
    source_excerpt: str | None = None
    ticktick_sync_status: str = "pending"
    ticktick_task_id: str | None = None
    ticktick_synced_at: datetime | None = None
    ticktick_sync_error: str | None = None
    created_at: datetime
    updated_at: datetime


class SummaryResponse(BaseModel):
    id: int
    model: str
    text: str | None
    status: str
    updated_at: datetime
    task_updates: list[dict] | None = None  # Task updates found in this session


class TagResponse(UTCBaseModel):
    """Response model for tag."""
    id: int
    name: str
    category: str
    color: str
    auto_generated: bool
    usage_count: int = 0
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TagCreate(BaseModel):
    """Request model for creating a custom tag."""
    name: str = Field(..., min_length=1, max_length=50)
    category: str | None = Field(default="custom")
    color: str | None = None


class SessionResponse(UTCBaseModel):
    id: int
    status: str
    review_status: str
    description: str | None
    audio_path: Path | None
    last_error: str | None
    last_transcribed_at: datetime | None
    reviewed_at: datetime | None = None
    has_pj: bool
    todo_count: int
    task_updates_count: int = 0  # Number of task updates processed
    processing_stages: dict | None = None  # Track processing progress
    created_at: datetime
    updated_at: datetime
    transcriptions: list[TranscriptionResponse]
    speaker_segments: list[SpeakerSegmentResponse]
    summary: SummaryResponse | None
    todos: list[TodoResponse]
    tags: list[TagResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


class UserPreferencesResponse(UTCBaseModel):
    auto_approve_sessions: bool


class UserPreferencesUpdateRequest(BaseModel):
    auto_approve_sessions: bool


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


class ReportPreferenceRequest(BaseModel):
    cadence: ReportCadence = Field(default=ReportCadence.WEEKLY)
    timezone: str | None = Field(default=None, description="IANA timezone, defaults to UTC")
    delivery_channels: list[str] | None = Field(default=None)
    is_active: bool = Field(default=True)
    email_enabled: bool = Field(default=True)


class ReportPreferenceResponse(UTCBaseModel):
    id: int
    user_id: int
    cadence: ReportCadence
    timezone: str
    delivery_channels: list[str] | None
    is_active: bool
    email_enabled: bool
    last_generated_at: datetime | None
    next_scheduled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportResponse(UTCBaseModel):
    id: int
    user_id: int
    preference_id: int | None
    cadence: ReportCadence
    period_start: datetime
    period_end: datetime
    status: ReportStatus
    summary: str | None
    payload: dict[str, Any] | None
    metadata: dict[str, Any] | None = Field(default=None, alias="metadata_payload")
    generated_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ReportListResponse(UTCBaseModel):
    reports: list[ReportResponse]
    total: int


class ReportGenerateRequest(BaseModel):
    cadence: ReportCadence | None = Field(
        default=None,
        description="Optional cadence override. Defaults to the user's preference.",
    )
    period_start: datetime | None = Field(
        default=None,
        description="Optional override for report period start (UTC). Defaults to cadence window.",
    )
    period_end: datetime | None = Field(
        default=None,
        description="Optional override for report period end (UTC). Defaults to now.",
    )


__all__ = [
    "APIError",
    "AudioUploadResponse",
    "TranscriptionResponse",
    "SpeakerSegmentResponse",
    "TodoResponse",
    "SummaryResponse",
    "SessionResponse",
    "ElevenLabsWebhookPayload",
    "TagResponse",
    "TagCreate",
    "ReportPreferenceRequest",
    "ReportPreferenceResponse",
    "ReportResponse",
    "ReportListResponse",
    "ReportGenerateRequest",
    "UserPreferencesResponse",
    "UserPreferencesUpdateRequest",
]
