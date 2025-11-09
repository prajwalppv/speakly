"""Utilities for cleaning up stored audio files."""

from __future__ import annotations

import logging
from pathlib import Path

from ..models import Session as SessionModel

logger = logging.getLogger(__name__)


def delete_session_audio_file(session: SessionModel) -> bool:
    """
    Delete the stored audio file for a session and clear the DB reference.

    Returns True if the session was updated (file deleted or path cleared).
    """
    audio_path_value = session.audio_path
    if not audio_path_value:
        return False

    audio_path = Path(audio_path_value)
    try:
        if audio_path.exists():
            audio_path.unlink()
            logger.info(
                "Deleted audio file",
                extra={
                    "extra_data": {
                        "session_id": session.id,
                        "path": str(audio_path),
                    }
                },
            )
        session.audio_path = None
        return True
    except Exception as exc:  # pragma: no cover - best-effort cleanup
        logger.warning(
            "Failed to delete audio file",
            extra={
                "extra_data": {
                    "session_id": session.id,
                    "path": str(audio_path),
                    "error": str(exc),
                }
            },
        )
        return False
