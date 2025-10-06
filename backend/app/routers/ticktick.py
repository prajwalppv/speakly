"""TickTick OAuth and integration endpoints."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_session
from ..config import settings
from ..models import User
from ..services.ticktick import (
    TickTickAuthError,
    TickTickClient,
    TickTickNotConfiguredError,
    TickTickOAuth,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ticktick", tags=["ticktick"])


def _build_state(user_id: int, state: str | None) -> str:
    return state or f"user_{user_id}"


@router.get("/connect")
async def connect_ticktick(
    state: Optional[str] = Query(default=None, description="CSRF state parameter"),
    current_user: User = Depends(get_current_user),
):
    """Initiate TickTick OAuth flow with a HTTP redirect."""
    try:
        user_id = current_user.id
        resolved_state = _build_state(user_id, state)
        auth_url = TickTickOAuth.get_authorization_url(state=resolved_state)
        return RedirectResponse(url=auth_url, status_code=302)

    except TickTickNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/connect/url")
async def connect_ticktick_url(
    state: Optional[str] = Query(default=None, description="CSRF state parameter"),
    current_user: User = Depends(get_current_user),
):
    """Return the TickTick OAuth authorization URL (no redirect)."""
    try:
        user_id = current_user.id
        resolved_state = _build_state(user_id, state)
        auth_url = TickTickOAuth.get_authorization_url(state=resolved_state)
        return {"authorization_url": auth_url}

    except TickTickNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/callback")
async def ticktick_callback(
    code: str = Query(..., description="Authorization code from TickTick"),
    state: Optional[str] = Query(default=None, description="State parameter"),
    db: Session = Depends(get_session),
):
    """
    Handle OAuth callback from TickTick.

    Exchanges authorization code for access token and stores it.
    """
    try:
        # Extract user_id from state (in production, verify state from session)
        user_id = 1  # Fallback for legacy state values
        if state and state.startswith("user_"):
            try:
                user_id = int(state.split("_")[1])
            except (ValueError, IndexError):
                pass

        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Exchange code for token
        token_data = await TickTickOAuth.exchange_code_for_token(code)

        # Save token to database
        TickTickOAuth.save_token(db, user, token_data)

        logger.info(f"Successfully connected TickTick for user {user_id}")

        # Redirect to frontend with success message
        frontend_url = settings.frontend_base_url.rstrip("/")
        return RedirectResponse(url=f"{frontend_url}/?ticktick=connected", status_code=302)

    except TickTickAuthError as e:
        logger.error(f"TickTick auth error: {str(e)}")
        # Redirect to frontend with error
        frontend_url = settings.frontend_base_url.rstrip("/")
        return RedirectResponse(url=f"{frontend_url}/?ticktick=error&message={str(e)}", status_code=302)

    except TickTickNotConfiguredError as e:
        frontend_url = settings.frontend_base_url.rstrip("/")
        return RedirectResponse(url=f"{frontend_url}/?ticktick=error&message={str(e)}", status_code=302)

    except Exception as e:
        logger.exception("Unexpected error during TickTick callback")
        frontend_url = settings.frontend_base_url.rstrip("/")
        return RedirectResponse(url=f"{frontend_url}/?ticktick=error&message=Connection failed", status_code=302)


@router.get("/status")
async def ticktick_status(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Check if TickTick is connected for a user.
    """
    try:
        user_id = current_user.id
        client = TickTickClient(user_id, db)
        token = client._get_token()

        return {
            "connected": True,
            "user_id": user_id,
            "expires_at": token.expires_at.isoformat(),
            "scope": token.scope,
        }

    except (TickTickNotConfiguredError, TickTickAuthError) as e:
        return {
            "connected": False,
            "user_id": current_user.id,
            "error": str(e),
        }


@router.get("/projects")
async def get_projects(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get all TickTick projects (lists) for the user.
    """
    try:
        user_id = current_user.id
        client = TickTickClient(user_id, db)
        projects = await client.get_projects()

        return {
            "success": True,
            "user_id": user_id,
            "projects": projects,
        }

    except (TickTickNotConfiguredError, TickTickAuthError) as e:
        raise HTTPException(status_code=401, detail=str(e))

    except Exception as e:
        logger.exception("Error fetching TickTick projects")
        raise HTTPException(status_code=500, detail="Failed to fetch projects")


@router.post("/disconnect")
async def disconnect_ticktick(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Disconnect TickTick integration for a user.

    Removes stored token from database.
    """
    from ..models import TickTickToken

    user_id = current_user.id
    token = db.query(TickTickToken).filter(TickTickToken.user_id == user_id).first()

    if not token:
        raise HTTPException(status_code=404, detail="No TickTick connection found")

    db.delete(token)
    db.commit()

    logger.info(f"Disconnected TickTick for user {user_id}")

    return {
        "success": True,
        "message": "TickTick disconnected successfully",
        "user_id": user_id,
    }
