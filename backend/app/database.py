from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

engine = create_engine(
    settings.database_url,
    connect_args=(
        {"check_same_thread": False}
        if settings.database_url.startswith("sqlite")
        else {}
    ),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_database() -> None:
    """Create tables if they do not exist."""
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_session_columns()
    _ensure_transcription_columns()


def _ensure_session_columns() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("sessions"):
        return

    existing = {column["name"] for column in inspector.get_columns("sessions")}
    statements: list[str] = []
    if "status" not in existing:
        statements.append(
            "ALTER TABLE sessions ADD COLUMN status VARCHAR NOT NULL DEFAULT 'pending'"
        )
    if "last_error" not in existing:
        statements.append("ALTER TABLE sessions ADD COLUMN last_error TEXT")
    if "last_transcribed_at" not in existing:
        statements.append(
            "ALTER TABLE sessions ADD COLUMN last_transcribed_at DATETIME"
        )
    if "has_pj" not in existing:
        statements.append(
            "ALTER TABLE sessions ADD COLUMN has_pj BOOLEAN NOT NULL DEFAULT 0"
        )
    if "summary_run_id" not in existing:
        statements.append("ALTER TABLE sessions ADD COLUMN summary_run_id INTEGER")
    if "todo_count" not in existing:
        statements.append(
            "ALTER TABLE sessions ADD COLUMN todo_count INTEGER NOT NULL DEFAULT 0"
        )

    if not statements:
        return

    with engine.begin() as connection:
        for stmt in statements:
            connection.execute(text(stmt))


def _ensure_transcription_columns() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("transcriptions"):
        return

    existing = {column["name"] for column in inspector.get_columns("transcriptions")}
    statements: list[str] = []
    if "duration_ms" not in existing:
        statements.append("ALTER TABLE transcriptions ADD COLUMN duration_ms INTEGER")
    if "channel_count" not in existing:
        statements.append("ALTER TABLE transcriptions ADD COLUMN channel_count INTEGER")

    if not statements:
        return

    with engine.begin() as connection:
        for stmt in statements:
            connection.execute(text(stmt))


def get_session() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = ["Base", "engine", "SessionLocal", "get_session", "init_database"]
