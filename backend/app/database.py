from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_database() -> None:
    """Create tables if they do not exist."""
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_session_columns()


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
        statements.append("ALTER TABLE sessions ADD COLUMN last_transcribed_at DATETIME")

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
