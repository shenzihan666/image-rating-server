"""
Batch operation schemas for request/response validation
"""

from pydantic import BaseModel, Field

from app.schemas.analyze import ImageAnalyzeResponse


class BatchAnalyzeRequest(BaseModel):
    """Request schema for batch image analysis."""

    image_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of image IDs to analyze (max 50)"
    )
    force_new: bool = Field(
        False,
        description="Re-analyze even if cached result exists"
    )


class BatchAnalyzeResponse(BaseModel):
    """Response schema for batch image analysis results."""

    success: bool = Field(..., description="Overall success status")
    total: int = Field(..., description="Total number of images to analyze")
    succeeded: int = Field(..., description="Number of successful analyses")
    failed: int = Field(..., description="Number of failed analyses")
    results: list[ImageAnalyzeResponse] = Field(
        default_factory=list,
        description="List of analysis results"
    )
    message: str = Field(..., description="Summary message")


class BatchDeleteRequest(BaseModel):
    """Request schema for batch image deletion."""

    image_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of image IDs to delete (max 50)"
    )


class BatchDeleteResponse(BaseModel):
    """Response schema for batch image deletion results."""

    success: bool = Field(..., description="Overall success status")
    total: int = Field(..., description="Total number of images to delete")
    deleted: int = Field(..., description="Number of successfully deleted images")
    failed: int = Field(..., description="Number of failed deletions")
    errors: list[str] = Field(
        default_factory=list,
        description="List of error messages for failed deletions"
    )
    message: str = Field(..., description="Summary message")
