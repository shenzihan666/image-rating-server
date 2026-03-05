"""
Pydantic schemas for AI analyze API
"""

from pydantic import BaseModel, Field


class AIModelInfo(BaseModel):
    """Schema for AI model information."""

    name: str = Field(..., description="Unique model identifier")
    description: str = Field(..., description="Human-readable model description")
    is_active: bool = Field(..., description="Whether this model is currently active")
    is_loaded: bool = Field(..., description="Whether this model is loaded in memory")


class SetActiveModelRequest(BaseModel):
    """Request schema for setting the active model."""

    model_name: str = Field(..., description="Name of the model to activate")


class AnalysisResult(BaseModel):
    """Schema for image analysis result."""

    model: str = Field(..., description="Name of the model used")
    score: float | None = Field(None, description="Overall score if applicable")
    details: dict = Field(default_factory=dict, description="Detailed analysis results")
