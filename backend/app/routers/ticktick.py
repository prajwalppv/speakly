"""TickTick OAuth and integration endpoints."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

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


@router.get("/connect")
async def connect_ticktick(
    user_id: int = Query(default=1, description="User ID to connect TickTick for"),
    state: Optional[str] = Query(default=None, description="CSRF state parameter"),
):
    """
    Initiate TickTick OAuth flow.

    Redirects user to TickTick authorization page.
    """
    try:
        # Generate state if not provided (in production, should store in session)
        if not state:
            state = f"user_{user_id}"

        auth_url = TickTickOAuth.get_authorization_url(state=state)
        return RedirectResponse(url=auth_url, status_code=302)

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
        user_id = 1  # Default user for now
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
    user_id: int = Query(default=1, description="User ID to check status for"),
    db: Session = Depends(get_session),
):
    """
    Check if TickTick is connected for a user.
    """
    try:
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
            "user_id": user_id,
            "error": str(e),
        }


@router.get("/projects")
async def get_projects(
    user_id: int = Query(default=1, description="User ID"),
    db: Session = Depends(get_session),
):
    """
    Get all TickTick projects (lists) for the user.
    """
    try:
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
    user_id: int = Query(default=1, description="User ID to disconnect TickTick for"),
    db: Session = Depends(get_session),
):
    """
    Disconnect TickTick integration for a user.

    Removes stored token from database.
    """
    from ..models import TickTickToken

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
