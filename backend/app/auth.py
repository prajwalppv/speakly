"""
Authentication and authorization utilities for Clerk JWT tokens.

This module handles:
- JWT token verification from Clerk
- User extraction from tokens
- User provisioning on first login
- FastAPI dependency for authenticated routes
"""
from typing import Optional
import logging

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import get_session
from .models import User

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()

# Cache for Clerk JWKS (public keys)
_jwks_cache: Optional[dict] = None


async def get_clerk_jwks() -> dict:
    """
    Fetch Clerk's JWKS (JSON Web Key Set) for verifying JWT signatures.
    
    Clerk uses RS256 algorithm with rotating keys. We need to fetch the
    public keys to verify tokens.
    
    Caches the result to avoid repeated requests.
    """
    global _jwks_cache
    
    if _jwks_cache is not None:
        return _jwks_cache
    
    # In development mode, we skip JWKS verification for easier testing
    # In production, you should fetch Clerk's JWKS from their well-known endpoint
    try:
        # Check if we're in development mode (using test secret key)
        if settings.clerk_secret_key and settings.clerk_secret_key.startswith("sk_test_"):
            # Development: skip JWKS verification
            logger.warning("Development mode: JWT signature verification disabled")
            _jwks_cache = {}
            return _jwks_cache
        
        # Production: Fetch Clerk JWKS (not implemented yet)
        logger.warning("Production JWKS verification not implemented - using unverified tokens")
        _jwks_cache = {}
        return _jwks_cache
    except Exception as e:
        logger.error(f"Failed to fetch Clerk JWKS: {e}")
        # In development, allow tokens without verification
        _jwks_cache = {}
        return _jwks_cache


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
    try:
        # In development mode, we decode without verification
        # In production, you'd verify against Clerk's JWKS
        if settings.clerk_secret_key and settings.clerk_secret_key.startswith("sk_test_"):
            # Development: decode without verification
            payload = jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=["RS256"]
            )
            logger.debug(f"Decoded JWT token (dev mode): user_id={payload.get('sub')}")
            return payload
        else:
            # Production: verify signature with Clerk's public key
            # This requires fetching JWKS and matching the key
            # For now, we'll use the same approach but log a warning
            logger.warning("Production mode but using unverified JWT - implement JWKS verification!")
            payload = jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=["RS256"]
            )
            return payload
            
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _select_email_from_addresses(
    email_addresses: Optional[list], primary_id: Optional[str] = None
) -> Optional[str]:
    """Pick the best email out of Clerk's email address payload."""
    if not isinstance(email_addresses, list):
        return None

    def extract(entry: dict) -> Optional[str]:
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


def _extract_email_from_payload(payload: dict) -> Optional[str]:
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


def _fetch_email_from_clerk(clerk_user_id: str) -> Optional[str]:
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
    email: Optional[str],
    name: Optional[str],
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
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(
        f"Created new user from Clerk",
        extra={"extra_data": {"user_id": user.id, "clerk_user_id": clerk_user_id, "email": email}}
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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_session),
) -> Optional[User]:
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
