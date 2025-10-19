"""
Comprehensive test suite for TaskSyncService.
Testing all 120 uncovered lines for maximum coverage.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest


class TestTaskSyncServiceInit:
    """Test TaskSyncService initialization."""

    def test_init_creates_instance(self):
        """Test TaskSyncService initializes correctly."""
        from app.services.task_sync_service import TaskSyncService

        service = TaskSyncService()

        assert service._integrations is None
        assert service._loaded is False


class TestLoadIntegrations:
    """Test _load_integrations method."""

    @patch("app.services.task_sync_service.list_integrations")
    def test_load_integrations_filters_task_sync(self, mock_list):
        """Test _load_integrations filters by TASK_SYNC type."""
        from app.integrations.base import IntegrationType, TaskSyncIntegration
        from app.services.task_sync_service import TaskSyncService

        # Create mock integrations
        mock_task_sync = Mock(spec=TaskSyncIntegration)
        mock_task_sync.integration_type = IntegrationType.TASK_SYNC
        mock_task_sync.name = "test_task"

        mock_other = Mock()
        mock_other.integration_type = IntegrationType.CALENDAR

        mock_list.return_value = [mock_task_sync, mock_other]

        service = TaskSyncService()
        service._load_integrations()

        assert service._loaded is True
        assert len(service._integrations) == 1
        assert service._integrations[0] == mock_task_sync

    @patch("app.services.task_sync_service.list_integrations")
    def test_load_integrations_only_once(self, mock_list):
        """Test _load_integrations only loads once (idempotent)."""
        from app.services.task_sync_service import TaskSyncService

        mock_list.return_value = []

        service = TaskSyncService()
        service._load_integrations()
        service._load_integrations()

        # Should only call list_integrations once
        assert mock_list.call_count == 1

    @patch("app.services.task_sync_service.list_integrations")
    def test_load_integrations_empty_list(self, mock_list):
        """Test _load_integrations handles empty integration list."""
        from app.services.task_sync_service import TaskSyncService

        mock_list.return_value = []

        service = TaskSyncService()
        service._load_integrations()

        assert service._integrations == []
        assert service._loaded is True


class TestSyncTodo:
    """Test sync_todo method."""

    @pytest.mark.asyncio
    @patch("app.services.task_sync_service.list_integrations")
    async def test_sync_todo_no_integrations(self, mock_list):
        """Test sync_todo returns empty dict when no integrations."""
        from app.services.task_sync_service import TaskSyncService

        mock_list.return_value = []

        service = TaskSyncService()
        mock_todo = Mock()
        mock_db = Mock()

        results = await service.sync_todo(mock_todo, mock_db)

        assert results == {}

    @pytest.mark.asyncio
    @patch("app.services.task_sync_service.list_integrations")
    async def test_sync_todo_user_not_connected(self, mock_list):
        """Test sync_todo skips when user not connected."""
        from app.integrations.base import IntegrationType, TaskSyncIntegration
        from app.services.task_sync_service import TaskSyncService

        mock_integration = Mock(spec=TaskSyncIntegration)
        mock_integration.integration_type = IntegrationType.TASK_SYNC
        mock_integration.name = "test"
        mock_integration.is_connected.return_value = False

        mock_list.return_value = [mock_integration]

        service = TaskSyncService()
        mock_todo = Mock()
        mock_todo.session.user_id = 1
        mock_db = Mock()

        results = await service.sync_todo(mock_todo, mock_db)

        assert results == {}

    @pytest.mark.asyncio
    @patch("app.services.task_sync_service.list_integrations")
    async def test_sync_todo_success(self, mock_list):
        """Test successful todo sync."""
        from app.integrations.base import IntegrationType, TaskSyncIntegration
        from app.services.task_sync_service import TaskSyncService

        mock_integration = Mock(spec=TaskSyncIntegration)
        mock_integration.integration_type = IntegrationType.TASK_SYNC
        mock_integration.name = "test"
        mock_integration.is_connected.return_value = True
        mock_integration.sync_task = AsyncMock(return_value={"task_id": "123"})

        mock_list.return_value = [mock_integration]

        service = TaskSyncService()
        service._update_todo_sync_status = Mock()

        mock_todo = Mock()
        mock_todo.session.user_id = 1
        mock_todo.id = 1
        mock_db = Mock()

        results = await service.sync_todo(mock_todo, mock_db)

        assert "test" in results
        assert results["test"]["success"] is True
        assert results["test"]["data"] == {"task_id": "123"}
        service._update_todo_sync_status.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.task_sync_service.list_integrations")
    async def test_sync_todo_handles_exception(self, mock_list):
        """Test sync_todo handles integration exceptions."""
        from app.integrations.base import IntegrationType, TaskSyncIntegration
        from app.services.task_sync_service import TaskSyncService

        mock_integration = Mock(spec=TaskSyncIntegration)
        mock_integration.integration_type = IntegrationType.TASK_SYNC
        mock_integration.name = "test"
        mock_integration.is_connected.return_value = True
        mock_integration.sync_task = AsyncMock(side_effect=Exception("Sync failed"))

        mock_list.return_value = [mock_integration]

        service = TaskSyncService()
        service._update_todo_sync_status = Mock()

        mock_todo = Mock()
        mock_todo.session.user_id = 1
        mock_todo.id = 1
        mock_db = Mock()

        results = await service.sync_todo(mock_todo, mock_db)

        assert "test" in results
        assert results["test"]["success"] is False
        assert "Sync failed" in results["test"]["error"]


class TestUpdateTodoSyncStatus:
    """Test _update_todo_sync_status method."""

    def test_update_todo_sync_status_ticktick_success(self):
        """Test updating TODO sync status for TickTick success."""
        from app.services.task_sync_service import TaskSyncService

        service = TaskSyncService()
        mock_todo = Mock()
        mock_db = Mock()

        result = {"task_id": "123", "project_id": "proj-1"}

        service._update_todo_sync_status(mock_todo, "ticktick", result, mock_db)

        assert mock_todo.ticktick_task_id == "123"
        assert mock_todo.ticktick_project_id == "proj-1"
        assert mock_todo.ticktick_sync_status == "synced"
        assert mock_todo.ticktick_sync_error is None
        mock_db.commit.assert_called_once()

    def test_update_todo_sync_status_ticktick_error(self):
        """Test updating TODO sync status for TickTick error."""
        from app.services.task_sync_service import TaskSyncService

        service = TaskSyncService()
        mock_todo = Mock()
        mock_db = Mock()

        service._update_todo_sync_status(
            mock_todo, "ticktick", None, mock_db, error="Connection timeout"
        )

        assert mock_todo.ticktick_sync_status == "error"
        assert mock_todo.ticktick_sync_error == "Connection timeout"
        mock_db.commit.assert_called_once()

    def test_update_todo_sync_status_non_ticktick(self):
        """Test updating status for non-TickTick integration (no-op)."""
        from app.services.task_sync_service import TaskSyncService

        service = TaskSyncService()
        mock_todo = Mock()
        mock_db = Mock()

        service._update_todo_sync_status(
            mock_todo, "other_integration", {"task_id": "123"}, mock_db
        )

        # Should not update any ticktick fields
        mock_db.commit.assert_not_called()


class TestProcessTaskUpdates:
    """Test process_task_updates method."""

    @pytest.mark.asyncio
    @patch("app.services.task_sync_service.list_integrations")
    async def test_process_task_updates_no_session(self, mock_list):
        """Test process_task_updates handles missing session."""
        from app.services.task_sync_service import TaskSyncService

        mock_list.return_value = []

        service = TaskSyncService()
        mock_db = Mock()
        mock_db.query().filter().first.return_value = None

        stats = await service.process_task_updates([], 999, mock_db)

        assert stats == {"updated": 0, "skipped": 0, "failed": 0}

    @pytest.mark.asyncio
    @patch("app.services.task_sync_service.list_integrations")
    async def test_process_task_updates_empty_list(self, mock_list):
        """Test process_task_updates with empty update list."""
        from app.models import Session as SessionModel
        from app.services.task_sync_service import TaskSyncService

        mock_list.return_value = []

        service = TaskSyncService()
        mock_session = Mock(spec=SessionModel)
        mock_session.user_id = 1

        mock_db = Mock()
        mock_db.query().filter().first.return_value = mock_session

        stats = await service.process_task_updates([], 1, mock_db)

        assert stats == {"updated": 0, "skipped": 0, "failed": 0}


class TestSyncAllPendingTodos:
    """Test sync_all_pending_todos method."""

    @pytest.mark.asyncio
    @patch("app.services.task_sync_service.list_integrations")
    async def test_sync_all_pending_todos_no_todos(self, mock_list):
        """Test sync_all_pending_todos with no pending todos."""
        from app.services.task_sync_service import TaskSyncService

        mock_list.return_value = []

        service = TaskSyncService()
        service.process_task_updates = AsyncMock(return_value={"updated": 0})

        mock_db = Mock()
        mock_db.query().filter().all.return_value = []
        mock_db.query().filter_by().one_or_none.return_value = None

        stats = await service.sync_all_pending_todos(1, mock_db)

        assert stats["synced"] == 0
        assert stats["failed"] == 0

    @pytest.mark.asyncio
    @patch("app.services.task_sync_service.list_integrations")
    async def test_sync_all_pending_todos_with_task_updates(self, mock_list):
        """Test sync_all_pending_todos processes task updates."""
        from app.services.task_sync_service import TaskSyncService

        mock_list.return_value = []

        service = TaskSyncService()
        service.process_task_updates = AsyncMock(return_value={"updated": 2})

        mock_db = Mock()
        mock_db.query().filter().all.return_value = []
        mock_db.query().filter_by().one_or_none.return_value = None

        task_updates = [{"title": "Task 1"}, {"title": "Task 2"}]
        stats = await service.sync_all_pending_todos(1, mock_db, task_updates)

        assert stats["updated"] == 2
        service.process_task_updates.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.task_sync_service.list_integrations")
    async def test_sync_all_pending_todos_success(self, mock_list):
        """Test successful sync_all_pending_todos."""
        from app.services.task_sync_service import TaskSyncService

        mock_list.return_value = []

        service = TaskSyncService()
        service.sync_todo = AsyncMock(return_value={"test": {"success": True}})

        mock_todo = Mock()

        mock_todo_query = Mock()
        mock_todo_query.filter().all.return_value = [mock_todo]

        # Session query returns None to simplify test
        mock_session_query = Mock()
        mock_session_query.filter_by().one_or_none.return_value = None

        mock_db = Mock()
        mock_db.query.side_effect = [mock_todo_query, mock_session_query]

        stats = await service.sync_all_pending_todos(1, mock_db)

        # Verify stats are correct
        assert stats["synced"] == 1
        assert stats["failed"] == 0
        assert stats["skipped"] == 0

    @pytest.mark.asyncio
    @patch("app.services.task_sync_service.list_integrations")
    async def test_sync_all_pending_todos_completed_with_warnings(self, mock_list):
        """Test sync marks session as completed_with_warnings when errors exist."""
        from app.services.task_sync_service import TaskSyncService

        mock_list.return_value = []

        service = TaskSyncService()
        service.sync_todo = AsyncMock(return_value={"test": {"success": True}})

        mock_session = type(
            "MockSession",
            (),
            {
                "id": 1,
                "processing_stages": {"summarizing": {"status": "failed"}},
                "last_error": "Summary failed",
                "status": None,
            },
        )()

        mock_todo = Mock()

        mock_todo_query = Mock()
        mock_todo_query.filter().all.return_value = [mock_todo]

        mock_session_query = Mock()
        mock_session_query.filter_by().one_or_none.return_value = mock_session

        mock_db = Mock()
        mock_db.query.side_effect = [mock_todo_query, mock_session_query]

        stats = await service.sync_all_pending_todos(1, mock_db)

        assert mock_session.status == "completed_with_warnings"

    @pytest.mark.asyncio
    @patch("app.services.task_sync_service.list_integrations")
    async def test_sync_all_pending_todos_handles_exceptions(self, mock_list):
        """Test sync_all_pending_todos handles sync exceptions."""
        from app.services.task_sync_service import TaskSyncService

        mock_list.return_value = []

        service = TaskSyncService()
        service.sync_todo = AsyncMock(side_effect=Exception("Sync error"))

        mock_todo = Mock()
        mock_db = Mock()
        mock_db.query().filter().all.return_value = [mock_todo]
        mock_db.query().filter_by().one_or_none.return_value = None

        stats = await service.sync_all_pending_todos(1, mock_db)

        assert stats["failed"] == 1


class TestDeleteFromTicktick:
    """Test delete_from_ticktick method."""

    @pytest.mark.asyncio
    @patch("app.services.task_sync_service.SessionLocal")
    @patch("app.services.ticktick.TickTickClient")
    async def test_delete_from_ticktick_success(
        self, mock_client_class, mock_session_local
    ):
        """Test successful deletion from TickTick."""
        from app.services.task_sync_service import TaskSyncService

        mock_client = Mock()
        mock_client.delete_task = AsyncMock()
        mock_client_class.return_value = mock_client

        mock_db = Mock()
        mock_session_local.return_value.__enter__.return_value = mock_db

        service = TaskSyncService()
        await service.delete_from_ticktick("task-123", "proj-1")

        mock_client.delete_task.assert_called_once_with("task-123", "proj-1")

    @pytest.mark.asyncio
    @patch("app.services.task_sync_service.SessionLocal")
    @patch("app.services.ticktick.TickTickClient")
    async def test_delete_from_ticktick_handles_error(
        self, mock_client_class, mock_session_local
    ):
        """Test delete_from_ticktick handles errors."""
        from app.services.task_sync_service import TaskSyncService

        mock_client = Mock()
        mock_client.delete_task = AsyncMock(side_effect=Exception("Delete failed"))
        mock_client_class.return_value = mock_client

        mock_db = Mock()
        mock_session_local.return_value.__enter__.return_value = mock_db

        service = TaskSyncService()

        with pytest.raises(Exception, match="Delete failed"):
            await service.delete_from_ticktick("task-123", "proj-1")


class TestScheduleTaskSync:
    """Test schedule_task_sync function."""

    @patch("app.services.task_sync_service.asyncio")
    def test_schedule_task_sync_success(self, mock_asyncio):
        """Test schedule_task_sync runs event loop."""
        from app.services.task_sync_service import schedule_task_sync

        mock_loop = Mock()
        mock_asyncio.new_event_loop.return_value = mock_loop

        schedule_task_sync(1)

        mock_asyncio.new_event_loop.assert_called_once()
        mock_asyncio.set_event_loop.assert_called_once_with(mock_loop)
        mock_loop.run_until_complete.assert_called_once()
        mock_loop.close.assert_called_once()

    @patch("app.services.task_sync_service.asyncio")
    def test_schedule_task_sync_handles_exception(self, mock_asyncio):
        """Test schedule_task_sync handles exceptions gracefully."""
        from app.services.task_sync_service import schedule_task_sync

        mock_loop = Mock()
        mock_loop.run_until_complete.side_effect = Exception("Loop failed")
        mock_asyncio.new_event_loop.return_value = mock_loop

        # Should not raise, just log
        schedule_task_sync(1)

        mock_loop.close.assert_called_once()


class TestAsyncTaskSync:
    """Test _async_task_sync function."""

    @pytest.mark.asyncio
    @patch("app.services.task_sync_service.task_sync_service")
    @patch("app.services.task_sync_service.SessionLocal")
    async def test_async_task_sync_success(self, mock_session_local, mock_service):
        """Test _async_task_sync calls service correctly."""
        from app.services.task_sync_service import _async_task_sync

        mock_db = Mock()
        mock_session_local.return_value.__enter__.return_value = mock_db

        mock_service.sync_all_pending_todos = AsyncMock()

        await _async_task_sync(1, [])

        mock_service.sync_all_pending_todos.assert_called_once_with(1, mock_db, [])

    @pytest.mark.asyncio
    @patch("app.services.task_sync_service.task_sync_service")
    @patch("app.services.task_sync_service.SessionLocal")
    async def test_async_task_sync_handles_exception(
        self, mock_session_local, mock_service
    ):
        """Test _async_task_sync handles exceptions."""
        from app.services.task_sync_service import _async_task_sync

        mock_db = Mock()
        mock_session_local.return_value.__enter__.return_value = mock_db

        mock_service.sync_all_pending_todos = AsyncMock(
            side_effect=Exception("Sync failed")
        )

        # Should not raise, just log
        await _async_task_sync(1, [])
