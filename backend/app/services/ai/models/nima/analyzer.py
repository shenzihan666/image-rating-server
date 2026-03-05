"""
NIMA Analyzer implementation
"""
import asyncio
from pathlib import Path
from typing import Any

import torch
from loguru import logger
from PIL import Image
from torchvision import transforms

from app.services.ai.base import BaseAIAnalyzer
from app.services.ai.models.nima.model import NIMA


def _sync_load_weights(model_path: Path, device: torch.device) -> dict | None:
    """
    Synchronously load model weights from disk.

    This is a blocking operation and should be run in a thread pool.

    Args:
        model_path: Path to the model weights file
        device: Target device for loading

    Returns:
        State dict or None if loading fails
    """
    return torch.load(model_path, map_location=device, weights_only=False)


class NIMAAnalyzer(BaseAIAnalyzer):
    """NIMA (Neural Image Assessment) analyzer implementation."""

    def __init__(self, model_path: str | None = None) -> None:
        """
        Initialize NIMA analyzer.

        Args:
            model_path: Path to the pretrained model weights
        """
        self._model_path = model_path or self._get_default_model_path()
        self._model: NIMA | None = None
        self._device: torch.device | None = None
        self._transform: transforms.Compose | None = None
        self._loaded = False

    @property
    def name(self) -> str:
        """Model name."""
        return "nima"

    @property
    def description(self) -> str:
        """Model description."""
        return "Neural Image Assessment - Evaluates image aesthetic quality"

    def _get_default_model_path(self) -> str:
        """Get the default model path."""
        return str(Path(__file__).parent / "squeeze-0.218914.pkl")

    def _setup_transform(self) -> transforms.Compose:
        """Setup image transformation pipeline."""
        return transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
        ])

    async def load(self) -> bool:
        """
        Load the NIMA model into memory.

        Returns:
            True if successful, False otherwise
        """
        try:
            if self._loaded:
                logger.info("NIMA model already loaded")
                return True

            logger.info("Loading NIMA model...")

            # Set device
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            logger.info(f"Using device: {self._device}")

            # Initialize model
            self._model = NIMA(num_classes=5, backbone="squeeze")

            # Load weights (async to avoid blocking event loop)
            model_path = Path(self._model_path)
            if model_path.exists():
                # torch.load is a blocking I/O operation, run in thread pool
                state_dict = await asyncio.to_thread(
                    _sync_load_weights, model_path, self._device
                )
                if state_dict is not None:
                    if hasattr(state_dict, "state_dict"):
                        state_dict = state_dict.state_dict()
                    elif isinstance(state_dict, dict) and "state_dict" in state_dict:
                        state_dict = state_dict["state_dict"]
                    self._model.load_state_dict(state_dict)
                    logger.info(f"Loaded weights from: {model_path}")
            else:
                logger.warning(f"Model weights not found at: {model_path}")

            self._model.to(self._device)
            self._model.eval()

            # Setup transforms
            self._transform = self._setup_transform()

            self._loaded = True
            logger.info("NIMA model loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load NIMA model: {e}")
            self._loaded = False
            return False

    async def unload(self) -> bool:
        """
        Unload the NIMA model from memory.

        Returns:
            True if successful
        """
        try:
            if self._model is not None:
                del self._model
                self._model = None

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            self._loaded = False
            logger.info("NIMA model unloaded")
            return True

        except Exception as e:
            logger.error(f"Error unloading NIMA model: {e}")
            return False

    def is_loaded(self) -> bool:
        """Check if the model is loaded."""
        return self._loaded

    def _preprocess_image(self, image_path: str) -> torch.Tensor | None:
        """
        Preprocess image for model input.

        Args:
            image_path: Path to the image file

        Returns:
            Preprocessed tensor or None if failed
        """
        try:
            # Load image
            img = Image.open(image_path).convert("RGB")

            # Apply transforms
            if self._transform is None:
                self._transform = self._setup_transform()

            tensor = self._transform(img)

            # Add batch dimension
            tensor = tensor.unsqueeze(0)

            return tensor

        except Exception as e:
            logger.error(f"Error preprocessing image {image_path}: {e}")
            return None

    async def analyze(self, image_path: str) -> dict[str, Any]:
        """
        Analyze an image and return aesthetic quality score.

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary containing:
                - score: Mean aesthetic score (1-10)
                - distribution: Probability distribution over scores
                - histogram: Score histogram (optional)
        """
        if not self._loaded or self._model is None or self._device is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        # Preprocess image
        tensor = self._preprocess_image(image_path)
        if tensor is None:
            raise ValueError(f"Failed to preprocess image: {image_path}")

        # Run inference
        with torch.no_grad():
            tensor = tensor.to(self._device)
            probs = self._model(tensor)
            mean_score = self._model.predict_score(tensor)

        # Convert to numpy for output
        probs_np = probs.cpu().numpy()[0]
        score = mean_score.cpu().numpy()[0]

        # Build distribution dict based on model class count.
        class_count = self._model.num_classes
        distribution = {i + 1: float(probs_np[i]) for i in range(class_count)}

        return {
            "score": round(float(score), 4),
            "distribution": distribution,
            "min_score": 1.0,
            "max_score": float(class_count),
        }

    def analyze_sync(self, image_path: str) -> dict[str, Any]:
        """
        Synchronous version of analyze for convenience.

        Args:
            image_path: Path to the image file

        Returns:
            Analysis results dictionary
        """
        import asyncio
        return asyncio.run(self.analyze(image_path))
