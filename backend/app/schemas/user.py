"""
User schemas for request/response validation
"""

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=1, max_length=100, description="User full name")


class UserCreate(UserBase):
    """User creation schema."""

    password: str = Field(..., min_length=6, max_length=100, description="User password")


class UserUpdate(BaseModel):
    """User update schema."""

    full_name: str | None = Field(None, min_length=1, max_length=100)
    email: EmailStr | None = None


class UserResponse(BaseModel):
    """User response schema."""

    user_id: str = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    is_active: bool = Field(True, description="Whether user is active")
    created_at: str | None = Field(None, description="Account creation timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True
        populate_by_name = True
