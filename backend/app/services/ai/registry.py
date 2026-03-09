"""
AI Model Registry - Manages available models and active model state
"""

import asyncio

from loguru import logger

from app.services.ai.base import BaseAIAnalyzer


class AIModelRegistry:
    """Registry for managing AI models with single active model support."""

    _models: dict[str, BaseAIAnalyzer] = {}
    _active_model: str | None = None
    _lock: asyncio.Lock = asyncio.Lock()

    @classmethod
    async def register(cls, model: BaseAIAnalyzer) -> None:
        """
        Register a new AI model.

        Args:
            model: AI model instance to register
        """
        async with cls._lock:
            cls._models[model.name] = model
        logger.info(f"Registered AI model: {model.name}")

    @classmethod
    async def unregister(cls, name: str) -> bool:
        """
        Unregister an AI model.

        Args:
            name: Name of the model to unregister

        Returns:
            True if model was unregistered, False if not found
        """
        async with cls._lock:
            if name in cls._models:
                if cls._active_model == name:
                    await cls._models[name].unload()
                    cls._active_model = None
                del cls._models[name]
                logger.info(f"Unregistered AI model: {name}")
                return True
            return False

    @classmethod
    async def set_active(cls, name: str, force_reload: bool = False) -> bool:
        """
        Set the active model. Only one model can be active at a time.

        Args:
            name: Name of the model to activate
            force_reload: Whether to unload and reload the model even if already active

        Returns:
            True if activation was successful, False otherwise
        """
        async with cls._lock:
            if name not in cls._models:
                logger.warning(f"Model not found: {name}")
                return False

            previous_active = cls._active_model

            # Unload current active model if exists
            if previous_active and previous_active != name:
                logger.info(f"Unloading current active model: {previous_active}")
                await cls._models[previous_active].unload()
                cls._active_model = None

            # Load and set new active model
            model = cls._models[name]
            if force_reload and model.is_loaded():
                logger.info(f"Force reloading model: {name}")
                await model.unload()
                cls._active_model = None

            if cls._active_model == name and model.is_loaded() and not force_reload:
                logger.info(f"Model already active: {name}")
                return True

            if cls._active_model == name and not model.is_loaded():
                cls._active_model = None

            if await model.load():
                cls._active_model = name
                logger.info(f"Activated AI model: {name}")
                return True

            logger.error(f"Failed to load model: {name}")
            return False

    @classmethod
    async def deactivate(cls) -> bool:
        """
        Deactivate the current active model.

        Returns:
            True if deactivation was successful
        """
        async with cls._lock:
            if cls._active_model:
                await cls._models[cls._active_model].unload()
                logger.info(f"Deactivated model: {cls._active_model}")
                cls._active_model = None
        return True

    @classmethod
    async def get_active(cls) -> BaseAIAnalyzer | None:
        """
        Get the currently active model.

        Returns:
            Active model instance or None
        """
        async with cls._lock:
            if cls._active_model:
                return cls._models.get(cls._active_model)
            return None

    @classmethod
    async def get_active_name(cls) -> str | None:
        """
        Get the name of the currently active model.

        Returns:
            Active model name or None
        """
        async with cls._lock:
            return cls._active_model

    @classmethod
    async def list_models(cls) -> list[dict]:
        """
        List all registered models with their status.

        Returns:
            List of model information dictionaries
        """
        async with cls._lock:
            return [
                {
                    "name": model.name,
                    "description": model.description,
                    "is_active": model.name == cls._active_model,
                    "is_loaded": model.is_loaded(),
                }
                for model in cls._models.values()
            ]

    @classmethod
    async def get_model(cls, name: str) -> BaseAIAnalyzer | None:
        """
        Get a specific model by name.

        Args:
            name: Model name

        Returns:
            Model instance or None if not found
        """
        async with cls._lock:
            return cls._models.get(name)
