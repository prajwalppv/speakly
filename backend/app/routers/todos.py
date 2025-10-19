"""
Todo/Task management endpoints.

Provides APIs for creating, updating, and deleting tasks manually.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_session
from ..models import Session as SessionModel
from ..models import Todo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/todos", tags=["todos"])


# Request/Response schemas
class CreateTodoRequest(BaseModel):
    title: str
    due_hint: str | None = None
    source_excerpt: str | None = None
    confidence: float = 1.0  # Manual tasks have 100% confidence


class UpdateTodoRequest(BaseModel):
    title: str | None = None
    due_hint: str | None = None
    status: str | None = None
    source_excerpt: str | None = None


class TodoResponse(BaseModel):
    id: int
    title: str
    due_hint: str | None
    confidence: float | None
    status: str
    source_excerpt: str | None
    ticktick_sync_status: str
    ticktick_task_id: str | None
    created_at: str
    updated_at: str


@router.post(
    "/sessions/{session_id}/todos",
    response_model=TodoResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_todo(
    session_id: int,
    request: CreateTodoRequest,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """
    Create a new todo manually for a session.

    Args:
        session_id: Session to add todo to
        request: Todo creation data
        db: Database session

    Returns:
        Created todo

    Raises:
        HTTPException: 404 if session not found
    """
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    # Create todo
    todo = Todo(
        session_id=session_id,
        title=request.title,
        due_hint=request.due_hint,
        source_excerpt=request.source_excerpt,
        confidence=request.confidence,
        status="active",
        ticktick_sync_status="pending",
    )
    db.add(todo)

    # Update session todo count
    session.todo_count = (
        db.query(Todo).filter(Todo.session_id == session_id).count() + 1
    )
    db.commit()
    db.refresh(todo)

    logger.info(
        f"Manually created todo {todo.id} for session {session_id}",
        extra={"todo_id": todo.id, "session_id": session_id, "title": todo.title},
    )

    return {
        "id": todo.id,
        "title": todo.title,
        "due_hint": todo.due_hint,
        "confidence": todo.confidence,
        "status": todo.status,
        "source_excerpt": todo.source_excerpt,
        "ticktick_sync_status": todo.ticktick_sync_status,
        "ticktick_task_id": todo.ticktick_task_id,
        "created_at": todo.created_at.isoformat(),
        "updated_at": todo.updated_at.isoformat(),
    }


@router.put("/{todo_id}", response_model=TodoResponse)
async def update_todo(
    todo_id: int,
    request: UpdateTodoRequest,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """
    Update an existing todo in both local database and TickTick.

    Args:
        todo_id: ID of todo to update
        request: Update data
        db: Database session

    Returns:
        Updated todo

    Raises:
        HTTPException: 404 if todo not found
    """
    todo = db.query(Todo).filter(Todo.id == todo_id).first()

    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Todo {todo_id} not found"
        )

    # Update local database first
    updates_made = []
    if request.title is not None:
        todo.title = request.title
        updates_made.append("title")
    if request.due_hint is not None:
        todo.due_hint = request.due_hint
        updates_made.append("due_hint")
    if request.status is not None:
        todo.status = request.status
        updates_made.append("status")
    if request.source_excerpt is not None:
        todo.source_excerpt = request.source_excerpt
        updates_made.append("source_excerpt")

    db.commit()
    db.refresh(todo)

    # Update in TickTick if task is synced
    if todo.ticktick_task_id and todo.ticktick_project_id:
        try:
            from ..services.ticktick import TickTickClient

            client = TickTickClient(user_id=1, db=db)  # TODO: Get actual user_id

            # Prepare TickTick updates
            ticktick_updates = {}
            if request.title is not None:
                ticktick_updates["title"] = request.title
            if request.status is not None:
                # Handle status mapping: completed -> use complete endpoint
                if request.status.lower() in ["completed", "done"]:
                    await client.complete_task(
                        todo.ticktick_task_id, todo.ticktick_project_id
                    )
                    todo.ticktick_sync_status = "synced"
                else:
                    ticktick_updates["status"] = 0  # Mark as normal/active

            # Apply other updates if any
            if ticktick_updates:
                await client.update_task(
                    todo.ticktick_task_id, ticktick_updates, todo.ticktick_project_id
                )
                todo.ticktick_sync_status = "synced"

            db.commit()

            logger.info(
                f"Updated todo {todo_id} in both local DB and TickTick",
                extra={
                    "todo_id": todo_id,
                    "updates": updates_made,
                    "ticktick_updates": list(ticktick_updates.keys()),
                },
            )

        except Exception as e:
            logger.error(f"Failed to update todo {todo_id} in TickTick: {e}")
            todo.ticktick_sync_status = "error"
            todo.ticktick_sync_error = str(e)
            db.commit()
    else:
        logger.info(
            f"Updated todo {todo_id} in local DB only (not synced to TickTick)",
            extra={"todo_id": todo_id, "updates": updates_made},
        )

    return {
        "id": todo.id,
        "title": todo.title,
        "due_hint": todo.due_hint,
        "confidence": todo.confidence,
        "status": todo.status,
        "source_excerpt": todo.source_excerpt,
        "ticktick_sync_status": todo.ticktick_sync_status,
        "ticktick_task_id": todo.ticktick_task_id,
        "created_at": todo.created_at.isoformat(),
        "updated_at": todo.updated_at.isoformat(),
    }


@router.delete(
    "/{todo_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def delete_todo(
    todo_id: int,
    db: Session = Depends(get_session),
) -> None:
    """
    Delete a todo from both local database and TickTick.

    Args:
        todo_id: ID of todo to delete
        db: Database session

    Raises:
        HTTPException: 404 if todo not found
    """
    todo = db.query(Todo).filter(Todo.id == todo_id).first()

    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Todo {todo_id} not found"
        )

    session_id = todo.session_id
    ticktick_task_id = todo.ticktick_task_id
    ticktick_project_id = todo.ticktick_project_id

    # Delete from TickTick first if synced
    if ticktick_task_id and ticktick_project_id:
        try:
            from ..services.ticktick import TickTickClient

            client = TickTickClient(user_id=1, db=db)  # TODO: Get actual user_id
            await client.delete_task(ticktick_task_id, ticktick_project_id)

            logger.info(f"Deleted task {ticktick_task_id} from TickTick successfully")

        except Exception as e:
            logger.warning(f"Failed to delete todo {todo_id} from TickTick: {e}")
            # Continue with local deletion even if TickTick fails

    # Delete from local database
    db.delete(todo)

    # Update session todo count
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if session:
        session.todo_count = (
            db.query(Todo).filter(Todo.session_id == session_id).count()
        )

    db.commit()

    logger.info(
        f"Deleted todo {todo_id} from local database",
        extra={
            "todo_id": todo_id,
            "session_id": session_id,
            "ticktick_deleted": bool(ticktick_task_id),
        },
    )


@router.post("/{todo_id}/resync", status_code=status.HTTP_202_ACCEPTED)
def resync_todo(
    todo_id: int,
    db: Session = Depends(get_session),
) -> dict[str, str]:
    """
    Re-trigger sync for a todo to TickTick.

    Args:
        todo_id: ID of todo to resync
        db: Database session

    Returns:
        Status message

    Raises:
        HTTPException: 404 if todo not found
    """
    todo = db.query(Todo).filter(Todo.id == todo_id).first()

    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Todo {todo_id} not found"
        )

    # Reset sync status to trigger re-sync
    todo.ticktick_sync_status = "pending"
    todo.ticktick_sync_error = None
    db.commit()

    # Trigger sync (would call task_sync_service in production)
    from ..services.task_sync_service import schedule_task_sync

    schedule_task_sync(todo.session_id)

    logger.info(f"Re-sync requested for todo {todo_id}", extra={"todo_id": todo_id})

    return {"message": f"Todo {todo_id} queued for re-sync"}
