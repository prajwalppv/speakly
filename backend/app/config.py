from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
AUDIO_STORAGE_DIR = PROJECT_ROOT / "storage" / "audio"
DEFAULT_DB_PATH = DATA_DIR / "app.db"


class Settings(BaseSettings):
    """Runtime configuration for the Speakly backend."""

    environment: Literal["dev", "prod", "test"] = Field(
        default="dev", validation_alias="SPEAKLY_ENVIRONMENT"
    )
    database_url: str = Field(
        default=f"sqlite:///{DEFAULT_DB_PATH}", validation_alias="SPEAKLY_DATABASE_URL"
    )
    audio_storage_dir: Path = Field(default=AUDIO_STORAGE_DIR, validation_alias="SPEAKLY_AUDIO_DIR")
    log_level: str = Field(default="INFO", validation_alias="SPEAKLY_LOG_LEVEL")
    
    # ElevenLabs STT (optional - only needed if using elevenlabs provider)
    elevenlabs_api_key: str | None = Field(default=None, validation_alias="ELEVENLABS_API_KEY")
    elevenlabs_base_url: str = Field(
        default="https://api.elevenlabs.io", validation_alias="ELEVENLABS_BASE_URL"
    )
    elevenlabs_webhook_secret: str | None = Field(
        default=None, validation_alias="ELEVENLABS_WEBHOOK_SECRET"
    )
    elevenlabs_webhook_id: str | None = Field(
        default=None, validation_alias="ELEVENLABS_WEBHOOK_ID"
    )
    elevenlabs_diarization_enabled: bool = Field(
        default=True, validation_alias="ELEVENLABS_DIARIZATION_ENABLED"
    )
    elevenlabs_diarization_threshold: float | None = Field(
        default=None, validation_alias="ELEVENLABS_DIARIZATION_THRESHOLD"
    )
    
    pj_profile_name: str = Field(default="PJ", validation_alias="PJ_PROFILE_NAME")
    pj_voice_tags: str = Field(default="pj,patrick", validation_alias="PJ_VOICE_TAGS")
    
    # Speech-to-Text Provider Configuration
    stt_provider: Literal["auto", "groq", "elevenlabs", "mock"] = Field(
        default="auto", 
        validation_alias="SPEAKLY_STT_PROVIDER",
        description="STT provider: auto (prefer Groq), groq (Whisper), elevenlabs (Scribe), mock (dev mode)"
    )
    
    # LLM Configuration (Groq for production, Ollama for local dev)
    groq_api_key: str | None = Field(default=None, validation_alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", validation_alias="GROQ_MODEL")
    groq_chunk_duration_seconds: int = Field(
        default=600,
        validation_alias="GROQ_CHUNK_DURATION_SECONDS",
        description="Chunk length (seconds) when splitting large audio for Groq STT"
    )
    groq_max_file_mb: float = Field(
        default=24.0,
        validation_alias="GROQ_MAX_FILE_MB",
        description="Maximum file size in megabytes to send to Groq STT without chunking"
    )
    ollama_base_url: str | None = Field(default=None, validation_alias="OLLAMA_BASE_URL")
    ollama_model_summary: str = Field(default="llama3", validation_alias="OLLAMA_MODEL_SUMMARY")
    ollama_model_todo: str = Field(default="llama3", validation_alias="OLLAMA_MODEL_TODO")
    llm_provider: Literal["auto", "groq", "ollama", "none"] = Field(
        default="auto", validation_alias="SPEAKLY_LLM_PROVIDER"
    )
    
    # LLM Rate Limiting and Retry Configuration
    llm_max_concurrent_requests: int = Field(
        default=1,  # Reduced from 3 to prevent overwhelming API (each session makes 4 calls)
        validation_alias="SPEAKLY_LLM_MAX_CONCURRENT_REQUESTS",
        description="Maximum number of concurrent LLM API requests"
    )
    llm_retry_max_attempts: int = Field(
        default=5,
        validation_alias="SPEAKLY_LLM_RETRY_MAX_ATTEMPTS",
        description="Maximum number of retry attempts for failed LLM requests"
    )
    llm_retry_min_wait_seconds: int = Field(
        default=2,  # Increased from 1 to give API more recovery time
        validation_alias="SPEAKLY_LLM_RETRY_MIN_WAIT_SECONDS",
        description="Minimum wait time in seconds between retries"
    )
    llm_retry_max_wait_seconds: int = Field(
        default=60,
        validation_alias="SPEAKLY_LLM_RETRY_MAX_WAIT_SECONDS",
        description="Maximum wait time in seconds between retries"
    )
    
    todo_confidence_threshold: float = Field(
        default=0.35, validation_alias="TODO_CONFIDENCE_THRESHOLD"
    )
    developer_mode: bool = Field(default=False, validation_alias="SPEAKLY_DEVELOPER_MODE")

    # Journey report email delivery (Brevo)
    report_email_enabled: bool = Field(
        default=False, validation_alias="REPORT_EMAIL_ENABLED"
    )
    report_email_from_email: str | None = Field(
        default=None, validation_alias="REPORT_EMAIL_FROM_EMAIL"
    )
    report_email_from_name: str | None = Field(
        default=None, validation_alias="REPORT_EMAIL_FROM_NAME"
    )
    brevo_api_key: str | None = Field(default=None, validation_alias="BREVO_API_KEY")
    
    # Clerk Authentication (backend only needs secret key for JWT verification)
    clerk_secret_key: str | None = Field(default=None, validation_alias="CLERK_SECRET_KEY")
    
    # TickTick Integration
    ticktick_enabled: bool = Field(default=False, validation_alias="TICKTICK_ENABLED")
    ticktick_client_id: str | None = Field(default=None, validation_alias="TICKTICK_CLIENT_ID")
    ticktick_client_secret: str | None = Field(default=None, validation_alias="TICKTICK_CLIENT_SECRET")
    ticktick_redirect_uri: str = Field(
        default="http://localhost:8000/api/ticktick/callback",
        validation_alias="TICKTICK_REDIRECT_URI"
    )
    ticktick_base_url: str = Field(
        default="https://api.ticktick.com/open/v1",
        validation_alias="TICKTICK_BASE_URL"
    )
    frontend_base_url: str = Field(
        default="http://localhost:5173",
        validation_alias="SPEAKLY_FRONTEND_URL"
    )
    
    # Feature Flags (for monetization/rollout control)
    feature_auto_tagging: bool = Field(default=True, validation_alias="SPEAKLY_FEATURE_AUTO_TAGGING")
    feature_custom_tags: bool = Field(default=True, validation_alias="SPEAKLY_FEATURE_CUSTOM_TAGS")
    feature_advanced_search: bool = Field(default=True, validation_alias="SPEAKLY_FEATURE_ADVANCED_SEARCH")
    feature_report_generation: bool = Field(default=False, validation_alias="SPEAKLY_FEATURE_REPORT_GENERATION")
    feature_command_palette: bool = Field(default=True, validation_alias="SPEAKLY_FEATURE_COMMAND_PALETTE")

    # Tagging Configuration
    max_tags_per_session: int = Field(default=5, validation_alias="SPEAKLY_MAX_TAGS_PER_SESSION")

    # Usage Limits (for free tier)
    free_recordings_per_month: int = Field(default=10, validation_alias="SPEAKLY_FREE_RECORDINGS_PER_MONTH")
    free_tasks_per_session: int = Field(default=3, validation_alias="SPEAKLY_FREE_TASKS_PER_SESSION")
    free_tags_per_session: int = Field(default=3, validation_alias="SPEAKLY_FREE_TAGS_PER_SESSION")

    # CORS configuration
    cors_origins: str = Field(
        default="http://localhost:5173,https://speakly-frontend.fly.dev",
        validation_alias="SPEAKLY_CORS_ORIGINS",
    )

    # Configuration prioritizes environment variables over .env files
    # In production: all config from Fly.io secrets (environment variables)
    # In local dev: use docker-compose.yml or .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

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
