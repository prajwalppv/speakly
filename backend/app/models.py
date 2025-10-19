from __future__ import annotations

from datetime import datetime
import enum

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import UniqueConstraint
from sqlalchemy.sql import expression
from sqlalchemy.orm import relationship

from .database import Base


class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)  # Display name from Clerk
    email = Column(String, nullable=True, unique=True, index=True)  # Email from Clerk
    clerk_user_id = Column(String, nullable=True, unique=True, index=True)  # Clerk's user ID
    auto_approve_sessions = Column(
        Boolean,
        nullable=False,
        server_default=expression.true(),
        default=True,
    )
    
    # Legacy field for backwards compatibility (kept for migration)
    # Will be removed after all users migrated to Clerk

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    ticktick_token = relationship(
        "TickTickToken", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    report_preferences = relationship(
        "ReportPreference", back_populates="user", cascade="all, delete-orphan", uselist=True
    )
    reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")


class Session(Base, TimestampMixin):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    description = Column(String, nullable=True)
    audio_path = Column(String, nullable=True)  # Temporary storage, deleted after transcription
    status = Column(String, nullable=False, default="pending")
    last_error = Column(Text, nullable=True)
    last_transcribed_at = Column(DateTime, nullable=True)
    has_pj = Column(Boolean, default=False, nullable=False)
    summary_run_id = Column(Integer, ForeignKey("llm_runs.id"), nullable=True)
    todo_count = Column(Integer, default=0, nullable=False)
    processing_stages = Column(JSON, nullable=True)  # Track processing progress
    review_status = Column(String, nullable=False, default="pending")
    reviewed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="sessions")
    transcriptions = relationship(
        "Transcription",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Transcription.created_at",
    )
    speaker_segments = relationship(
        "SpeakerSegment",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SpeakerSegment.start_ms",
    )
    todos = relationship(
        "Todo",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Todo.created_at",
    )
    llm_runs = relationship(
        "LlmRun",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="LlmRun.created_at",
        foreign_keys="LlmRun.session_id",
    )
    summary_run = relationship(
        "LlmRun",
        foreign_keys=[summary_run_id],
        post_update=True,
    )
    session_tags = relationship(
        "SessionTag",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SessionTag.created_at",
    )


