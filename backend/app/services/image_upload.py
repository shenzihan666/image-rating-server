"""
Image upload business logic service
"""
import uuid

from fastapi import UploadFile
from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# Type alias for Image model columns
from app.models.image import Image
from app.schemas.upload import ImageMetadata, UploadResult, UploadStatus
from app.services.storage import FileStorageService, get_storage_service


class ImageUploadService:
    """Service for handling image upload business logic."""

    def __init__(
        self,
        storage_service: FileStorageService | None = None,
    ) -> None:
        """Initialize upload service."""
        self.storage = storage_service or get_storage_service()

    async def validate_file(self, file: UploadFile) -> tuple[bool, str | None]:
        """
        Validate uploaded file.

        Args:
            file: UploadFile object

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file.filename:
            return False, "Filename is required"

        if not self.storage.validate_extension(file.filename):
            return False, f"File extension not allowed: {file.filename}"

        # Read file content for validation and processing
        content = await file.read()
        await file.seek(0)  # Reset for potential re-read

        if not self.storage.validate_file_size(len(content)):
            return False, f"File size exceeds limit: {file.filename}"

        return True, None

    async def check_duplicate(
        self,
        db: AsyncSession,
        hash_sha256: str,
    ) -> Image | None:
        """
        Check if image with same hash already exists.

        Args:
            db: Database session
            hash_sha256: SHA256 hash to check

        Returns:
            Existing Image if found, None otherwise
        """
        stmt = select(Image).where(Image.hash_sha256 == hash_sha256)  # type: ignore[misc]
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def process_single_upload(
        self,
        db: AsyncSession,
        file: UploadFile,
        provided_hash: str | None,
        user_id: str,
    ) -> UploadResult:
        """
        Process a single file upload.

        Args:
            db: Database session
            file: UploadFile object
            provided_hash: Hash provided by client
            user_id: ID of uploading user

        Returns:
            UploadResult with status and metadata
        """
        original_filename = file.filename or "unknown"

        try:
            # Validate file
            is_valid, error = await self.validate_file(file)
            if not is_valid:
                return UploadResult(
                    status=UploadStatus.FAILED,
                    original_filename=original_filename,
                    error_message=error,
                    is_duplicate=False,
                )

            # Read file content
            content = await file.read()

            # Compute hash
            computed_hash = await self.storage.compute_hash(content)

            # Validate hash if provided
            if provided_hash and provided_hash != computed_hash:
                logger.warning(
                    f"Hash mismatch for {original_filename}: "
                    f"provided={provided_hash}, computed={computed_hash}"
                )

            # Check for duplicates using computed hash
            existing_image = await self.check_duplicate(db, computed_hash)
            if existing_image:
                return UploadResult(
                    status=UploadStatus.DUPLICATED,
                    original_filename=original_filename,
                    metadata=ImageMetadata(
                        image_id=existing_image.id,
                        file_name=existing_image.title,
                        file_size=existing_image.file_size,
                        mime_type=existing_image.mime_type,
                        width=existing_image.width,
                        height=existing_image.height,
                        file_path=existing_image.file_path,
                        hash_sha256=existing_image.hash_sha256 or computed_hash,
                    ),
                    is_duplicate=True,
                )

            # Save file atomically
            absolute_path, relative_path = await self.storage.save_file_atomic(
                content, original_filename
            )

            # Extract image dimensions (async to avoid blocking event loop)
            width, height = await self.storage.extract_image_dimensions(absolute_path)

            # Create database record with nested transaction for race condition handling
            image_id = str(uuid.uuid4())
            image = Image(
                id=image_id,
                user_id=user_id,
                title=original_filename,
                description=None,
                file_path=relative_path,
                file_size=len(content),
                width=width,
                height=height,
                mime_type=file.content_type or "application/octet-stream",
                hash_sha256=computed_hash,
            )

            # Use nested transaction (SAVEPOINT) to handle race condition
            try:
                async with db.begin_nested():
                    db.add(image)
                    await db.flush()
                    logger.info(f"Image uploaded successfully: {image_id} - {original_filename}")
            except IntegrityError:
                # Race condition: another request inserted the same hash first
                # The nested transaction is automatically rolled back
                logger.info(f"Race condition detected for {original_filename}, hash already exists: {computed_hash}")

                # Re-query to get the existing image
                existing_image = await self.check_duplicate(db, computed_hash)
                if existing_image:
                    return UploadResult(
                        status=UploadStatus.DUPLICATED,
                        original_filename=original_filename,
                        metadata=ImageMetadata(
                            image_id=existing_image.id,
                            file_name=existing_image.title,
                            file_size=existing_image.file_size,
                            mime_type=existing_image.mime_type,
                            width=existing_image.width,
                            height=existing_image.height,
                            file_path=existing_image.file_path,
                            hash_sha256=existing_image.hash_sha256 or computed_hash,
                        ),
                        is_duplicate=True,
                    )
                else:
                    # Should not happen, but handle gracefully
                    return UploadResult(
                        status=UploadStatus.FAILED,
                        original_filename=original_filename,
                        error_message=f"IntegrityError but no duplicate found for hash {computed_hash}",
                        is_duplicate=False,
                    )

            # If we get here without exception, the insert was successful
            return UploadResult(
                status=UploadStatus.SUCCESS,
                original_filename=original_filename,
                metadata=ImageMetadata(
                    image_id=image_id,
                    file_name=original_filename,
                    file_size=len(content),
                    mime_type=file.content_type or "application/octet-stream",
                    width=width,
                    height=height,
                    file_path=relative_path,
                    hash_sha256=computed_hash,
                ),
                is_duplicate=False,
            )

        except Exception as e:
            logger.error(f"Failed to process upload {original_filename}: {e}")
            return UploadResult(
                status=UploadStatus.FAILED,
                original_filename=original_filename,
                error_message=str(e),
                is_duplicate=False,
            )


# Singleton instance
_upload_service: ImageUploadService | None = None


def get_upload_service() -> ImageUploadService:
    """Get or create upload service singleton."""
    global _upload_service
    if _upload_service is None:
        _upload_service = ImageUploadService()
    return _upload_service
