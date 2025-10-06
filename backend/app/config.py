from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


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
    
    # LLM Configuration (Groq for production, Ollama for local dev)
    groq_api_key: str | None = Field(default=None, env="GROQ_API_KEY")
    groq_model: str = Field(default="deepseek-r1-distill-llama-70b", env="GROQ_MODEL")
    ollama_base_url: str | None = Field(default=None, env="OLLAMA_BASE_URL")
    ollama_model_summary: str = Field(default="llama3", env="OLLAMA_MODEL_SUMMARY")
    ollama_model_todo: str = Field(default="llama3", env="OLLAMA_MODEL_TODO")
    llm_provider: Literal["auto", "groq", "ollama", "none"] = Field(
        default="auto", env="SPEAKLY_LLM_PROVIDER"
    )
    
    todo_confidence_threshold: float = Field(
        default=0.35, env="TODO_CONFIDENCE_THRESHOLD"
    )
    developer_mode: bool = Field(default=False, env="SPEAKLY_DEVELOPER_MODE")
    
    # Clerk Authentication (backend only needs secret key for JWT verification)
    clerk_secret_key: str | None = Field(default=None, env="CLERK_SECRET_KEY")
    
    # TickTick Integration
    ticktick_enabled: bool = Field(default=False, env="TICKTICK_ENABLED")
    ticktick_client_id: str | None = Field(default=None, env="TICKTICK_CLIENT_ID")
    ticktick_client_secret: str | None = Field(default=None, env="TICKTICK_CLIENT_SECRET")
    ticktick_redirect_uri: str = Field(
        default="http://localhost:8000/api/ticktick/callback",
        env="TICKTICK_REDIRECT_URI"
    )
    ticktick_base_url: str = Field(
        default="https://api.ticktick.com/open/v1",
        env="TICKTICK_BASE_URL"
    )
    frontend_base_url: str = Field(
        default="http://localhost:5173",
        env="SPEAKLY_FRONTEND_URL"
    )
    
    # Feature Flags (for monetization/rollout control)
    feature_auto_tagging: bool = Field(default=True, env="SPEAKLY_FEATURE_AUTO_TAGGING")
    feature_custom_tags: bool = Field(default=True, env="SPEAKLY_FEATURE_CUSTOM_TAGS")
    feature_advanced_search: bool = Field(default=True, env="SPEAKLY_FEATURE_ADVANCED_SEARCH")
    feature_report_generation: bool = Field(default=False, env="SPEAKLY_FEATURE_REPORT_GENERATION")
    feature_command_palette: bool = Field(default=True, env="SPEAKLY_FEATURE_COMMAND_PALETTE")

    # Tagging Configuration
    max_tags_per_session: int = Field(default=5, env="SPEAKLY_MAX_TAGS_PER_SESSION")

    # Usage Limits (for free tier)
    free_recordings_per_month: int = Field(default=10, env="SPEAKLY_FREE_RECORDINGS_PER_MONTH")
    free_tasks_per_session: int = Field(default=3, env="SPEAKLY_FREE_TASKS_PER_SESSION")
    free_tags_per_session: int = Field(default=3, env="SPEAKLY_FREE_TAGS_PER_SESSION")

    # CORS configuration
    cors_origins: str = Field(
        default="http://localhost:5173,https://speakly-frontend.fly.dev",
        env="SPEAKLY_CORS_ORIGINS",
    )

    # Explicitly disable env_file to prevent it from overriding environment variables
    # In production, all config comes from environment variables (Fly.io secrets)
    # In local dev, use docker-compose.yml or export variables manually
    model_config = {
        "case_sensitive": False,
    }

    @property
    def pj_voice_tag_set(self) -> set[str]:
        return {tag.strip().lower() for tag in self.pj_voice_tags.split(",") if tag.strip()}

    @property
    def cors_origin_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if not raw or raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


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
