"""TickTick API client for OAuth 2.0 and task management."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..models import TickTickToken, User

logger = logging.getLogger(__name__)


class TickTickNotConfiguredError(Exception):
    """Raised when TickTick integration is not configured."""
    pass


class TickTickAuthError(Exception):
    """Raised when TickTick authentication fails."""
    pass


class TickTickAPIError(Exception):
    """Raised when TickTick API request fails."""
    pass


class TickTickClient:
    """Client for interacting with TickTick OpenAPI."""

    def __init__(self, user_id: int, db: Session):
        """
        Initialize TickTick client for a specific user.

        Args:
            user_id: Database ID of the user
            db: SQLAlchemy database session
        """
        if not settings.ticktick_enabled:
            raise TickTickNotConfiguredError("TickTick integration is not enabled")

        if not settings.ticktick_client_id or not settings.ticktick_client_secret:
            raise TickTickNotConfiguredError("TickTick credentials not configured")

        self.user_id = user_id
        self.db = db
        self.base_url = settings.ticktick_base_url

    def _get_token(self) -> TickTickToken:
        """Get valid access token for the user."""
        token = self.db.query(TickTickToken).filter(
            TickTickToken.user_id == self.user_id
        ).first()

        if not token:
            raise TickTickAuthError(f"No TickTick token found for user {self.user_id}")

        # Check if token is expired
        if datetime.utcnow() >= token.expires_at:
            raise TickTickAuthError("TickTick token has expired")

        return token

    async def create_task(
        self,
        title: str,
        content: str | None = None,
        project_id: str | None = None,
        start_date: datetime | None = None,
        due_date: datetime | None = None,
        priority: int | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new task in TickTick.

        Args:
            title: Task title
            content: Task description/content
            project_id: TickTick project/list ID (defaults to Inbox)
            start_date: Task start date
            due_date: Task due date
            priority: Priority level (0=None, 1=Low, 3=Medium, 5=High)
            tags: List of tags to add

        Returns:
            dict: Created task data from TickTick API

        Raises:
            TickTickAuthError: If authentication fails
            TickTickAPIError: If API request fails
        """
        token = self._get_token()

        # Build task payload
        task_data: dict[str, Any] = {
            "title": title,
        }

        if content:
            task_data["content"] = content

        if project_id:
            task_data["projectId"] = project_id

        if start_date:
            task_data["startDate"] = start_date.strftime("%Y-%m-%dT%H:%M:%S+0000")

        if due_date:
            task_data["dueDate"] = due_date.strftime("%Y-%m-%dT%H:%M:%S+0000")

        if priority is not None:
            task_data["priority"] = priority

        if tags:
            task_data["tags"] = tags

        headers = {
            "Authorization": f"Bearer {token.access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/task",
                    headers=headers,
                    json=task_data,
                )
                response.raise_for_status()
                result = response.json()

                logger.info(
                    "Created TickTick task",
                    extra={
                        "user_id": self.user_id,
                        "task_id": result.get("id"),
                        "project_id": result.get("projectId"),
                        "title": title,
                        "full_response_keys": list(result.keys()),
                    },
                )

                return result

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"TickTick API error: {e.response.status_code} - {e.response.text}",
                    extra={"user_id": self.user_id},
                )
                raise TickTickAPIError(f"Failed to create task: {e.response.text}") from e

            except httpx.RequestError as e:
                logger.error(
                    f"TickTick request error: {str(e)}",
                    extra={"user_id": self.user_id},
                )
                raise TickTickAPIError(f"Failed to connect to TickTick: {str(e)}") from e

    async def get_projects(self) -> list[dict[str, Any]]:
        """
        Get all projects (lists) for the user.

        Returns:
            list: List of project data from TickTick API
        """
        token = self._get_token()

        headers = {
            "Authorization": f"Bearer {token.access_token}",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/project",
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"TickTick API error: {e.response.status_code}",
                    extra={"user_id": self.user_id},
                )
                raise TickTickAPIError(f"Failed to get projects: {e.response.text}") from e

            except httpx.RequestError as e:
                raise TickTickAPIError(f"Failed to connect to TickTick: {str(e)}") from e

    async def get_or_create_speakly_project(self) -> str:
        """
        Get or create the 'Speakly' project in TickTick.

        Returns:
            str: Project ID of the Speakly project

        Raises:
            TickTickAPIError: If unable to get/create project
        """
        # Get all projects
        projects = await self.get_projects()

        # Look for existing Speakly project
        for project in projects:
            if project.get("name") == "Speakly":
                project_id = project.get("id")
                logger.info(
                    f"Found existing Speakly project: {project_id}",
                    extra={"user_id": self.user_id},
                )
                return project_id

        # Create Speakly project if it doesn't exist
        logger.info(f"Creating Speakly project for user {self.user_id}")
        token = self._get_token()

        headers = {
            "Authorization": f"Bearer {token.access_token}",
            "Content-Type": "application/json",
        }

        project_data = {
            "name": "Speakly",
            "color": "#d4af37",  # Gold color
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/project",
                    headers=headers,
                    json=project_data,
                )
                response.raise_for_status()
                result = response.json()
                project_id = result.get("id")

                logger.info(
                    f"Created Speakly project: {project_id}",
                    extra={"user_id": self.user_id},
                )

                return project_id

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"TickTick API error creating project: {e.response.status_code}",
                    extra={"user_id": self.user_id},
                )
                raise TickTickAPIError(f"Failed to create Speakly project: {e.response.text}") from e

            except httpx.RequestError as e:
                raise TickTickAPIError(f"Failed to connect to TickTick: {str(e)}") from e

    async def get_tasks(self, project_id: str | None = None) -> list[dict[str, Any]]:
        """
        Get tasks for the user.

        Args:
            project_id: Optional project ID to filter tasks

        Returns:
            list: List of task data from TickTick API
        """
        token = self._get_token()

        headers = {
            "Authorization": f"Bearer {token.access_token}",
        }

        url = f"{self.base_url}/task"
        if project_id:
            url += f"?projectId={project_id}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"TickTick API error: {e.response.status_code}",
                    extra={"user_id": self.user_id},
                )
                raise TickTickAPIError(f"Failed to get tasks: {e.response.text}") from e

            except httpx.RequestError as e:
                raise TickTickAPIError(f"Failed to connect to TickTick: {str(e)}") from e

    async def search_tasks(self, query: str, project_id: str | None = None) -> list[dict[str, Any]]:
        """
        Search for tasks by title/content.

        Args:
            query: Search query string
            project_id: Optional project ID to limit search

        Returns:
            list: Matching tasks
        """
        # Get all tasks (TickTick API doesn't have direct search, so we filter locally)
        tasks = await self.get_tasks(project_id)
        
        query_lower = query.lower()
        matching_tasks = []
        
        for task in tasks:
            # Search in title and content
            title = task.get("title", "").lower()
            content = task.get("content", "").lower()
            
            if query_lower in title or query_lower in content:
                matching_tasks.append(task)
        
        logger.info(
            f"Found {len(matching_tasks)} tasks matching '{query}'",
        )
        
        return matching_tasks

    async def update_task(self, task_id: str, updates: dict[str, Any], project_id: str = None) -> dict[str, Any]:
        """
        Update an existing task in TickTick.

        Args:
            task_id: ID of the task to update
            updates: Dictionary of fields to update
            project_id: Project ID (will be fetched if not provided)

        Returns:
            dict: Updated task data from TickTick API

        Raises:
            TickTickAuthError: If authentication fails
            TickTickAPIError: If API request fails
        """
        token = self._get_token()

        # Get project_id if not provided
        if not project_id:
            project_id = await self.get_or_create_speakly_project()

        headers = {
            "Authorization": f"Bearer {token.access_token}",
            "Content-Type": "application/json",
        }

        # Build the complete payload as per TickTick API docs
        payload = {
            "id": task_id,
            "projectId": project_id,
            **updates
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Use POST for updates (per TickTick API docs)
                response = await client.post(
                    f"{self.base_url}/task/{task_id}",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                
                # Some update operations return empty response body
                if response.content:
                    result = response.json()
                else:
                    # If no content, return the updates that were applied
                    result = {"id": task_id, **updates}

                logger.info(
                    f"Updated TickTick task {task_id}",
                    extra={"user_id": self.user_id, "task_id": task_id, "updates": list(updates.keys())},
                )

                return result

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"TickTick API error: {e.response.status_code} - {e.response.text}",
                    extra={"user_id": self.user_id},
                )
                raise TickTickAPIError(f"Failed to update task: {e.response.text}") from e

            except httpx.RequestError as e:
                logger.error(
                    f"TickTick request error: {str(e)}",
                    extra={"user_id": self.user_id},
                )
                raise TickTickAPIError(f"Failed to connect to TickTick: {str(e)}") from e

    async def complete_task(self, task_id: str, project_id: str = None) -> dict[str, Any]:
        """
        Mark a task as completed using the dedicated complete endpoint.

        Args:
            task_id: ID of the task to complete
            project_id: Project ID (will be fetched if not provided)

        Returns:
            dict: Response from TickTick API
        """
        token = self._get_token()

        # Get project_id if not provided
        if not project_id:
            project_id = await self.get_or_create_speakly_project()

        headers = {
            "Authorization": f"Bearer {token.access_token}",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/project/{project_id}/task/{task_id}/complete",
                    headers=headers,
                )
                response.raise_for_status()

                # Complete endpoint may return empty response
                if response.content:
                    result = response.json()
                else:
                    result = {"id": task_id, "status": 2, "completed": True}

                logger.info(f"Completed task {task_id} in TickTick")
                return result

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"TickTick API error: {e.response.status_code} - {e.response.text}",
                    extra={"user_id": self.user_id, "task_id": task_id},
                )
                if e.response.status_code == 401:
                    raise TickTickAuthError("Authentication failed - token may be expired") from e
                else:
                    raise TickTickAPIError(f"Failed to complete task: {e.response.text}") from e

            except (httpx.RequestError, httpx.TimeoutException) as e:
                logger.error(
                    f"TickTick request error: {str(e)}",
                    extra={"user_id": self.user_id, "task_id": task_id},
                )
                raise TickTickAPIError(f"Failed to connect to TickTick: {str(e)}") from e

    async def delete_task(self, task_id: str, project_id: str) -> None:
        """
        Delete a task from TickTick.

        Args:
            task_id: ID of the task to delete
            project_id: ID of the project containing the task

        Raises:
            TickTickAuthError: If authentication fails
            TickTickAPIError: If API request fails
        """
        token = self._get_token()

        url = f"{self.base_url}/project/{project_id}/task/{task_id}"
        headers = {"Authorization": f"Bearer {token.access_token}"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(url, headers=headers, timeout=10.0)

                if response.status_code == 204:
                    logger.info(f"Deleted task {task_id} from TickTick")
                    return

                if response.status_code == 401:
                    raise TickTickAuthError("Authentication failed - token may be expired")

                if response.status_code == 404:
                    logger.warning(f"Task {task_id} not found in TickTick (may already be deleted)")
                    return

                raise TickTickAPIError(
                    f"Failed to delete task: {response.status_code} - {response.text}"
                )

            except httpx.RequestError as e:
                raise TickTickAPIError(f"Failed to connect to TickTick: {str(e)}") from e


class TickTickOAuth:
    """Handles OAuth 2.0 flow for TickTick."""

    @staticmethod
    def get_authorization_url(state: str | None = None) -> str:
        """
        Generate OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            str: Authorization URL
        """
        if not settings.ticktick_client_id:
            raise TickTickNotConfiguredError("TickTick client ID not configured")

        params = {
            "client_id": settings.ticktick_client_id,
            "scope": "tasks:write tasks:read",
            "redirect_uri": settings.ticktick_redirect_uri,
            "response_type": "code",
        }

        if state:
            params["state"] = state

        return f"https://ticktick.com/oauth/authorize?{urlencode(params)}"

    @staticmethod
    async def exchange_code_for_token(code: str) -> dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            dict: Token response with access_token, expires_in, etc.

        Raises:
            TickTickAuthError: If token exchange fails
        """
        if not settings.ticktick_client_id or not settings.ticktick_client_secret:
            raise TickTickNotConfiguredError("TickTick credentials not configured")

        data = {
            "client_id": settings.ticktick_client_id,
            "client_secret": settings.ticktick_client_secret,
            "code": code,
            "redirect_uri": settings.ticktick_redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    "https://ticktick.com/oauth/token",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"TickTick OAuth error: {e.response.status_code} - {e.response.text}")
                raise TickTickAuthError(f"Token exchange failed: {e.response.text}") from e

            except httpx.RequestError as e:
                logger.error(f"TickTick OAuth request error: {str(e)}")
                raise TickTickAuthError(f"Failed to connect to TickTick: {str(e)}") from e

    @staticmethod
    def save_token(db: Session, user: User, token_data: dict[str, Any]) -> TickTickToken:
        """
        Save or update TickTick token in database.

        Args:
            db: Database session
            user: User to save token for
            token_data: Token data from OAuth response

        Returns:
            TickTickToken: Saved token record
        """
        # Calculate expiration time
        expires_in_seconds = token_data.get("expires_in", 15552000)  # Default ~6 months
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds)

        # Check if token already exists
        existing_token = db.query(TickTickToken).filter(
            TickTickToken.user_id == user.id
        ).first()

        if existing_token:
            # Update existing token
            existing_token.access_token = token_data["access_token"]
            existing_token.refresh_token = token_data.get("refresh_token")
            existing_token.token_type = token_data.get("token_type", "bearer")
            existing_token.expires_at = expires_at
            existing_token.scope = token_data.get("scope", "tasks:write tasks:read")
            existing_token.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(existing_token)

            logger.info(f"Updated TickTick token for user {user.id}")
            return existing_token

        else:
            # Create new token
            new_token = TickTickToken(
                user_id=user.id,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_type=token_data.get("token_type", "bearer"),
                expires_at=expires_at,
                scope=token_data.get("scope", "tasks:write tasks:read"),
            )

            db.add(new_token)
            db.commit()
            db.refresh(new_token)

            logger.info(f"Created TickTick token for user {user.id}")
            return new_token


__all__ = [
    "TickTickClient",
    "TickTickOAuth",
    "TickTickNotConfiguredError",
    "TickTickAuthError",
    "TickTickAPIError",
]
