"""
Application Configuration using Pydantic Settings
"""
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Image Rating Server"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8080

    # CORS
    FRONTEND_URL: str = "http://localhost:8081"
    ALLOWED_ORIGINS: str = f"{FRONTEND_URL},http://localhost:3000"

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse ALLOWED_ORIGINS into a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data.db"
    DATABASE_ECHO: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: str = "logs/app.log"

    # Qwen3-VL defaults
    QWEN3_VL_API_KEY: str | None = None
    QWEN3_VL_BASE_URL: str | None = None
    QWEN3_VL_MODEL_NAME: str | None = None

    # Upload Settings
    UPLOAD_DIR: str = "uploads"
    UPLOAD_MAX_FILE_SIZE: int = 52428800  # 50MB
    UPLOAD_MAX_FILES_PER_REQUEST: int = 10
    UPLOAD_ALLOWED_EXTENSIONS: str = "jpg,jpeg,png,gif,webp,bmp"

    @property
    def upload_allowed_extensions_set(self) -> set[str]:
        """Parse allowed extensions into a set."""
        return {ext.strip().lower() for ext in self.UPLOAD_ALLOWED_EXTENSIONS.split(",")}

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()

    @property
    def log_file_path(self) -> Path:
        """Get the log file path as a Path object."""
        path = Path(self.LOG_FILE_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
