"""
Authentication endpoints - Login, logout, token refresh with database
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import CurrentUser, get_db
from app.core.database import AsyncSession
from app.schemas.token import TokenResponse
from app.schemas.user import UserResponse
from app.services.auth import AuthService

router = APIRouter()
auth_service = AuthService  # Will be initialized with db in endpoints


# Request/Response Schemas
class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr
    password: str = Field(..., min_length=6)


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""

    refresh_token: str


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    request: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Authenticate user and return access/refresh tokens.

    Args:
        request: Login credentials
        db: Database session

    Returns:
        TokenResponse with access_token, refresh_token, and expiration

    Raises:
        HTTPException: If credentials are invalid
    """
    service = AuthService(db)

    # Authenticate user
    user = await service.authenticate(request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Create tokens
    return await service.create_tokens(user)


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Refresh an access token using a refresh token.

    Args:
        request: Refresh token
        db: Database session

    Returns:
        TokenResponse with new access_token and refresh_token

    Raises:
        HTTPException: If refresh token is invalid
    """
    from app.core.security import verify_token

    payload = verify_token(request.refresh_token, token_type="refresh")

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload",
        )

    # Fetch user from database
    service = AuthService(db)
    user = await service.get_user_by_id(user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new tokens
    return await service.create_tokens(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: CurrentUser) -> None:
    """
    Logout the current user.

    In a JWT-based system, the client simply discards the token.
    For additional security, you could implement token blacklisting.

    Args:
        current_user: Current authenticated user
    """
    # TODO: Implement token blacklisting if needed
    # For now, this is a stateless operation
    pass


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user_profile(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Get the current authenticated user's profile.

    Args:
        current_user: Current authenticated user from access token
        db: Database session

    Returns:
        UserResponse with the authenticated user's data
    """
    service = AuthService(db)
    user = await service.get_user_by_id(current_user["user_id"])

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )
