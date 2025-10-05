"""
Global integration registry instance.

This module provides a singleton registry for all integrations.
"""

from __future__ import annotations

from .base import Integration, IntegrationRegistry

# Global registry instance
_registry = IntegrationRegistry()


def register_integration(integration: Integration) -> None:
    """
    Register an integration with the global registry.

    Args:
        integration: Integration instance to register
    """
    _registry.register(integration)


def get_integration(name: str) -> Integration | None:
    """
    Get an integration by name.

    Args:
        name: Name of the integration

    Returns:
        Integration instance or None if not found
    """
    return _registry.get(name)


def list_integrations(enabled_only: bool = False) -> list[Integration]:
    """
    List all registered integrations.

    Args:
        enabled_only: If True, only return enabled integrations

    Returns:
        List of integration instances
    """
    if enabled_only:
        return _registry.list_enabled()
    return _registry.list_all()


def get_registry() -> IntegrationRegistry:
    """Get the global registry instance."""
    return _registry
