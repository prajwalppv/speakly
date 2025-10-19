"""
Comprehensive test suite for TickTick integration.
Testing all 125 uncovered lines for maximum coverage.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest


class TestTickTickIntegrationBasics:
    """Test basic properties and methods."""

    def test_name_property(self):
        """Test integration name."""
        from app.integrations.ticktick_integration import TickTickIntegration

        integration = TickTickIntegration()
        assert integration.name == "ticktick"

    def test_integration_type(self):
        """Test integration type."""
        from app.integrations.base import IntegrationType
        from app.integrations.ticktick_integration import TickTickIntegration

        integration = TickTickIntegration()
        assert integration.integration_type == IntegrationType.TASK_SYNC

    @patch("app.integrations.ticktick_integration.settings")
    def test_is_enabled_true(self, mock_settings):
        """Test is_enabled when TickTick is enabled."""
        from app.integrations.ticktick_integration import TickTickIntegration

        mock_settings.ticktick_enabled = True
        integration = TickTickIntegration()
        assert integration.is_enabled() is True

    @patch("app.integrations.ticktick_integration.settings")
    def test_is_enabled_false(self, mock_settings):
        """Test is_enabled when TickTick is disabled."""
        from app.integrations.ticktick_integration import TickTickIntegration

        mock_settings.ticktick_enabled = False
        integration = TickTickIntegration()
        assert integration.is_enabled() is False


class TestIsConnected:
    """Test is_connected method."""

    @patch("app.integrations.ticktick_integration.TickTickClient")
    @patch("app.integrations.ticktick_integration.settings")
    def test_is_connected_true(self, mock_settings, mock_client_class):
        """Test is_connected when user has valid token."""
        from app.integrations.ticktick_integration import TickTickIntegration

        mock_settings.ticktick_enabled = True
        mock_client = Mock()
        mock_client._get_token.return_value = Mock()
        mock_client_class.return_value = mock_client

        integration = TickTickIntegration()
        result = integration.is_connected(1, Mock())

        assert result is True

    @patch("app.integrations.ticktick_integration.TickTickClient")
    @patch("app.integrations.ticktick_integration.settings")
    def test_is_connected_false_no_token(self, mock_settings, mock_client_class):
        """Test is_connected when user has no token."""
        from app.integrations.ticktick_integration import TickTickIntegration

        mock_settings.ticktick_enabled = True
        mock_client = Mock()
        mock_client._get_token.side_effect = Exception("No token")
        mock_client_class.return_value = mock_client

        integration = TickTickIntegration()
        result = integration.is_connected(1, Mock())

        assert result is False

    @patch("app.integrations.ticktick_integration.settings")
    def test_is_connected_disabled(self, mock_settings):
        """Test is_connected when integration disabled."""
        from app.integrations.ticktick_integration import TickTickIntegration

        mock_settings.ticktick_enabled = False
        integration = TickTickIntegration()
        result = integration.is_connected(1, Mock())

        assert result is False


class TestGetConnectionStatus:
    """Test get_connection_status method."""

    @patch("app.integrations.ticktick_integration.settings")
    def test_connection_status_disabled(self, mock_settings):
        """Test status when integration is disabled."""
        from app.integrations.ticktick_integration import TickTickIntegration

        mock_settings.ticktick_enabled = False
        integration = TickTickIntegration()
        status = integration.get_connection_status(1, Mock())

        assert status["connected"] is False
        assert "not enabled" in status["error"]

    @patch("app.integrations.ticktick_integration.TickTickClient")
    @patch("app.integrations.ticktick_integration.settings")
    def test_connection_status_connected(self, mock_settings, mock_client_class):
        """Test status when user is connected."""
        from app.integrations.ticktick_integration import TickTickIntegration

        mock_settings.ticktick_enabled = True

        mock_token = Mock()
        mock_token.expires_at = datetime.utcnow() + timedelta(hours=1)
        mock_token.scope = "tasks:write tasks:read"

        mock_client = Mock()
        mock_client._get_token.return_value = mock_token
        mock_client_class.return_value = mock_client

        integration = TickTickIntegration()
        status = integration.get_connection_status(1, Mock())

        assert status["connected"] is True
        assert status["user_id"] == 1
        assert status["scope"] == "tasks:write tasks:read"

    @patch("app.integrations.ticktick_integration.TickTickClient")
    @patch("app.integrations.ticktick_integration.settings")
    def test_connection_status_error(self, mock_settings, mock_client_class):
        """Test status when connection fails."""
        from app.integrations.ticktick_integration import TickTickIntegration

        mock_settings.ticktick_enabled = True
        mock_client = Mock()
        mock_client._get_token.side_effect = Exception("Token expired")
        mock_client_class.return_value = mock_client

        integration = TickTickIntegration()
        status = integration.get_connection_status(1, Mock())

        assert status["connected"] is False
        assert "Token expired" in status["error"]


class TestSyncTask:
    """Test sync_task method."""

    @pytest.mark.asyncio
    @patch("app.integrations.ticktick_integration.TickTickClient")
    @patch("app.integrations.ticktick_integration.settings")
    async def test_sync_task_success(self, mock_settings, mock_client_class):
        """Test successful task sync."""
        from app.integrations.ticktick_integration import TickTickIntegration

        mock_settings.ticktick_enabled = True

        mock_todo = Mock()
        mock_todo.id = 1
        mock_todo.session_id = 10
        mock_todo.title = "Test task"
        mock_todo.source_excerpt = "Do this thing"
        mock_todo.due_hint = "by Friday"
        mock_todo.confidence = 0.95
        mock_todo.session.description = "Test session"
        mock_todo.session.transcriptions = []

        mock_client = Mock()
        mock_client.get_or_create_speakly_project = AsyncMock(return_value="proj-1")
        mock_client.create_task = AsyncMock(
            return_value={"id": "task-123", "projectId": "proj-1"}
        )
        mock_client_class.return_value = mock_client

        integration = TickTickIntegration()
        result = await integration.sync_task(mock_todo, 1, Mock())

        assert result["task_id"] == "task-123"
        assert result["project_id"] == "proj-1"

    @pytest.mark.asyncio
    @patch("app.integrations.ticktick_integration.settings")
    async def test_sync_task_disabled(self, mock_settings):
        """Test sync_task raises when disabled."""
        from app.integrations.ticktick_integration import (
            IntegrationError,
            TickTickIntegration,
        )

        mock_settings.ticktick_enabled = False
        integration = TickTickIntegration()

        with pytest.raises(IntegrationError, match="not enabled"):
            await integration.sync_task(Mock(), 1, Mock())

    @pytest.mark.asyncio
    @patch("app.integrations.ticktick_integration.TickTickClient")
    @patch("app.integrations.ticktick_integration.settings")
    async def test_sync_task_with_transcript_snippet(
        self, mock_settings, mock_client_class
    ):
        """Test sync includes transcript snippet when no description."""
        from app.integrations.ticktick_integration import TickTickIntegration

        mock_settings.ticktick_enabled = True

        mock_transcription = Mock()
        mock_transcription.text = "A" * 200  # Long transcript

        mock_todo = Mock()
        mock_todo.id = 1
        mock_todo.session_id = 10
        mock_todo.title = "Task"
        mock_todo.source_excerpt = None
        mock_todo.due_hint = None
        mock_todo.confidence = None
        mock_todo.session.description = None
        mock_todo.session.transcriptions = [mock_transcription]

        mock_client = Mock()
        mock_client.get_or_create_speakly_project = AsyncMock(return_value="proj-1")
        mock_client.create_task = AsyncMock(
            return_value={"id": "t1", "projectId": "p1"}
        )
        mock_client_class.return_value = mock_client

        integration = TickTickIntegration()
        await integration.sync_task(mock_todo, 1, Mock())

        # Verify create_task was called with content including snippet
        call_kwargs = mock_client.create_task.call_args[1]
        assert "Context" in call_kwargs["content"]


class TestGetOrCreateProject:
    """Test get_or_create_project method."""

    @pytest.mark.asyncio
    @patch("app.integrations.ticktick_integration.TickTickClient")
    @patch("app.integrations.ticktick_integration.settings")
    async def test_get_or_create_project_success(
        self, mock_settings, mock_client_class
    ):
        """Test successful project creation."""
        from app.integrations.ticktick_integration import TickTickIntegration

        mock_settings.ticktick_enabled = True
        mock_client = Mock()
        mock_client.get_or_create_speakly_project = AsyncMock(return_value="proj-123")
        mock_client_class.return_value = mock_client

        integration = TickTickIntegration()
        project_id = await integration.get_or_create_project("Speakly", 1, Mock())

        assert project_id == "proj-123"

    @pytest.mark.asyncio
    @patch("app.integrations.ticktick_integration.settings")
    async def test_get_or_create_project_disabled(self, mock_settings):
        """Test raises when disabled."""
        from app.integrations.ticktick_integration import (
            IntegrationError,
            TickTickIntegration,
        )

        mock_settings.ticktick_enabled = False
        integration = TickTickIntegration()

        with pytest.raises(IntegrationError):
            await integration.get_or_create_project("Test", 1, Mock())


class TestGetProjects:
    """Test get_projects method."""

    @pytest.mark.asyncio
    @patch("app.integrations.ticktick_integration.TickTickClient")
    @patch("app.integrations.ticktick_integration.settings")
    async def test_get_projects_success(self, mock_settings, mock_client_class):
        """Test successful projects retrieval."""
        from app.integrations.ticktick_integration import TickTickIntegration

        mock_settings.ticktick_enabled = True
        mock_client = Mock()
        mock_client.get_projects = AsyncMock(
            return_value=[{"id": "p1", "name": "Test"}]
        )
        mock_client_class.return_value = mock_client

        integration = TickTickIntegration()
        projects = await integration.get_projects(1, Mock())

        assert len(projects) == 1
        assert projects[0]["name"] == "Test"


class TestSearchTasks:
    """Test search_tasks method."""

    @pytest.mark.asyncio
    @patch("app.integrations.ticktick_integration.TickTickClient")
    @patch("app.integrations.ticktick_integration.settings")
    async def test_search_tasks_fuzzy_matching(self, mock_settings, mock_client_class):
        """Test fuzzy task search."""
        from app.integrations.ticktick_integration import TickTickIntegration

        mock_settings.ticktick_enabled = True
        mock_client = Mock()
        mock_client.get_or_create_speakly_project = AsyncMock(return_value="proj-1")
        mock_client.get_tasks = AsyncMock(
            return_value=[
                {"id": "t1", "title": "Buy groceries", "content": ""},
                {"id": "t2", "title": "Call dentist", "content": ""},
            ]
        )
        mock_client_class.return_value = mock_client

        integration = TickTickIntegration()
        results = await integration.search_tasks("grocery", 1, Mock())

        # Should find the groceries task with fuzzy matching
        assert len(results) >= 1
        assert any("groceries" in r["title"].lower() for r in results)

    @pytest.mark.asyncio
    @patch("app.integrations.ticktick_integration.TickTickClient")
    @patch("app.integrations.ticktick_integration.settings")
    async def test_search_tasks_no_matches(self, mock_settings, mock_client_class):
        """Test search with no matches."""
        from app.integrations.ticktick_integration import TickTickIntegration

        mock_settings.ticktick_enabled = True
        mock_client = Mock()
        mock_client.get_or_create_speakly_project = AsyncMock(return_value="proj-1")
        mock_client.get_tasks = AsyncMock(
            return_value=[
                {"id": "t1", "title": "Unrelated task", "content": ""},
            ]
        )
        mock_client_class.return_value = mock_client

        integration = TickTickIntegration()
        results = await integration.search_tasks(
            "completely different query", 1, Mock()
        )

        # Should return empty list (no matches above threshold)
        assert len(results) == 0


class TestUpdateTaskStatus:
    """Test update_task_status method."""

    @pytest.mark.asyncio
    @patch("app.integrations.ticktick_integration.TickTickClient")
    @patch("app.integrations.ticktick_integration.settings")
    async def test_update_task_status_completed(self, mock_settings, mock_client_class):
        """Test updating task to completed status."""
        from app.integrations.ticktick_integration import TickTickIntegration

        mock_settings.ticktick_enabled = True
        mock_client = Mock()
        mock_client.update_task = AsyncMock(return_value={"id": "t1", "status": 2})
        mock_client_class.return_value = mock_client

        integration = TickTickIntegration()
        result = await integration.update_task_status("t1", "completed", 1, Mock())

        # Verify update_task was called with status=2
        call_args = mock_client.update_task.call_args[0]
        assert call_args[1]["status"] == 2

    @pytest.mark.asyncio
    @patch("app.integrations.ticktick_integration.TickTickClient")
    @patch("app.integrations.ticktick_integration.settings")
    async def test_update_task_status_cancelled(self, mock_settings, mock_client_class):
        """Test updating task to cancelled status."""
        from app.integrations.ticktick_integration import TickTickIntegration

        mock_settings.ticktick_enabled = True
        mock_client = Mock()
        mock_client.update_task = AsyncMock(return_value={"id": "t1"})
        mock_client_class.return_value = mock_client

        integration = TickTickIntegration()
        await integration.update_task_status("t1", "cancelled", 1, Mock())

        call_args = mock_client.update_task.call_args[0]
        assert call_args[1]["status"] == 2  # Completed with note

    @pytest.mark.asyncio
    @patch("app.integrations.ticktick_integration.TickTickClient")
    @patch("app.integrations.ticktick_integration.settings")
    async def test_update_task_status_in_progress(
        self, mock_settings, mock_client_class
    ):
        """Test in_progress status doesn't update."""
        from app.integrations.ticktick_integration import TickTickIntegration

        mock_settings.ticktick_enabled = True
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        integration = TickTickIntegration()
        result = await integration.update_task_status("t1", "in_progress", 1, Mock())

        # Should return no_update flag
        assert result.get("no_update") is True


