"""
Pydantic schemas for AI analyze API
"""
from typing import Any, Literal

from pydantic import BaseModel, Field


class AIModelConfigField(BaseModel):
    """Schema for a model configuration field."""

    key: str = Field(..., description="Unique config field key")
    label: str = Field(..., description="Human-readable field label")
    field_type: Literal["text", "password", "url"] = Field(
        "text",
        description="Input control type",
    )
    required: bool = Field(False, description="Whether the field is required")
    secret: bool = Field(False, description="Whether the field contains sensitive data")
    placeholder: str | None = Field(None, description="Suggested placeholder")
    help_text: str | None = Field(None, description="Additional field helper text")


class AIModelInfo(BaseModel):
    """Schema for AI model information."""

    name: str = Field(..., description="Unique model identifier")
    description: str = Field(..., description="Human-readable model description")
    is_active: bool = Field(..., description="Whether this model is currently active")
    is_loaded: bool = Field(..., description="Whether this model is loaded in memory")
    configurable: bool = Field(..., description="Whether the model exposes runtime config")
    configured: bool = Field(..., description="Whether the model has required config")


class AIModelDetail(AIModelInfo):
    """Schema for detailed AI model information."""

    config_fields: list[AIModelConfigField] = Field(
        default_factory=list,
        description="Config field metadata for this model",
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Public model configuration values",
    )
    configured_secret_fields: list[str] = Field(
        default_factory=list,
        description="Secret fields that already have persisted values",
    )


class AIModelConnectionTestResponse(BaseModel):
    """Connection test result for a model."""

    ok: bool = Field(..., description="Whether the connection test succeeded")
    status: str = Field(..., description="Machine-readable connection test status")
    message: str = Field(..., description="Human-readable test result")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional structured details from the test run",
    )


class SetActiveModelRequest(BaseModel):
    """Request schema for setting the active model."""

    model_name: str = Field(..., description="Name of the model to activate")


class AnalysisResult(BaseModel):
    """Schema for image analysis result."""

    model: str = Field(..., description="Name of the model used")
    score: float | None = Field(None, description="Overall score if applicable")
    details: dict = Field(default_factory=dict, description="Detailed analysis results")


class UpdateAIModelConfigRequest(BaseModel):
    """Request schema for updating persisted model configuration."""

    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Model-specific configuration values",
    )


class AIPromptVersionSummary(BaseModel):
    """Prompt version summary."""

    id: str
    prompt_id: str
    version_number: int
    commit_message: str | None = None
    created_by: str | None = None
    created_at: str


class AIPromptVersionDetail(AIPromptVersionSummary):
    """Full prompt version payload."""

    system_prompt: str
    user_prompt: str


class AIPromptSummary(BaseModel):
    """Prompt summary for list pages."""

    id: str
    model_name: str
    name: str
    description: str | None = None
    is_active: bool
    current_version_id: str | None = None
    current_version_number: int | None = None
    created_at: str
    updated_at: str


class AIPromptDetail(AIPromptSummary):
    """Prompt detail including current version."""

    current_version: AIPromptVersionDetail | None = None


class CreateAIPromptRequest(BaseModel):
    """Create prompt with an initial version."""

    model_name: str = Field(..., description="Target model identifier")
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    is_active: bool = True
    system_prompt: str = Field(..., min_length=1)
    user_prompt: str = Field(..., min_length=1)
    commit_message: str | None = None
    created_by: str | None = None


class UpdateAIPromptRequest(BaseModel):
    """Update prompt metadata."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    is_active: bool | None = None


class CreateAIPromptVersionRequest(BaseModel):
    """Create a new prompt version."""

    system_prompt: str = Field(..., min_length=1)
    user_prompt: str = Field(..., min_length=1)
    commit_message: str | None = None
    created_by: str | None = None
