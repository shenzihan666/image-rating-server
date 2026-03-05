"""
File storage service with atomic write and hash computation
"""
import asyncio
import hashlib
import shutil
import uuid
from datetime import datetime
from pathlib import Path

import aiofiles
from loguru import logger
from PIL import Image as PILImage

from app.core.config import settings


def _sync_extract_image_dimensions(file_path: Path) -> tuple[int | None, int | None]:
    """
    Synchronously extract image dimensions using PIL.

    This is a blocking operation and should be run in a thread pool.

    Args:
        file_path: Path to image file

    Returns:
        Tuple of (width, height) or (None, None) if extraction fails
    """
    try:
        with PILImage.open(file_path) as img:
            return img.size[0], img.size[1]
    except Exception:
        return None, None


def _sync_move_file(src: Path, dst: Path) -> None:
    """
    Synchronously move a file.

    This is a blocking operation and should be run in a thread pool.

    Args:
        src: Source file path
        dst: Destination file path
    """
    shutil.move(str(src), str(dst))


class FileStorageService:
    """Service for file storage operations."""

    def __init__(self) -> None:
        """Initialize storage service."""
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.temp_dir = self.upload_dir / "temp"
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure upload directories exist."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def _get_date_path(self) -> Path:
        """Get date-based subdirectory path (YYYY/MM/DD)."""
        now = datetime.now()
        return Path(str(now.year)) / f"{now.month:02d}" / f"{now.day:02d}"

    def _generate_filename(self, original_ext: str) -> str:
        """Generate unique filename using UUID."""
        return f"{uuid.uuid4()}{original_ext}"

    async def compute_hash(self, file_content: bytes) -> str:
        """
        Compute SHA256 hash of file content.

        Args:
            file_content: Raw file bytes

        Returns:
            Hexadecimal SHA256 hash string
        """
        return hashlib.sha256(file_content).hexdigest()

    async def save_file_atomic(
        self,
        file_content: bytes,
        original_filename: str,
    ) -> tuple[Path, str]:
        """
        Save file atomically using temp file + move pattern.

        Args:
            file_content: Raw file bytes
            original_filename: Original filename for extension extraction

        Returns:
            Tuple of (absolute_path, relative_path)
        """
        # Extract extension
        ext = Path(original_filename).suffix.lower() or ".bin"

        # Generate paths
        date_path = self._get_date_path()
        filename = self._generate_filename(ext)
        relative_path = date_path / filename
        absolute_path = self.upload_dir / relative_path

        # Ensure date directory exists
        (self.upload_dir / date_path).mkdir(parents=True, exist_ok=True)

        # Write to temp file first
        temp_filename = f"{uuid.uuid4()}.tmp"
        temp_path = self.temp_dir / temp_filename

        try:
            async with aiofiles.open(temp_path, "wb") as f:
                await f.write(file_content)

            # Atomic move (async to avoid blocking event loop)
            await asyncio.to_thread(_sync_move_file, temp_path, absolute_path)
            logger.debug(f"File saved atomically: {absolute_path}")

            return absolute_path, str(relative_path).replace("\\", "/")
        except Exception as e:
            # Cleanup temp file on failure
            if temp_path.exists():
                temp_path.unlink()
            logger.error(f"Failed to save file: {e}")
            raise

    async def extract_image_dimensions(self, file_path: Path) -> tuple[int | None, int | None]:
        """
        Extract image dimensions using PIL.

        This method runs the PIL operation in a thread pool to avoid
        blocking the asyncio event loop.

        Args:
            file_path: Path to image file

        Returns:
            Tuple of (width, height) or (None, None) if extraction fails
        """
        try:
            # PIL operations are synchronous, run in thread pool
            width, height = await asyncio.to_thread(
                _sync_extract_image_dimensions, file_path
            )
            if width is None or height is None:
                logger.warning(f"Failed to extract image dimensions for: {file_path}")
            return width, height
        except Exception as e:
            logger.warning(f"Failed to extract image dimensions: {e}")
            return None, None

    def validate_extension(self, filename: str) -> bool:
        """
        Validate file extension against allowed extensions.

        Args:
            filename: Filename to validate

        Returns:
            True if extension is allowed
        """
        ext = Path(filename).suffix.lower().lstrip(".")
        return ext in settings.upload_allowed_extensions_set

    def validate_file_size(self, file_size: int) -> bool:
        """
        Validate file size against max allowed size.

        Args:
            file_size: File size in bytes

        Returns:
            True if file size is within limit
        """
        return file_size <= settings.UPLOAD_MAX_FILE_SIZE


# Singleton instance
_storage_service: FileStorageService | None = None


def get_storage_service() -> FileStorageService:
    """Get or create storage service singleton."""
    global _storage_service
    if _storage_service is None:
        _storage_service = FileStorageService()
    return _storage_service
