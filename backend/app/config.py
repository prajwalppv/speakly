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
    elevenlabs_api_key: str | None = Field(default=None, env="ELEVENLABS_API_KEY")
    elevenlabs_base_url: str = Field(
        default="https://api.elevenlabs.io", env="ELEVENLABS_BASE_URL"
    )
    elevenlabs_webhook_secret: str | None = Field(
        default=None, env="ELEVENLABS_WEBHOOK_SECRET"
    )
    elevenlabs_webhook_id: str | None = Field(
        default=None, env="ELEVENLABS_WEBHOOK_ID"
    )
    elevenlabs_diarization_enabled: bool = Field(
        default=True, env="ELEVENLABS_DIARIZATION_ENABLED"
    )
    elevenlabs_diarization_threshold: float | None = Field(
        default=None, env="ELEVENLABS_DIARIZATION_THRESHOLD"
    )
    pj_profile_name: str = Field(default="PJ", env="PJ_PROFILE_NAME")
    pj_voice_tags: str = Field(default="pj,patrick", env="PJ_VOICE_TAGS")
    ollama_base_url: str | None = Field(default=None, env="OLLAMA_BASE_URL")
    ollama_model_summary: str = Field(default="llama3", env="OLLAMA_MODEL_SUMMARY")
    ollama_model_todo: str = Field(default="llama3", env="OLLAMA_MODEL_TODO")
    todo_confidence_threshold: float = Field(
        default=0.35, env="TODO_CONFIDENCE_THRESHOLD"
    )
    developer_mode: bool = Field(default=False, env="SPEAKLY_DEVELOPER_MODE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def pj_voice_tag_set(self) -> set[str]:
        return {tag.strip().lower() for tag in self.pj_voice_tags.split(",") if tag.strip()}


settings = Settings()


__all__ = [
    "Settings",
    "settings",
    "PROJECT_ROOT",
    "DATA_DIR",
    "LOG_DIR",
    "AUDIO_STORAGE_DIR",
    "DEFAULT_DB_PATH",
]
