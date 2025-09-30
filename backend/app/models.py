from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
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
    name = Column(String, nullable=False, unique=True)

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class Session(Base, TimestampMixin):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    description = Column(String, nullable=True)
    audio_path = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")
    last_error = Column(Text, nullable=True)
    last_transcribed_at = Column(DateTime, nullable=True)
    has_pj = Column(Boolean, default=False, nullable=False)
    summary_run_id = Column(Integer, ForeignKey("llm_runs.id"), nullable=True)
    todo_count = Column(Integer, default=0, nullable=False)

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


__all__ = [
    "User",
    "Session",
    "Transcription",
    "SpeakerProfile",
    "SpeakerSegment",
    "LlmRun",
    "Todo",
]
