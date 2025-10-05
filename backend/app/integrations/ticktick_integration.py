"""
TickTick integration following SOLID principles.

This module provides a clean, pluggable TickTick integration
that implements the TaskSyncIntegration interface.
"""

from __future__ import annotations

import logging
from typing import Any

from rapidfuzz import fuzz, process
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Todo
from ..services.ticktick import TickTickClient
from .base import IntegrationError, IntegrationType, TaskSyncIntegration

logger = logging.getLogger(__name__)


class TickTickIntegration(TaskSyncIntegration[Todo]):
    """
    TickTick integration for task synchronization.

    Follows Single Responsibility Principle - only handles TickTick sync logic.
    """

    @property
    def name(self) -> str:
        return "ticktick"

    @property
    def integration_type(self) -> IntegrationType:
        return IntegrationType.TASK_SYNC

    def is_enabled(self) -> bool:
        """Check if TickTick integration is enabled."""
        return settings.ticktick_enabled

    def is_connected(self, user_id: int, db: Session) -> bool:
        """Check if user has connected TickTick."""
        if not self.is_enabled():
            return False

        try:
            client = TickTickClient(user_id, db)
            client._get_token()  # Will raise if no token
            return True
        except Exception:
            return False

    def get_connection_status(
        self, user_id: int, db: Session
    ) -> dict[str, Any]:
        """Get detailed TickTick connection status."""
        if not self.is_enabled():
            return {
                "connected": False,
                "error": "TickTick integration is not enabled",
            }

        try:
            client = TickTickClient(user_id, db)
            token = client._get_token()
            return {
                "connected": True,
                "user_id": user_id,
                "expires_at": token.expires_at.isoformat() if token.expires_at else None,
                "scope": token.scope,
            }
        except Exception as e:
            return {
                "connected": False,
                "user_id": user_id,
                "error": str(e),
            }

    async def sync_task(
        self, todo: Todo, user_id: int, db: Session
    ) -> dict[str, Any]:
        """
        Sync a TODO to TickTick with rich metadata and session linking.

        Args:
            todo: The TODO to sync
            user_id: User ID
            db: Database session

        Returns:
            dict: Sync result with task_id and metadata

        Raises:
            IntegrationError: If sync fails
        """
        if not self.is_enabled():
            raise IntegrationError("TickTick integration is not enabled")

        try:
            client = TickTickClient(user_id, db)

            # Get or create Speakly project
            project_id = await client.get_or_create_speakly_project()

            # Get session details for rich metadata
            from ..models import Session as SessionModel, Transcription
            
            # Prepare content with metadata
            content_parts = []
            
            # Add session reference at the top
            content_parts.append(f"📎 From recording #{todo.session_id}")
            
            # Add session context if description exists
            if todo.session.description:
                content_parts.append(f"\n📝 Recording: {todo.session.description}")
            else:
                # Try to get snippet from transcription
                if todo.session.transcriptions:
                    transcript = todo.session.transcriptions[0].text
                    if transcript:
                        snippet = transcript[:150] + "..." if len(transcript) > 150 else transcript
                        content_parts.append(f"\n**Context:**\n{snippet}")
            
            if todo.source_excerpt:
                content_parts.append(f'\n**Exact quote:**\n"{todo.source_excerpt}"')
            
            if todo.due_hint:
                content_parts.append(f"\n⏰ {todo.due_hint}")
            
            if todo.confidence:
                content_parts.append(f"\n🎯 Confidence: {int(todo.confidence * 100)}%")
            
            content = "\n".join(content_parts)

            # Create task with rich metadata
            # Add session ID to title for quick reference
            task_title = f"{todo.title} #{todo.session_id}"
            
            task = await client.create_task(
                title=task_title,
                content=content,
                project_id=project_id,
                tags=["speakly"],  # Only one tag to avoid bloat
            )

            logger.info(
                f"Successfully synced TODO {todo.id} to TickTick with rich metadata",
                extra={
                    "todo_id": todo.id,
                    "task_id": task.get("id"),
                    "project_id_from_ticktick": task.get("projectId"),
                    "session_id": todo.session_id
                },
            )

            return {
                "task_id": task.get("id"),
                "project_id": task.get("projectId"),  # Use TickTick's response, not our input
                "metadata": task,
            }

        except Exception as e:
            logger.error(
                f"Failed to sync TODO {todo.id} to TickTick: {str(e)}",
                extra={"todo_id": todo.id, "error": str(e)},
            )
            raise IntegrationError(f"TickTick sync failed: {str(e)}") from e

    async def get_or_create_project(
        self, project_name: str, user_id: int, db: Session
    ) -> str:
        """Get or create a project in TickTick."""
        if not self.is_enabled():
            raise IntegrationError("TickTick integration is not enabled")

        try:
            client = TickTickClient(user_id, db)
            
            # For now, always use Speakly project
            # In the future, this could support custom project names
            return await client.get_or_create_speakly_project()
            
        except Exception as e:
            raise IntegrationError(f"Failed to get/create project: {str(e)}") from e

    async def get_projects(
        self, user_id: int, db: Session
    ) -> list[dict[str, Any]]:
        """Get all projects from TickTick."""
        if not self.is_enabled():
            raise IntegrationError("TickTick integration is not enabled")

        try:
            client = TickTickClient(user_id, db)
            return await client.get_projects()
        except Exception as e:
            raise IntegrationError(f"Failed to get projects: {str(e)}") from e

    async def search_tasks(
        self, query: str, user_id: int, db: Session
    ) -> list[dict[str, Any]]:
        """Search for tasks in TickTick by title/content with fuzzy matching."""
        if not self.is_enabled():
            raise IntegrationError("TickTick integration is not enabled")

        try:
            client = TickTickClient(user_id, db)
            project_id = await client.get_or_create_speakly_project()
            
            # Get all tasks
            all_tasks = await client.get_tasks(project_id)
            
            # Use fuzzy matching to find best matches
            query_lower = query.lower()
            scored_tasks = []
            
            for task in all_tasks:
                title = task.get("title", "")
                content = task.get("content", "")
                
                # Calculate fuzzy match scores
                title_score = fuzz.partial_ratio(query_lower, title.lower())
                content_score = fuzz.partial_ratio(query_lower, content.lower())
                
                # Use the higher score
                best_score = max(title_score, content_score)
                
                # Only include if score is above threshold (70%)
                if best_score >= 70:
                    task_with_score = task.copy()
                    task_with_score["match_score"] = best_score
                    scored_tasks.append(task_with_score)
            
            # Sort by score (highest first)
            scored_tasks.sort(key=lambda x: x["match_score"], reverse=True)
            
            logger.info(
                f"Fuzzy search found {len(scored_tasks)} tasks for '{query}'",
                extra={
                    "user_id": user_id,
                    "query": query,
                    "results": len(scored_tasks),
                    "top_score": scored_tasks[0]["match_score"] if scored_tasks else 0
                }
            )
            
            return scored_tasks
            
        except Exception as e:
            raise IntegrationError(f"Failed to search tasks: {str(e)}") from e

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        user_id: int,
        db: Session,
    ) -> dict[str, Any]:
        """Update a task's status in TickTick.
        
        Args:
            task_id: TickTick task ID
            status: Status string (completed, in_progress, blocked, cancelled)
            user_id: User ID
            db: Database session
            
        Returns:
            Updated task data
        """
        if not self.is_enabled():
            raise IntegrationError("TickTick integration is not enabled")

        try:
            client = TickTickClient(user_id, db)
            
            # Map our status to TickTick status
            # TickTick: 0=normal, 1=note, 2=completed
            updates = {}
            
            if status == "completed":
                updates["status"] = 2
            elif status == "cancelled":
                # Mark as completed with a note
                updates["status"] = 2
                updates["content"] = f"Cancelled via Speakly\n{updates.get('content', '')}"
            elif status == "blocked":
                # Add to title/content to indicate blocked
                updates["title"] = f"[BLOCKED] {updates.get('title', '')}"
            # in_progress doesn't change status (remains 0)
            
            if updates:
                return await client.update_task(task_id, updates)
            
            return {"task_id": task_id, "no_update": True}
            
        except Exception as e:
            logger.error(
                f"Failed to update task {task_id} status: {str(e)}",
                extra={"task_id": task_id, "status": status, "error": str(e)},
            )
            raise IntegrationError(f"TickTick status update failed: {str(e)}") from e

    async def process_task_update(
        self,
        update: dict[str, Any],
        user_id: int,
        db: Session,
    ) -> dict[str, Any]:
        """Process a task update from voice note.
        
        This searches for matching tasks and updates them.
        
        Args:
            update: Dict with 'title', 'status', 'notes', 'confidence'
            user_id: User ID
            db: Database session
            
        Returns:
            Result dict with matched task and update status
        """
        if not self.is_enabled():
            raise IntegrationError("TickTick integration is not enabled")

        try:
            title = update.get("title", "")
            status = update.get("status", "")
            confidence = update.get("confidence", 0.0)
            
            # Skip low confidence updates
            if confidence < 0.7:
                logger.info(f"Skipping low confidence update: {confidence}")
                return {"skipped": True, "reason": "low_confidence", "confidence": confidence}
            
            # Search for matching tasks
            matching_tasks = await self.search_tasks(title, user_id, db)
            
            if not matching_tasks:
                logger.info(f"No matching tasks found for: {title}")
                return {"skipped": True, "reason": "no_match", "query": title}
            
            # Use the first match (best match)
            task = matching_tasks[0]
            task_id = task.get("id")
            match_score = task.get("match_score", 0)
            
            # Update the task status
            result = await self.update_task_status(task_id, status, user_id, db)
            
            logger.info(
                f"Updated task {task_id} to status '{status}' (match score: {match_score}%)",
                extra={
                    "task_id": task_id,
                    "status": status,
                    "matched_title": task.get("title"),
                    "match_score": match_score,
                    "query": title,
                }
            )
            
            return {
                "success": True,
                "task_id": task_id,
                "matched_title": task.get("title"),
                "status": status,
                "match_score": match_score,
                "match_quality": "excellent" if match_score >= 90 else "good" if match_score >= 80 else "fair",
                "auto_updated": True,  # Flag for UI
            }
            
        except Exception as e:
            logger.error(
                f"Failed to process task update: {str(e)}",
                extra={"update": update, "error": str(e)},
            )
            raise IntegrationError(f"Task update processing failed: {str(e)}") from e


# Create singleton instance
ticktick_integration = TickTickIntegration()
