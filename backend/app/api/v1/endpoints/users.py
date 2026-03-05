"""
User management endpoints with database
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import ActiveUser, CurrentUser, get_db
from app.core.database import AsyncSession
from app.core.security import hash_password, verify_password
from app.schemas.user import UserResponse, UserUpdate
from app.services.user import UserService

router = APIRouter()


# Request/Response Schemas
class UserResponseSchema(BaseModel):
    """User response schema."""

    user_id: str
    email: str
    full_name: str
    is_active: bool
    created_at: str | None = None


class UserUpdateRequest(BaseModel):
    """User update request schema."""

    full_name: str | None = Field(None, min_length=1, max_length=100)
    email: EmailStr | None = None


class PasswordChangeRequest(BaseModel):
    """Password change request schema."""

    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6, max_length=100)


class UserListResponse(BaseModel):
    """User list response schema."""

    users: list[UserResponseSchema]
    total: int
    page: int
    page_size: int


@router.get("/me", response_model=UserResponse)
async def get_user_profile(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Get the current user's profile.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        UserResponse with current user data
    """
    user_service = UserService(db)
    user = await user_service.get_by_id(current_user["user_id"])

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


@router.patch("/me", response_model=UserResponse)
async def update_user_profile(
    request: UserUpdateRequest,
    current_user: ActiveUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Update the current user's profile.

    Args:
        request: Update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        UserResponse with updated user data
    """
    user_service = UserService(db)

    # Convert request to UserUpdate schema
    update_data = UserUpdate(
        full_name=request.full_name,
        email=request.email,
    )

    result = await user_service.update(current_user["user_id"], update_data)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return result


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: PasswordChangeRequest,
    current_user: ActiveUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Change the current user's password.

    Args:
        request: Password change data
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: If old password is incorrect
    """
    from sqlalchemy import select

    from app.models.user import User

    # Get user with password
    result = await db.execute(
        select(User).where(User.id == current_user["user_id"])
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Verify old password
    if not verify_password(request.old_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password",
        )

    if request.old_password == request.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from old password",
        )

    # Update password
    user.hashed_password = hash_password(request.new_password)
    await db.commit()


@router.get("/", response_model=UserListResponse)
async def list_users(
    current_user: ActiveUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> UserListResponse:
    """
    List all users (admin only).

    Args:
        current_user: Current authenticated user (must be admin)
        db: Database session
        page: Page number
        page_size: Items per page

    Returns:
        UserListResponse with paginated user list
    """
    # TODO: Check if user is admin
    from sqlalchemy import func, select

    from app.models.user import User

    # Get total count
    count_result = await db.execute(select(func.count()).select_from(User))
    total = count_result.scalar()

    # Get paginated users
    result = await db.execute(
        select(User)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    users = result.scalars().all()

    return UserListResponse(
        users=[
            UserResponseSchema(
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                created_at=user.created_at.isoformat() if user.created_at else None,
            )
            for user in users
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: ActiveUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Get a specific user by ID.

    Args:
        user_id: User ID to fetch
        current_user: Current authenticated user
        db: Database session

    Returns:
        UserResponse with requested user data

    Raises:
        HTTPException: If user not found
    """
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)

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