class Transcription(Base, TimestampMixin):
    __tablename__ = "transcriptions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    provider = Column(String, nullable=False, default="elevenlabs")
    provider_job_id = Column(String, nullable=True, unique=True)
    status = Column(String, nullable=False, default="pending")
    text = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    metadata_payload = Column(JSON, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    channel_count = Column(Integer, nullable=True)

    session = relationship("Session", back_populates="transcriptions")
    speaker_segments = relationship(
        "SpeakerSegment",
        back_populates="transcription",
        cascade="all, delete-orphan",
    )
    llm_runs = relationship(
        "LlmRun",
        back_populates="transcription",
        foreign_keys="LlmRun.transcription_id",
    )
    edits = relationship(
        "TranscriptionEdit",
        back_populates="transcription",
        cascade="all, delete-orphan",
        order_by="TranscriptionEdit.created_at.desc()",
    )


class TranscriptionEdit(Base, TimestampMixin):
    """Track edit history for transcriptions."""
    __tablename__ = "transcription_edits"

    id = Column(Integer, primary_key=True, index=True)
    transcription_id = Column(Integer, ForeignKey("transcriptions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    previous_text = Column(Text, nullable=False)  # Text before edit
    new_text = Column(Text, nullable=False)  # Text after edit
    edit_type = Column(String, nullable=False, default="manual")  # manual, ai_correction, etc.
    notes = Column(Text, nullable=True)  # Optional notes about the edit

    transcription = relationship("Transcription", back_populates="edits")
    user = relationship("User")


class SpeakerProfile(Base, TimestampMixin):
    __tablename__ = "speaker_profiles"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    external_id = Column(String, nullable=True, unique=True)
    embedding_path = Column(String, nullable=True)
    is_primary = Column(Boolean, default=False, nullable=False)

    segments = relationship("SpeakerSegment", back_populates="speaker_profile")


class SpeakerSegment(Base, TimestampMixin):
    __tablename__ = "speaker_segments"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    transcription_id = Column(
        Integer, ForeignKey("transcriptions.id"), nullable=False, index=True
    )
    speaker_label = Column(String, nullable=True)
    speaker_profile_id = Column(Integer, ForeignKey("speaker_profiles.id"), nullable=True)
    start_ms = Column(Integer, nullable=False)
    end_ms = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=True)
    is_pj = Column(Boolean, default=False, nullable=False)
    channel_index = Column(Integer, nullable=True)
    attributes_json = Column(JSON, nullable=True)

    session = relationship(
        "Session",
        back_populates="speaker_segments",
        foreign_keys=[session_id],
    )
    transcription = relationship(
        "Transcription",
        back_populates="speaker_segments",
        foreign_keys=[transcription_id],
    )
    speaker_profile = relationship("SpeakerProfile", back_populates="segments")


class LlmRun(Base, TimestampMixin):
    __tablename__ = "llm_runs"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    transcription_id = Column(Integer, ForeignKey("transcriptions.id"), nullable=True)
    run_type = Column(String, nullable=False)
    model = Column(String, nullable=False)
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="pending")
    error = Column(Text, nullable=True)
    metadata_payload = Column(JSON, nullable=True)

    session = relationship(
        "Session",
        back_populates="llm_runs",
        foreign_keys=[session_id],
    )
    transcription = relationship(
        "Transcription",
        back_populates="llm_runs",
        foreign_keys=[transcription_id],
    )
    todos = relationship("Todo", back_populates="llm_run", cascade="all, delete-orphan")


class Todo(Base, TimestampMixin):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    llm_run_id = Column(Integer, ForeignKey("llm_runs.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    due_hint = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    status = Column(String, nullable=False, default="pending")
    source_start_ms = Column(Integer, nullable=True)
    source_end_ms = Column(Integer, nullable=True)
    source_excerpt = Column(Text, nullable=True)
    
    # TickTick sync tracking
    ticktick_task_id = Column(String, nullable=True, unique=True)
    ticktick_project_id = Column(String, nullable=True)
    ticktick_synced_at = Column(DateTime, nullable=True)
    ticktick_sync_status = Column(String, default="pending", nullable=False)  # pending, synced, error
    ticktick_sync_error = Column(Text, nullable=True)

    session = relationship(
        "Session",
        back_populates="todos",
        foreign_keys=[session_id],
    )
    llm_run = relationship(
        "LlmRun",
        back_populates="todos",
        foreign_keys=[llm_run_id],
    )


class TickTickToken(Base, TimestampMixin):
    """Stores TickTick OAuth tokens for users."""
    __tablename__ = "ticktick_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)
    token_type = Column(String, default="bearer", nullable=False)
    expires_at = Column(DateTime, nullable=False)
    scope = Column(String, default="tasks:write tasks:read", nullable=False)

    user = relationship("User", back_populates="ticktick_token")


class Tag(Base, TimestampMixin):
    """Tag model for categorizing sessions."""
    
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)  # e.g., "meeting", "urgent"
    category = Column(String, nullable=False)  # "type", "topic", "person", "priority", "context"
    color = Column(String, nullable=False)  # Hex color for UI display
    auto_generated = Column(Boolean, default=True)  # True if created by AI
    
    # Relationships
    session_tags = relationship("SessionTag", back_populates="tag", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name='{self.name}', category='{self.category}')>"


class SessionTag(Base, TimestampMixin):
    """Association table for many-to-many relationship between sessions and tags."""
    
    __tablename__ = "session_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, index=True)
    confidence = Column(Float, default=1.0)  # 0.0-1.0 confidence score for AI-generated tags
    auto_generated = Column(Boolean, default=True)  # True if added by AI, False if manual
    
    # Relationships
    session = relationship("Session", back_populates="session_tags")
    tag = relationship("Tag", back_populates="session_tags")
    
    def __repr__(self) -> str:
        return f"<SessionTag(session_id={self.session_id}, tag_id={self.tag_id}, confidence={self.confidence})>"


class ReportCadence(enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class ReportStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportPreference(Base, TimestampMixin):
    """User-level configuration for Journeys cadence and delivery."""

    __tablename__ = "report_preferences"
    __table_args__ = (UniqueConstraint("user_id", name="uq_report_preferences_user_id"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    cadence = Column(String, nullable=False, default=ReportCadence.WEEKLY.value, server_default=ReportCadence.WEEKLY.value)
    timezone = Column(String, nullable=False, default="UTC", server_default="UTC")
    delivery_channels = Column(JSON, nullable=True, default=list)
    is_active = Column(Boolean, nullable=False, default=True, server_default=expression.true())
    email_enabled = Column(Boolean, nullable=False, default=True, server_default=expression.true())
    last_generated_at = Column(DateTime, nullable=True)
    next_scheduled_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="report_preferences")
    reports = relationship("Report", back_populates="preference", cascade="all, delete-orphan")


class Report(Base, TimestampMixin):
    """Stored generated Journey report."""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    preference_id = Column(Integer, ForeignKey("report_preferences.id"), nullable=True, index=True)
    cadence = Column(String, nullable=False, default=ReportCadence.WEEKLY.value, server_default=ReportCadence.WEEKLY.value)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    status = Column(String, nullable=False, default=ReportStatus.PENDING.value, server_default=ReportStatus.PENDING.value)
    summary = Column(Text, nullable=True)
    payload = Column(JSON, nullable=True)
    metadata_payload = Column(JSON, nullable=True)
    generated_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="reports")
    preference = relationship("ReportPreference", back_populates="reports")


__all__ = [
    "User",
    "Session",
    "Transcription",
    "SpeakerProfile",
    "SpeakerSegment",
    "LlmRun",
    "Todo",
    "TickTickToken",
    "Tag",
    "SessionTag",
    "ReportPreference",
    "Report",
    "ReportCadence",
    "ReportStatus",
]
