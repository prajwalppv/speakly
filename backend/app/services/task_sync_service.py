"""
Generic Task Synchronization Service.

This service follows the Dependency Inversion Principle - it depends on
the TaskSyncIntegration interface, not concrete implementations.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..integrations.base import IntegrationType, TaskSyncIntegration
from ..integrations.registry import list_integrations
from ..models import Todo

logger = logging.getLogger(__name__)


class TaskSyncService:
    """
    Service for synchronizing tasks to external integrations.

    Follows Open/Closed Principle - open for extension (new integrations)
    but closed for modification (core sync logic stays the same).
    """

    def __init__(self):
        self._integrations: list[TaskSyncIntegration] | None = None
        self._loaded = False

    def _load_integrations(self) -> None:
        """Load all enabled task sync integrations (lazy loading)."""
        if self._loaded:
            return

        all_integrations = list_integrations(enabled_only=True)
        self._integrations = [
            integration
            for integration in all_integrations
            if integration.integration_type == IntegrationType.TASK_SYNC
            and isinstance(integration, TaskSyncIntegration)
        ]
        self._loaded = True

        logger.info(
            f"Loaded {len(self._integrations)} task sync integrations",
            extra={"integrations": [i.name for i in self._integrations]},
        )

    async def sync_todo(self, todo: Todo, db: Session) -> dict[str, dict]:
        """
        Sync a TODO to all connected integrations.

        Args:
            todo: The TODO to sync
            db: Database session

        Returns:
            dict: Results from each integration {integration_name: result}
        """
        # Lazy load integrations on first use
        self._load_integrations()

        if not self._integrations:
            logger.debug("No task sync integrations enabled")
            return {}

        user_id = todo.session.user_id
        results = {}

        for integration in self._integrations:
            try:
                # Check if user has connected this integration
                if not integration.is_connected(user_id, db):
                    logger.debug(
                        f"User {user_id} not connected to {integration.name}, skipping"
                    )
                    continue

                # Sync the task
                result = await integration.sync_task(todo, user_id, db)
                results[integration.name] = {
                    "success": True,
                    "data": result,
                }

                # Update TODO with sync info
                self._update_todo_sync_status(todo, integration.name, result, db)

                logger.info(
                    f"Successfully synced TODO {todo.id} to {integration.name}",
                    extra={
                        "todo_id": todo.id,
                        "integration": integration.name,
                    },
                )

            except Exception as e:
                logger.error(
                    f"Failed to sync TODO {todo.id} to {integration.name}: {str(e)}",
                    extra={
                        "todo_id": todo.id,
                        "integration": integration.name,
                        "error": str(e),
                    },
                )
                results[integration.name] = {
                    "success": False,
                    "error": str(e),
                }

                # Update TODO with error
                self._update_todo_sync_status(
                    todo, integration.name, None, db, error=str(e)
                )

        return results

    def _update_todo_sync_status(
        self,
        todo: Todo,
        integration_name: str,
        result: dict | None,
        db: Session,
        error: str | None = None,
    ) -> None:
        """Update TODO sync status for a specific integration."""
        # For now, only update for TickTick (backward compatibility)
        # In the future, we'll have a proper sync_status table
        if integration_name == "ticktick":
            if result:
                todo.ticktick_task_id = result.get("task_id")
                todo.ticktick_project_id = result.get("project_id")
                todo.ticktick_synced_at = datetime.utcnow()
                todo.ticktick_sync_status = "synced"
                todo.ticktick_sync_error = None
            elif error:
                todo.ticktick_sync_status = "error"
                todo.ticktick_sync_error = error

            db.commit()

    async def process_task_updates(
        self, task_updates: list[dict], session_id: int, db: Session
    ) -> dict[str, int]:
        """
        Process task updates from voice notes.

        Args:
            task_updates: List of task update dicts from LLM extraction
            session_id: Session ID
            db: Database session

        Returns:
            dict: Statistics (updated, skipped, failed counts)
        """
        self._load_integrations()

        stats = {"updated": 0, "skipped": 0, "failed": 0}

        # Get user_id from session
        from ..models import Session as SessionModel

        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            logger.error(f"Session {session_id} not found")
            return stats

        user_id = session.user_id

        logger.info(
            f"Processing {len(task_updates)} task updates for session {session_id}",
            extra={"session_id": session_id, "update_count": len(task_updates)},
        )

        for update in task_updates:
            try:
                # Process through each connected integration
                for integration in self._integrations:
                    if not integration.is_connected(user_id, db):
                        continue

                    # Check if integration supports task updates
                    if hasattr(integration, "process_task_update"):
                        result = await integration.process_task_update(
                            update, user_id, db
                        )

                        if result.get("success"):
                            stats["updated"] += 1
                            logger.info(
                                f"Updated task via {integration.name}",
                                extra={
                                    "integration": integration.name,
                                    "result": result,
                                },
                            )
                        elif result.get("skipped"):
                            stats["skipped"] += 1

            except Exception:
                logger.exception(f"Failed to process task update: {update}")
                stats["failed"] += 1

        logger.info(
            f"Task updates complete: {stats}",
            extra={"session_id": session_id, "stats": stats},
        )

        return stats

    async def sync_all_pending_todos(
        self, session_id: int, db: Session, task_updates: list[dict] | None = None
    ) -> dict[str, int]:
        """
        Sync all pending TODOs for a session and process task updates.

        Args:
            session_id: Session ID
            db: Database session
            task_updates: Optional list of task updates from voice notes

        Returns:
            dict: Statistics (synced, failed, skipped, updated counts)
        """
        # Lazy load integrations on first use
        self._load_integrations()

        stats = {"synced": 0, "failed": 0, "skipped": 0, "updated": 0}

        # First, process task updates if provided
        if task_updates:
            update_stats = await self.process_task_updates(task_updates, session_id, db)
            stats["updated"] = update_stats.get("updated", 0)
            # Don't add skipped/failed from updates to avoid confusion

        # Then sync new TODOs
        todos = (
            db.query(Todo)
            .filter(
                Todo.session_id == session_id,
                Todo.ticktick_sync_status.in_(["pending", "error"]),
            )
            .all()
        )

        logger.info(
            f"Syncing {len(todos)} pending TODOs for session {session_id}",
            extra={"session_id": session_id, "todo_count": len(todos)},
        )

        for todo in todos:
            try:
                results = await self.sync_todo(todo, db)
                if any(r.get("success") for r in results.values()):
                    stats["synced"] += 1
                elif results:
                    stats["failed"] += 1
                else:
                    stats["skipped"] += 1
            except Exception:
                logger.exception(f"Failed to sync TODO {todo.id}")
                stats["failed"] += 1

        logger.info(
            f"Task sync complete for session {session_id}: {stats}",
            extra={"session_id": session_id, "stats": stats},
        )

        # Update processing stage: syncing complete
        from datetime import datetime

        from ..models import Session as SessionModel

        session = db.query(SessionModel).filter_by(id=session_id).one_or_none()
        if session and session.processing_stages:
            # Must create a copy for SQLAlchemy to detect the change
            stages = session.processing_stages.copy()
            stages["syncing_tasks"] = {
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
            }
            session.processing_stages = stages

            # Check if any previous stages failed
            has_failures = any(
                stage_data.get("status") == "failed"
                for stage_data in session.processing_stages.values()
                if isinstance(stage_data, dict)
            )

            # Set session status - use warnings if any stage failed
            if has_failures or session.last_error:
                session.status = "completed_with_warnings"
                logger.warning(
                    f"Task sync completed for session {session_id}, session marked as completed with warnings",
                    extra={"session_id": session_id, "error": session.last_error},
                )
            else:
                session.status = "completed"
                logger.info(
                    f"Task sync completed for session {session_id}, session marked as completed",
                    extra={"session_id": session_id},
                )

            db.commit()

        return stats

    async def delete_from_ticktick(
        self, task_id: str, project_id: str, user_id: int
    ) -> None:
        """
        Delete a task from TickTick by task ID and project ID.

        Args:
            task_id: TickTick task ID to delete
            project_id: TickTick project ID where the task exists
            user_id: Speakly user ID that owns the TickTick credential
        """
        # Import here to get the TickTick client lazily
        from ..services.ticktick import TickTickClient

        with SessionLocal() as db:
            try:
                client = TickTickClient(user_id=user_id, db=db)
                await client.delete_task(task_id, project_id)
                logger.info(
                    f"Deleted task {task_id} from project {project_id} in TickTick"
                )
            except Exception as e:
                logger.exception(f"Failed to delete task {task_id} from TickTick: {e}")
                raise


# Create singleton instance
task_sync_service = TaskSyncService()


def schedule_task_sync(session_id: int, task_updates: list[dict] | None = None) -> None:
    """
    Schedule task sync in the current thread context.

    Args:
        session_id: Session ID to sync TODOs for
        task_updates: Optional list of task updates extracted from transcript
    """
    try:
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_async_task_sync(session_id, task_updates))
        finally:
            loop.close()
    except Exception:
        logger.exception(f"Failed to schedule task sync for session {session_id}")


async def _async_task_sync(
    session_id: int, task_updates: list[dict] | None = None
) -> None:
    """Async wrapper for task sync."""

    try:
        with SessionLocal() as db:
            await task_sync_service.sync_all_pending_todos(session_id, db, task_updates)
    except Exception:
        logger.exception(f"Task sync failed for session {session_id}")
