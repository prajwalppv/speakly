"""
Authentication and authorization utilities for Clerk JWT tokens.

This module handles:
- JWT token verification from Clerk
- User extraction from tokens
- User provisioning on first login
- FastAPI dependency for authenticated routes
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.algorithms import RSAAlgorithm
from sqlalchemy.orm import Session

from .config import settings
from .database import get_session
from .models import User

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()

# Cache for Clerk JWKS (public keys)
_jwks_cache: dict[str, Any] | None = None
_jwks_cache_expiry: datetime | None = None
_jwks_cache_lock = Lock()


def _extract_cache_ttl(headers: httpx.Headers) -> int | None:
    """Extract max-age from Cache-Control header if present."""
    cache_control = headers.get("Cache-Control")
    if not cache_control:
        return None
    for part in cache_control.split(","):
        part = part.strip()
        if part.lower().startswith("max-age="):
            value = part.split("=", 1)[1]
            try:
                return max(int(value), 0)
            except ValueError:
                return None
    return None


def get_clerk_jwks(force_refresh: bool = False) -> dict[str, Any]:
    """
    Fetch Clerk's JWKS (JSON Web Key Set) for verifying JWT signatures.

    Clerk uses RS256 algorithm with rotating keys. We need to fetch the
    public keys to verify tokens. Results are cached for a short period.
    """
    global _jwks_cache, _jwks_cache_expiry

    if settings.developer_mode and not settings.developer_verify_clerk_tokens:
        logger.debug("Developer mode enabled; skipping JWKS fetch.")
        return {}

    jwks_url = settings.clerk_jwks_url
    if not jwks_url:
        if settings.environment == "prod" or settings.developer_verify_clerk_tokens:
            logger.error(
                "CLERK_JWKS_URL not configured. Cannot verify Clerk tokens securely."
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service temporarily unavailable",
            )
        logger.warning(
            "CLERK_JWKS_URL not configured; returning empty JWKS (no signature verification)."
        )
        return {}

    now = datetime.now(tz=timezone.utc)

    with _jwks_cache_lock:
        if (
            not force_refresh
            and _jwks_cache is not None
            and _jwks_cache_expiry
            and _jwks_cache_expiry > now
        ):
            return _jwks_cache

        logger.debug("Fetching Clerk JWKS from %s", jwks_url)
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(jwks_url, headers={"Accept": "application/json"})
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            logger.error("Failed to fetch Clerk JWKS: %s", exc)
            if _jwks_cache and not force_refresh:
                logger.warning("Using cached JWKS after fetch failure.")
                return _jwks_cache
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service temporarily unavailable",
            ) from exc
        except Exception as exc:  # noqa: BLE001 - best-effort safety
            logger.exception("Unexpected error fetching Clerk JWKS")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service temporarily unavailable",
            ) from exc

        if not isinstance(payload, dict) or "keys" not in payload:
            logger.error("Clerk JWKS payload missing 'keys' attribute")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service temporarily unavailable",
            )

        ttl_seconds = _extract_cache_ttl(response.headers)
        if not ttl_seconds:
            ttl_seconds = settings.clerk_jwks_cache_ttl_seconds

        _jwks_cache = payload
        _jwks_cache_expiry = now + timedelta(seconds=ttl_seconds)

        logger.debug(
            "Cached Clerk JWKS (%d keys) for %d seconds",
            len(payload.get("keys", [])),
            ttl_seconds,
        )

    return _jwks_cache or {}


def verify_clerk_token(token: str) -> dict:
    """
    Verify and decode a Clerk JWT token.

    Args:
        token: The JWT token from the Authorization header

    Returns:
        Decoded token payload with user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    if settings.developer_mode and not settings.developer_verify_clerk_tokens:
        payload = jwt.decode(
            token, options={"verify_signature": False}, algorithms=["RS256"]
        )
        logger.debug(
            "Developer mode: decoded Clerk token without signature verification",
            extra={"extra_data": {"user_id": payload.get("sub")}},
        )
        return payload

    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        logger.warning("Invalid JWT header: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    kid = header.get("kid")
    if not kid:
        logger.warning("JWT token missing 'kid' header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def _find_key(jwks: dict[str, Any]) -> dict[str, Any] | None:
        for entry in jwks.get("keys", []):
            if entry.get("kid") == kid:
                return entry
        return None

    jwks = get_clerk_jwks()
    if not jwks or not jwks.get("keys"):
        logger.warning(
            "JWKS keyset empty. Decoding Clerk token without verification (environment=%s).",
            settings.environment,
        )
        return jwt.decode(
            token, options={"verify_signature": False}, algorithms=["RS256"]
        )

    key_data = _find_key(jwks)
    if key_data is None:
        jwks = get_clerk_jwks(force_refresh=True)
        key_data = _find_key(jwks)

    if key_data is None:
        logger.warning("No matching JWK found for kid=%s", kid)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        public_key = RSAAlgorithm.from_jwk(json.dumps(key_data))
    except Exception as exc:  # noqa: BLE001 - propagate as auth failure
        logger.warning("Failed to construct RSA key from Clerk JWKS: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        payload = jwt.decode(
            token,
            key=public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        logger.warning("Invalid JWT token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return payload


def _select_email_from_addresses(
    email_addresses: list | None, primary_id: str | None = None
) -> str | None:
    """Pick the best email out of Clerk's email address payload."""
    if not isinstance(email_addresses, list):
        return None

    def extract(entry: dict) -> str | None:
        if not isinstance(entry, dict):
            return None
        return entry.get("email_address") or entry.get("email")

    # Prefer Clerk's primary email id
    if primary_id:
        for entry in email_addresses:
            if isinstance(entry, dict) and entry.get("id") == primary_id:
                email = extract(entry)
                if email:
                    return email

    # Next, try verified emails
    for entry in email_addresses:
        if not isinstance(entry, dict):
            continue
        verified = entry.get("verified")
        verification_status = entry.get("verification", {}).get("status")
        if verified or verification_status == "verified":
            email = extract(entry)
            if email:
                return email

    # Fallback to the first available email_address
    for entry in email_addresses:
        email = extract(entry)
        if email:
            return email

    return None


def _extract_email_from_payload(payload: dict) -> str | None:
    """Extract the user's email address from a Clerk token or API response."""
    if not isinstance(payload, dict):
        return None

    for key in ("email", "email_address", "user_email"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value

    email = _select_email_from_addresses(
        payload.get("email_addresses"), payload.get("primary_email_address_id")
    )
    if email:
        return email

    emails = payload.get("emails")
    if isinstance(emails, list):
        for value in emails:
            if isinstance(value, str) and value:
                return value

    return None


def _fetch_email_from_clerk(clerk_user_id: str) -> str | None:
    """Look up the user's email via Clerk's backend API when the token lacks it."""
    if not settings.clerk_secret_key:
        logger.debug("Cannot fetch Clerk email: clerk_secret_key not configured")
        return None

    url = f"https://api.clerk.com/v1/users/{clerk_user_id}"
    headers = {
        "Authorization": f"Bearer {settings.clerk_secret_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Failed to fetch Clerk user %s: %s",
            clerk_user_id,
            exc.response.text[:200],
        )
        return None
    except Exception as exc:  # noqa: BLE001 - broad to avoid auth failures
        logger.warning("Unexpected Clerk API error for user %s: %s", clerk_user_id, exc)
        return None

    email = _extract_email_from_payload(data)
    if not email:
        email = _select_email_from_addresses(
            data.get("email_addresses"), data.get("primary_email_address_id")
        )

    if not email:
        logger.warning("Clerk API response missing email for user %s", clerk_user_id)

    return email


def get_or_create_user_from_clerk(
    clerk_user_id: str,
    email: str | None,
    name: str | None,
    db: Session,
) -> User:
    """
    Get existing user or create new user from Clerk token data.

    This implements auto-provisioning: when a user signs in for the first time,
    we automatically create their account in our database.

    Args:
        clerk_user_id: Clerk's unique user identifier (from token 'sub')
        email: User's email address (from token)
        name: User's full name (from token)
        db: Database session

    Returns:
        User object (existing or newly created)
    """
    # Try to find existing user by Clerk ID
    user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()

    if user:
        # Update email/name if they've changed
        updated = False
        if email and user.email != email:
            user.email = email
            updated = True
        if name and user.name != name:
            user.name = name
            updated = True

        if updated:
            db.commit()
            db.refresh(user)
            logger.info(f"Updated user {user.id} from Clerk data")

        return user

    # Create new user
    user = User(
        clerk_user_id=clerk_user_id,
        email=email or f"{clerk_user_id}@clerk.user",  # Fallback email
        name=name or "Unknown User",
        auto_approve_sessions=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(
        "Created new user from Clerk",
        extra={
            "extra_data": {
                "user_id": user.id,
                "clerk_user_id": clerk_user_id,
                "email": email,
            }
        },
    )

    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_session),
) -> User:
    """
    FastAPI dependency to get the current authenticated user.

    This extracts the JWT token from the Authorization header, verifies it,
    and returns the corresponding User object from the database.

    Usage in routes:
        @router.get("/protected")
        def protected_route(current_user: User = Depends(get_current_user)):
            return {"message": f"Hello {current_user.name}"}

    Args:
        credentials: HTTP Bearer token from Authorization header
        db: Database session

    Returns:
        Authenticated User object

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials

    # Verify and decode the JWT
    payload = verify_clerk_token(token)

    # Extract user information from token
    clerk_user_id = payload.get("sub")
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID",
        )

    # Get user metadata from token
    email = _extract_email_from_payload(payload)
    if not email:
        email = _fetch_email_from_clerk(clerk_user_id)
        if email:
            logger.debug("Resolved Clerk email via API for user %s", clerk_user_id)
        else:
            logger.warning(
                "Falling back to synthetic clerk email for user %s; token missing email",
                clerk_user_id,
            )
    name = payload.get("name") or payload.get("full_name")

    # Get or create user in our database
    user = get_or_create_user_from_clerk(
        clerk_user_id=clerk_user_id,
        email=email,
        name=name,
        db=db,
    )

    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_session),
) -> User | None:
    """
    Optional authentication - returns User if authenticated, None otherwise.

    Use this for routes that work both with and without authentication,
    but might behave differently.

    Args:
        credentials: Optional HTTP Bearer token
        db: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
