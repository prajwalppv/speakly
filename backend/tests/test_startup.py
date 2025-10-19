"""
Test suite for application startup module.
"""

from unittest.mock import patch

import pytest


class TestInitializeIntegrations:
    """Test initialize_integrations function."""

    @patch("app.startup.register_integration")
    @patch("app.startup.ticktick_integration")
    def test_initialize_integrations_success(self, mock_ticktick, mock_register):
        """Test successful integration initialization."""
        from app.integrations.base import IntegrationType
        from app.startup import initialize_integrations

        mock_ticktick.name = "ticktick"
        mock_ticktick.is_enabled.return_value = True
        mock_ticktick.integration_type = IntegrationType.TASK_SYNC

        initialize_integrations()

        mock_register.assert_called_once_with(mock_ticktick)

    @patch("app.startup.register_integration")
    @patch("app.startup.ticktick_integration")
    def test_initialize_integrations_disabled(self, mock_ticktick, mock_register):
        """Test initialization with disabled integration."""
        from app.integrations.base import IntegrationType
        from app.startup import initialize_integrations

        mock_ticktick.name = "ticktick"
        mock_ticktick.is_enabled.return_value = False
        mock_ticktick.integration_type = IntegrationType.TASK_SYNC

        initialize_integrations()

        mock_register.assert_called_once()

    @patch("app.startup.register_integration")
    @patch("app.startup.ticktick_integration")
    def test_initialize_integrations_handles_error(self, mock_ticktick, mock_register):
        """Test initialization handles registration errors."""
        from app.integrations.base import IntegrationType
        from app.startup import initialize_integrations

        mock_ticktick.name = "ticktick"
        mock_ticktick.integration_type = IntegrationType.TASK_SYNC
        mock_register.side_effect = Exception("Registration failed")

        # Should not raise, just log error
        initialize_integrations()

        mock_register.assert_called_once()


class TestStartup:
    """Test startup function."""

    @patch("app.startup.initialize_integrations")
    def test_startup_calls_initialize(self, mock_initialize):
        """Test startup function calls initialization."""
        from app.startup import startup

        startup()

        mock_initialize.assert_called_once()

    @patch("app.startup.initialize_integrations")
    def test_startup_handles_error(self, mock_initialize):
        """Test startup handles initialization errors."""
        from app.startup import startup

        mock_initialize.side_effect = Exception("Init failed")

        # Should raise the exception
        with pytest.raises(Exception, match="Init failed"):
            startup()