class TestProcessTaskUpdate:
    """Test process_task_update method."""

    @pytest.mark.asyncio
    @patch("app.integrations.ticktick_integration.settings")
    async def test_process_task_update_low_confidence(self, mock_settings):
        """Test skips low confidence updates."""
        from app.integrations.ticktick_integration import TickTickIntegration

        mock_settings.ticktick_enabled = True
        integration = TickTickIntegration()

        update = {"title": "Task", "status": "completed", "confidence": 0.5}
        result = await integration.process_task_update(update, 1, Mock())

        assert result["skipped"] is True
        assert result["reason"] == "low_confidence"

    @pytest.mark.asyncio
    @patch("app.integrations.ticktick_integration.settings")
    async def test_process_task_update_no_match(self, mock_settings):
        """Test handles no matching tasks."""
        from app.integrations.ticktick_integration import TickTickIntegration

        mock_settings.ticktick_enabled = True
        integration = TickTickIntegration()
        integration.search_tasks = AsyncMock(return_value=[])

        update = {"title": "Task", "status": "completed", "confidence": 0.9}
        result = await integration.process_task_update(update, 1, Mock())

        assert result["skipped"] is True
        assert result["reason"] == "no_match"

    @pytest.mark.asyncio
    @patch("app.integrations.ticktick_integration.settings")
    async def test_process_task_update_success(self, mock_settings):
        """Test successful task update processing."""
        from app.integrations.ticktick_integration import TickTickIntegration

        mock_settings.ticktick_enabled = True
        integration = TickTickIntegration()
        integration.search_tasks = AsyncMock(
            return_value=[{"id": "t1", "title": "Matching task", "match_score": 95}]
        )
        integration.update_task_status = AsyncMock(return_value={"id": "t1"})

        update = {"title": "Task", "status": "completed", "confidence": 0.9}
        result = await integration.process_task_update(update, 1, Mock())

        assert result["success"] is True
        assert result["task_id"] == "t1"
        assert result["match_quality"] == "excellent"


class TestGlobalInstance:
    """Test global ticktick_integration instance."""

    def test_global_instance_exists(self):
        """Test global instance is available."""
        from app.integrations.ticktick_integration import ticktick_integration

        assert ticktick_integration is not None
        assert ticktick_integration.name == "ticktick"
