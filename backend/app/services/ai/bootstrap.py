"""
AI model bootstrap utilities
"""
from app.services.ai.models.nima import NIMAAnalyzer
from app.services.ai.models.qwen_vl import QwenVLAnalyzer
from app.services.ai.registry import AIModelRegistry


async def register_builtin_models() -> None:
    """Register built-in AI models with the registry."""
    if await AIModelRegistry.get_model("nima") is None:
        await AIModelRegistry.register(NIMAAnalyzer())
    if await AIModelRegistry.get_model("qwen3-vl") is None:
        await AIModelRegistry.register(QwenVLAnalyzer())
