"""
Abstract base class for AI analyzers
"""
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AIModelConfigFieldDef:
    """Configuration field metadata exposed to the API/UI layer."""

    key: str
    label: str
    field_type: str = "text"
    required: bool = False
    secret: bool = False
    placeholder: str | None = None
    help_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the field definition to a plain dictionary."""
        return asdict(self)


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

    @property
    def config_fields(self) -> tuple[AIModelConfigFieldDef, ...]:
        """Optional model configuration fields."""
        return ()

    @property
    def supports_configuration(self) -> bool:
        """Whether the model exposes runtime configuration."""
        return bool(self.config_fields)

    def prepare_configuration(self, config: dict[str, Any] | None) -> dict[str, Any]:
        """Normalize configuration before validation or API exposure."""
        return dict(config or {})

    def get_missing_required_fields(self, config: dict[str, Any] | None) -> list[str]:
        """Return required config keys that are not populated."""
        prepared = self.prepare_configuration(config)
        missing: list[str] = []
        for field in self.config_fields:
            if not field.required:
                continue

            value = prepared.get(field.key)
            if value is None:
                missing.append(field.key)
                continue

            if isinstance(value, str) and not value.strip():
                missing.append(field.key)

        return missing

    def is_configured(self, config: dict[str, Any] | None) -> bool:
        """Check whether all required configuration is present."""
        return not self.get_missing_required_fields(config)

    def get_public_config(self, config: dict[str, Any] | None) -> dict[str, Any]:
        """Return a frontend-safe view of model configuration."""
        prepared = self.prepare_configuration(config)
        public_config: dict[str, Any] = {}
        for field in self.config_fields:
            value = prepared.get(field.key, "")
            public_config[field.key] = "" if field.secret and value else value
        return public_config

    def get_configured_secret_fields(self, config: dict[str, Any] | None) -> list[str]:
        """List secret fields that already have persisted values."""
        prepared = self.prepare_configuration(config)
        return [
            field.key
            for field in self.config_fields
            if field.secret and prepared.get(field.key)
        ]

    def merge_configuration(
        self,
        current: dict[str, Any] | None,
        updates: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Merge persisted config with user updates."""
        merged = dict(current or {})
        update_values = dict(updates or {})
        allowed_keys = {field.key for field in self.config_fields}
        secret_keys = {field.key for field in self.config_fields if field.secret}

        for key, raw_value in update_values.items():
            if key not in allowed_keys:
                continue

            if raw_value is None:
                merged.pop(key, None)
                continue

            value = raw_value.strip() if isinstance(raw_value, str) else raw_value
            if value == "":
                if key in secret_keys:
                    continue
                merged.pop(key, None)
                continue

            merged[key] = value

        return merged

    async def on_config_updated(self, config: dict[str, Any] | None) -> None:
        """Hook invoked after configuration is loaded from the database."""
        return None

    async def test_connection(self, config: dict[str, Any] | None) -> dict[str, Any]:
        """Test connectivity for models that rely on external providers."""
        missing_fields = self.get_missing_required_fields(config)
        if missing_fields:
            return {
                "ok": False,
                "status": "not_configured",
                "message": f"Missing required configuration: {', '.join(missing_fields)}",
                "details": {"missing_fields": missing_fields},
            }

        return {
            "ok": False,
            "status": "not_supported",
            "message": "Connection testing is not supported for this model.",
            "details": {},
        }
