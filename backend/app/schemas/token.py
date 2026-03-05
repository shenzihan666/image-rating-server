"""
Token schemas for authentication
"""
from pydantic import BaseModel, Field


class TokenPayload(BaseModel):
    """JWT token payload schema."""

    sub: str = Field(..., description="Subject (user ID)")
    exp: int = Field(..., description="Expiration time (unix timestamp)")
    type: str = Field(..., description="Token type (access/refresh)")
    email: str | None = Field(None, description="User email")
    is_active: bool = Field(True, description="Whether user is active")


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")
