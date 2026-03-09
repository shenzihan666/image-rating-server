"""
AI Analysis Services - Modular AI model management
"""
from app.services.ai.base import AIModelConfigFieldDef, BaseAIAnalyzer
from app.services.ai.registry import AIModelRegistry
from app.services.ai.schemas import (
    AIPromptDetail,
    AIPromptSummary,
    AIPromptVersionDetail,
    AIPromptVersionSummary,
    AIModelConfigField,
    AIModelDetail,
    AIModelInfo,
    CreateAIPromptRequest,
    CreateAIPromptVersionRequest,
    SetActiveModelRequest,
    UpdateAIPromptRequest,
    UpdateAIModelConfigRequest,
)

__all__ = [
    "AIPromptDetail",
    "AIPromptSummary",
    "AIPromptVersionDetail",
    "AIPromptVersionSummary",
    "AIModelConfigField",
    "AIModelConfigFieldDef",
    "AIModelDetail",
    "BaseAIAnalyzer",
    "AIModelRegistry",
    "AIModelInfo",
    "CreateAIPromptRequest",
    "CreateAIPromptVersionRequest",
    "SetActiveModelRequest",
    "UpdateAIPromptRequest",
    "UpdateAIModelConfigRequest",
]
