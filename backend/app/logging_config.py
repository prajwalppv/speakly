from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from logging.config import dictConfig

from .config import LOG_DIR, settings


class JsonFormatter(logging.Formatter):
    """Render logs in a structured JSON format."""

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - trivial
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        if record.args:
            log_record["args"] = record.args
        if hasattr(record, "extra_data"):
            log_record.update(getattr(record, "extra_data"))
        return json.dumps(log_record)


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "speakly.log"
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": JsonFormatter,
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "stream": sys.stdout,
                    "formatter": "json",
                },
                "file": {
                    "class": "logging.FileHandler",
                    "filename": str(log_file),
                    "formatter": "json",
                },
            },
            "root": {
                "handlers": ["console", "file"],
                "level": settings.log_level,
            },
            "loggers": {
                "uvicorn": {
                    "handlers": ["console", "file"],
                    "level": settings.log_level,
                    "propagate": False,
                }
            },
        }
    )


__all__ = ["configure_logging"]
