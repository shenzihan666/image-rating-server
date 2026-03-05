"""
Upload-related Pydantic schemas
"""
from enum import StrEnum

from pydantic import BaseModel, Field


class UploadStatus(StrEnum):
    """Upload status enum."""

    SUCCESS = "success"
    DUPLICATED = "duplicated"
    FAILED = "failed"


class ImageMetadata(BaseModel):
    """Image metadata schema."""

    image_id: str = Field(..., description="Unique image ID (UUID)")
    file_name: str = Field(..., description="Original file name")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    width: int | None = Field(None, description="Image width in pixels")
    height: int | None = Field(None, description="Image height in pixels")
    file_path: str = Field(..., description="Relative file path (YYYY/MM/DD/uuid.ext)")
    hash_sha256: str = Field(..., description="SHA256 hash of the file")


class UploadResult(BaseModel):
    """Single file upload result."""

    status: UploadStatus = Field(..., description="Upload status")
    original_filename: str = Field(..., description="Original filename")
    metadata: ImageMetadata | None = Field(default=None, description="Image metadata (if success)")
    error_message: str | None = Field(default=None, description="Error message (if failed)")
    is_duplicate: bool = Field(default=False, description="Whether this is a duplicate upload")


class UploadResponse(BaseModel):
    """Batch upload response."""

    success: bool = Field(..., description="Overall success status")
    total: int = Field(..., description="Total number of files")
    succeeded: int = Field(0, description="Number of successful uploads")
    duplicated: int = Field(0, description="Number of duplicated files")
    failed: int = Field(0, description="Number of failed uploads")
    results: list[UploadResult] = Field(default_factory=list, description="Individual results")
    message: str = Field(..., description="Summary message")
