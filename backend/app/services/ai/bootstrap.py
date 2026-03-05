"""
AI model bootstrap utilities
"""
from app.services.ai.models.nima import NIMAAnalyzer
from app.services.ai.registry import AIModelRegistry


async def register_builtin_models() -> None:
    """Register built-in AI models with the registry."""
    if await AIModelRegistry.get_model("nima") is None:
        await AIModelRegistry.register(NIMAAnalyzer())
