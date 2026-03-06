"""
Image analysis request and response schemas
"""

from pydantic import BaseModel, Field


class ImageAnalyzeRequest(BaseModel):
    """Request schema for image analysis."""

    force_new: bool = Field(
        False,
        description="If true, re-analyze even if a cached result exists"
    )


class ImageAnalyzeResponse(BaseModel):
    """Response schema for image analysis results."""

    image_id: str = Field(..., description="ID of the analyzed image")
    model: str = Field(..., description="Name of the AI model used")
    score: float | None = Field(None, description="Quality score (1-10 for NIMA)")
    details: dict = Field(default_factory=dict, description="Detailed analysis results")
    created_at: str = Field(..., description="Analysis timestamp")
