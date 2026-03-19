"""
Image schemas for request/response validation
"""

from pydantic import BaseModel, ConfigDict, Field


class ImageBase(BaseModel):
    """Base image schema."""

    title: str = Field(..., min_length=1, max_length=255, description="Image title")
    description: str | None = Field(None, description="Image description")


class ImageCreate(ImageBase):
    """Image creation schema - used internally during upload."""

    file_path: str = Field(..., description="Relative file path")
    file_size: int = Field(..., description="File size in bytes")
    width: int | None = Field(None, description="Image width in pixels")
    height: int | None = Field(None, description="Image height in pixels")
    mime_type: str = Field(..., description="MIME type")
    hash_sha256: str = Field(..., min_length=64, max_length=64, description="SHA256 hash")


class ImageUpdate(BaseModel):
    """Image update schema."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class ImageResponse(BaseModel):
    """Image response schema."""

    id: str = Field(..., description="Image ID")
    title: str = Field(..., description="Image title")
    description: str | None = Field(None, description="Image description")
    file_path: str = Field(..., description="Relative file path")
    file_size: int = Field(..., description="File size in bytes")
    width: int | None = Field(None, description="Image width in pixels")
    height: int | None = Field(None, description="Image height in pixels")
    mime_type: str = Field(..., description="MIME type")
    hash_sha256: str = Field(..., description="SHA256 hash")
    average_rating: float = Field(..., description="Average rating score")
    rating_count: int = Field(..., description="Number of ratings")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    ai_score: float | None = Field(None, description="Latest AI analysis score")
    ai_model: str | None = Field(None, description="AI model used for analysis")
    ai_analyzed_at: str | None = Field(None, description="Analysis timestamp")
    ai_decision: str | None = Field(None, description="AI decision: 合格 or 不合格")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ImageListResponse(BaseModel):
    """Paginated image list response schema."""

    items: list[ImageResponse]
    total: int = Field(..., description="Total number of images")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
