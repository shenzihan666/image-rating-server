"""
Abstract base class for AI analyzers
"""
from abc import ABC, abstractmethod


class BaseAIAnalyzer(ABC):
    """Abstract base class for AI image analysis models."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the model."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the model."""
        pass

    @abstractmethod
    async def load(self) -> bool:
        """
        Load the model into memory.

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def unload(self) -> bool:
        """
        Unload the model from memory.

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        """
        Check if the model is currently loaded.

        Returns:
            True if loaded, False otherwise
        """
        pass

    @abstractmethod
    async def analyze(self, image_path: str) -> dict:
        """
        Analyze an image and return results.

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary containing analysis results
        """
        pass
