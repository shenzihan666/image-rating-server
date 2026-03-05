"""
Logging configuration using Loguru
"""
import sys

from loguru import logger

from app.core.config import settings


def setup_logger() -> None:
    """
    Configure Loguru logger with console and file handlers.

    Replaces the default Python logging with Loguru for better formatting.
    """
    # Remove default handler
    logger.remove()

    # Console handler with formatting
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True,
    )

    # File handler for persistent logging
    logger.add(
        settings.log_file_path,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.LOG_LEVEL,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )

    logger.info(f"Logger configured: {settings.LOG_LEVEL} level")
