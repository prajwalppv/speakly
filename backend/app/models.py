from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
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

    user = relationship("User", back_populates="sessions")
    transcriptions = relationship(
        "Transcription",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Transcription.created_at",
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

    session = relationship("Session", back_populates="transcriptions")


__all__ = ["User", "Session", "Transcription"]
