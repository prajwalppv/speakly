"""
Base interfaces for integrations following SOLID principles.

This module defines the contracts that all integrations must follow,
enabling plug-and-play architecture for external services.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, TypeVar

from sqlalchemy.orm import Session


class IntegrationError(Exception):
    """Base exception for integration errors."""

    pass


class IntegrationType(str, Enum):
    """Types of integrations supported."""

    TASK_SYNC = "task_sync"
    CALENDAR = "calendar"
    NOTES = "notes"
    CRM = "crm"
    COMMUNICATION = "communication"


@dataclass
class IntegrationConfig:
    """Configuration for an integration."""

    name: str
    enabled: bool
    integration_type: IntegrationType
    metadata: dict[str, Any]


class Integration(ABC):
    """
    Base interface for all integrations.

    Follows the Interface Segregation Principle - this base class
    only defines common behavior all integrations must implement.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of the integration."""
        pass

    @property
    @abstractmethod
    def integration_type(self) -> IntegrationType:
        """Type of integration."""
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if the integration is enabled and configured."""
        pass

    @abstractmethod
    def is_connected(self, user_id: int, db: Session) -> bool:
        """Check if a user has connected this integration."""
        pass

    @abstractmethod
    def get_connection_status(self, user_id: int, db: Session) -> dict[str, Any]:
        """Get detailed connection status for a user."""
        pass


# Type variable for task data
T = TypeVar("T")


class TaskSyncIntegration(Integration, ABC, Generic[T]):
    """
    Interface for task synchronization integrations.

    Follows the Interface Segregation Principle - only task-related
    integrations need to implement these methods.
    """

    @abstractmethod
    async def sync_task(
        self, task_data: T, user_id: int, db: Session
    ) -> dict[str, Any]:
        """
        Sync a single task to the external service.

        Args:
            task_data: Task data to sync (type depends on implementation)
            user_id: User ID who owns the task
            db: Database session

        Returns:
            dict: Sync result with external task ID and metadata

        Raises:
            IntegrationError: If sync fails
        """
        pass

    @abstractmethod
    async def get_or_create_project(
        self, project_name: str, user_id: int, db: Session
    ) -> str:
        """
        Get or create a project/list in the external service.

        Args:
            project_name: Name of the project
            user_id: User ID
            db: Database session

        Returns:
            str: Project ID in the external service

        Raises:
            IntegrationError: If operation fails
        """
        pass

    @abstractmethod
    async def get_projects(self, user_id: int, db: Session) -> list[dict[str, Any]]:
        """
        Get all projects/lists from the external service.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            list: List of project data

        Raises:
            IntegrationError: If operation fails
        """
        pass


class IntegrationRegistry:
    """
    Registry for managing integrations.

    Follows the Dependency Inversion Principle - high-level code
    depends on the Integration interface, not concrete implementations.
    """

    def __init__(self):
        self._integrations: dict[str, Integration] = {}

    def register(self, integration: Integration) -> None:
        """Register an integration."""
        self._integrations[integration.name] = integration

    def get(self, name: str) -> Integration | None:
        """Get an integration by name."""
        return self._integrations.get(name)

    def get_by_type(self, integration_type: IntegrationType) -> list[Integration]:
        """Get all integrations of a specific type."""
        return [
            integration
            for integration in self._integrations.values()
            if integration.integration_type == integration_type
        ]

    def list_all(self) -> list[Integration]:
        """List all registered integrations."""
        return list(self._integrations.values())

    def list_enabled(self) -> list[Integration]:
        """List all enabled integrations."""
        return [
            integration
            for integration in self._integrations.values()
            if integration.is_enabled()
        ]
