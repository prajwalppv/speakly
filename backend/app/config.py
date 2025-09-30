from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseSettings, Field


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
AUDIO_STORAGE_DIR = PROJECT_ROOT / "storage" / "audio"
DEFAULT_DB_PATH = DATA_DIR / "app.db"


class Settings(BaseSettings):
    """Runtime configuration for the Speakly backend."""

    environment: Literal["dev", "prod", "test"] = Field(
        default="dev", env="SPEAKLY_ENVIRONMENT"
    )
    database_url: str = Field(
        default=f"sqlite:///{DEFAULT_DB_PATH}", env="SPEAKLY_DATABASE_URL"
    )
    audio_storage_dir: Path = Field(default=AUDIO_STORAGE_DIR, env="SPEAKLY_AUDIO_DIR")
    log_level: str = Field(default="INFO", env="SPEAKLY_LOG_LEVEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


__all__ = [
    "Settings",
    "settings",
    "PROJECT_ROOT",
    "DATA_DIR",
    "LOG_DIR",
    "AUDIO_STORAGE_DIR",
]
