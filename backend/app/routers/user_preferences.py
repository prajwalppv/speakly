from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_session
from ..models import User
from ..schemas import UserPreferencesResponse, UserPreferencesUpdateRequest

router = APIRouter(prefix="/api/user/preferences", tags=["user"])


@router.get("", response_model=UserPreferencesResponse)
def get_user_preferences(
    current_user: User = Depends(get_current_user),
) -> UserPreferencesResponse:
    return UserPreferencesResponse(
        auto_approve_sessions=bool(current_user.auto_approve_sessions),
    )


@router.put("", response_model=UserPreferencesResponse)
def update_user_preferences(
    payload: UserPreferencesUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> UserPreferencesResponse:
    current_user.auto_approve_sessions = payload.auto_approve_sessions
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return UserPreferencesResponse(
        auto_approve_sessions=bool(current_user.auto_approve_sessions),
    )
