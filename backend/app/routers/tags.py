"""API endpoints for tag management."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_session
from ..models import Session as SessionModel
from ..models import SessionTag, Tag
from ..schemas import TagCreate, TagResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=list[TagResponse])
async def list_tags(
    db: Session = Depends(get_session),
    category: str | None = None,
):
    """
    Get all available tags with usage counts.

    Query params:
        category: Filter by tag category (optional)
    """
    query = (
        db.query(Tag, func.count(SessionTag.id).label("usage_count"))
        .outerjoin(SessionTag)
        .group_by(Tag.id)
    )

    if category:
        query = query.filter(Tag.category == category)

    results = query.all()

    return [
        TagResponse(
            id=tag.id,
            name=tag.name,
            category=tag.category,
            color=tag.color,
            auto_generated=tag.auto_generated,
            usage_count=usage_count or 0,
            created_at=tag.created_at,
        )
        for tag, usage_count in results
    ]


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag_data: TagCreate,
    db: Session = Depends(get_session),
):
    """
    Create a new custom tag.

    Requires Pro subscription in production.
    """
    # Check if feature is enabled
    if not settings.feature_custom_tags:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "feature_not_available",
                "message": "Custom tags require a Pro subscription",
                "feature": "custom_tags",
                "upgrade_url": "/pricing",
            },
        )

    # Check if tag already exists
    existing = db.query(Tag).filter(Tag.name == tag_data.name.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tag '{tag_data.name}' already exists",
        )

    # Create tag
    from ..services.tagging import TaggingService

    tagging_service = TaggingService()

    tag = Tag(
        name=tag_data.name.lower(),
        category=tag_data.category or "custom",
        color=tag_data.color
        or tagging_service.assign_color(tag_data.category or "custom"),
        auto_generated=False,
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)

    logger.info(f"Created custom tag: {tag.name}")

    return TagResponse(
        id=tag.id,
        name=tag.name,
        category=tag.category,
        color=tag.color,
        auto_generated=tag.auto_generated,
        usage_count=0,
        created_at=tag.created_at,
    )


@router.post(
    "/sessions/{session_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def add_tag_to_session(
    session_id: int,
    tag_id: int,
    db: Session = Depends(get_session),
):
    """Add an existing tag to a session."""
    # Verify session exists
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    # Verify tag exists
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tag {tag_id} not found"
        )

    # Check if already associated
    existing = (
        db.query(SessionTag)
        .filter(SessionTag.session_id == session_id, SessionTag.tag_id == tag_id)
        .first()
    )

    if existing:
        return  # Already associated, no-op

    # Create association
    session_tag = SessionTag(
        session_id=session_id, tag_id=tag_id, confidence=1.0, auto_generated=False
    )
    db.add(session_tag)
    db.commit()

    logger.info(f"Added tag {tag.name} to session {session_id}")


@router.delete(
    "/sessions/{session_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_tag_from_session(
    session_id: int,
    tag_id: int,
    db: Session = Depends(get_session),
):
    """Remove a tag from a session."""
    deleted = (
        db.query(SessionTag)
        .filter(SessionTag.session_id == session_id, SessionTag.tag_id == tag_id)
        .delete()
    )

    if deleted == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag association not found"
        )

    db.commit()
    logger.info(f"Removed tag {tag_id} from session {session_id}")


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: int,
    db: Session = Depends(get_session),
):
    """
    Delete a tag.

    This will also remove all associations with sessions.
    """
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tag {tag_id} not found"
        )

    # Only allow deletion of custom (non-auto-generated) tags
    if tag.auto_generated:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete auto-generated tags",
        )

    db.delete(tag)
    db.commit()

    logger.info(f"Deleted tag: {tag.name}")
