"""
Integration framework for external services.

This module provides the base interfaces and registry for pluggable integrations.
"""

from .base import (
    Integration,
    IntegrationConfig,
    IntegrationError,
    IntegrationRegistry,
    TaskSyncIntegration,
)
from .registry import get_integration, list_integrations, register_integration

__all__ = [
    "Integration",
    "IntegrationConfig",
    "IntegrationError",
    "TaskSyncIntegration",
    "IntegrationRegistry",
    "get_integration",
    "register_integration",
    "list_integrations",
]
