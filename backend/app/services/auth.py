"""
Authentication service - Business logic for user authentication with database
"""
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.token import TokenResponse
from app.schemas.user import UserCreate, UserResponse


class AuthService:
    """Service for handling authentication operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize auth service with database session."""
        self.db = db

    async def register(self, user_data: UserCreate) -> UserResponse:
        """
        Register a new user.

        Args:
            user_data: User creation data

        Returns:
            Created user response

        Raises:
            ValueError: If email already exists
        """
        # Check if user exists
        result = await self.db.execute(
            select(User).where(User.email == user_data.email)
        )
        if result.scalar_one_or_none():
            raise ValueError("Email already registered")

        # Create new user
        hashed_pw = hash_password(user_data.password)
        new_user = User(
            id=str(uuid4()),
            email=user_data.email,
            hashed_password=hashed_pw,
            full_name=user_data.full_name,
        )

        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)

        return UserResponse(
            user_id=new_user.id,
            email=new_user.email,
            full_name=new_user.full_name,
            is_active=new_user.is_active,
            created_at=new_user.created_at.isoformat() if new_user.created_at else None,
        )

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate user with email and password.

        Args:
            email: User email
            password: Plain text password

        Returns:
            User if authenticated, None otherwise
        """
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if user and verify_password(password, user.hashed_password):
            return user

        return None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User if found, None otherwise
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_tokens(self, user: User) -> TokenResponse:
        """
        Create access and refresh tokens for user.

        Args:
            user: User object

        Returns:
            Token response with access and refresh tokens
        """
        user_data = {
            "sub": str(user.id),
            "email": user.email,
            "is_active": user.is_active,
        }

        access_token = create_access_token(data=user_data)
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=30 * 60,  # 30 minutes
        )
