"""
Application startup initialization.

This module handles loading and registering all integrations
and other startup tasks.
"""

import logging

from .integrations.registry import register_integration
from .integrations.ticktick_integration import ticktick_integration

logger = logging.getLogger(__name__)


def initialize_integrations() -> None:
    """
    Initialize and register all integrations.

    This function is called on application startup to register
    all available integrations with the registry.
    """
    integrations = [
        ticktick_integration,
        # Add more integrations here as they're implemented:
        # notion_integration,
        # todoist_integration,
        # linear_integration,
    ]

    for integration in integrations:
        try:
            register_integration(integration)
            status = "enabled" if integration.is_enabled() else "disabled"
            logger.info(
                f"Registered integration: {integration.name} ({status})",
                extra={
                    "integration": integration.name,
                    "type": integration.integration_type.value,
                    "enabled": integration.is_enabled(),
                },
            )
        except Exception as e:
            logger.error(
                f"Failed to register integration {integration.name}: {str(e)}",
                exc_info=True,
            )


def startup() -> None:
    """
    Run all startup tasks.

    This function is called when the FastAPI application starts.
    """
    logger.info("Running application startup tasks...")
    initialize_integrations()
    logger.info("Application startup complete")
