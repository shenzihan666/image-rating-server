"""
Dependency injection for API endpoints
"""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.database import get_db
from app.core.security import verify_token

# Re-export get_db for use in endpoints
__all__ = ["get_db", "get_current_user", "get_optional_user", "require_active_user", "CurrentUser", "OptionalUser", "ActiveUser"]

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> dict:
    """
    Get the current authenticated user from the JWT token.

    Args:
        credentials: HTTP Authorization credentials containing the JWT token

    Returns:
        User data extracted from the token

    Raises:
        HTTPException: If token is invalid or missing
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = verify_token(token, token_type="access")

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user information from token
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "user_id": user_id,
        "email": payload.get("email"),
        "is_active": payload.get("is_active", True),
    }


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> dict | None:
    """
    Get the current user if authenticated, otherwise return None.

    This is useful for endpoints that work both with and without authentication.

    Args:
        credentials: HTTP Authorization credentials containing the JWT token

    Returns:
        User data if token is valid, None otherwise
    """
    if credentials is None:
        return None

    token = credentials.credentials
    payload = verify_token(token, token_type="access")

    if payload is None:
        return None

    user_id: str | None = payload.get("sub")
    if user_id is None:
        return None

    return {
        "user_id": user_id,
        "email": payload.get("email"),
        "is_active": payload.get("is_active", True),
    }


async def require_active_user(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """
    Require the current user to be active.

    Args:
        current_user: Current user from get_current_user dependency

    Returns:
        User data if active

    Raises:
        HTTPException: If user is not active
    """
    if not current_user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return current_user


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[dict, Depends(get_current_user)]
OptionalUser = Annotated[dict | None, Depends(get_optional_user)]
ActiveUser = Annotated[dict, Depends(require_active_user)]
