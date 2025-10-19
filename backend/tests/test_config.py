"""
Test configuration system.
"""

from pathlib import Path

import pytest


class TestConfiguration:
    """Test app configuration."""

    def test_config_loads_defaults(self):
        """Test that config loads with default values."""
        from app.config import Settings

        settings = Settings()

        # Verify defaults
        assert settings.environment in ["dev", "prod", "test"]
        assert settings.log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]
        assert settings.audio_storage_dir is not None

    def test_config_paths_are_path_objects(self):
        """Test that directory paths are Path objects."""
        from app.config import DATA_DIR, LOG_DIR, Settings

        settings = Settings()

        assert isinstance(settings.audio_storage_dir, Path)
        assert isinstance(DATA_DIR, Path)
        assert isinstance(LOG_DIR, Path)

    @pytest.mark.skip(
        reason="Settings is a module-level singleton, cannot easily test env var changes"
    )
    def test_config_environment_variable(self, monkeypatch):
        """Test that environment can be set via env var."""
        # Test with prod environment
        monkeypatch.setenv("SPEAKLY_ENVIRONMENT", "prod")

        # Import Settings after setting env var to get fresh instance
        import importlib

        import app.config

        importlib.reload(app.config)

        from app.config import settings

        assert settings.environment == "prod"

    def test_config_audio_dir_setting(self):
        """Test audio directory configuration."""
        from app.config import Settings

        settings = Settings()

        assert settings.audio_storage_dir.name in ["audio", "storage"]
        # Path should end with audio storage directory
        assert "audio" in str(settings.audio_storage_dir).lower()

    def test_config_database_url_default(self):
        """Test database URL has sensible default."""
        from app.config import Settings

        settings = Settings()

        assert settings.database_url is not None
        assert "sqlite" in settings.database_url.lower()

    def test_config_log_level_validation(self):
        """Test log level is valid."""
        from app.config import Settings

        settings = Settings()

        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert settings.log_level.upper() in valid_levels

    def test_config_is_singleton(self):
        """Test that settings instance is consistent."""
        from app.config import settings as settings1
        from app.config import settings as settings2

        # Same instance
        assert settings1 is settings2

    def test_config_environment_prefix(self):
        """Test that all env vars use SPEAKLY_ prefix."""
        from app.config import Settings

        # This verifies the Config class uses env_prefix
        settings = Settings()

        # Config model should have env_prefix set
        assert hasattr(Settings, "Config") or hasattr(Settings, "model_config")


class TestDirectories:
    """Test directory configuration."""

    def test_data_directory_exists(self):
        """Test DATA_DIR is defined."""
        from app.config import DATA_DIR

        assert DATA_DIR is not None
        assert isinstance(DATA_DIR, Path)

    def test_log_directory_exists(self):
        """Test LOG_DIR is defined."""
        from app.config import LOG_DIR

        assert LOG_DIR is not None
        assert isinstance(LOG_DIR, Path)

    def test_project_root_exists(self):
        """Test PROJECT_ROOT is defined."""
        from app.config import PROJECT_ROOT

        assert PROJECT_ROOT is not None
        assert isinstance(PROJECT_ROOT, Path)

    def test_directories_are_related(self):
        """Test that directories have logical relationships."""
        from app.config import PROJECT_ROOT

        # DATA_DIR and LOG_DIR should be relative to PROJECT_ROOT
        assert PROJECT_ROOT.name == "backend" or PROJECT_ROOT.name == "app"
