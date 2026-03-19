"""
Image service for business logic layer
"""
from pathlib import Path

from loguru import logger
from sqlalchemy import func, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.image import Image


class ImageService:
    """Service for image operations."""

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize image service.

        Args:
            db: Database session
        """
        self.db = db

    async def get_images(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> tuple[list[Image], int]:
        """
        Get paginated list of images.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            search: Optional search term for title/description
            date_from: Optional start date filter (ISO format)
            date_to: Optional end date filter (ISO format)

        Returns:
            Tuple of (images list, total count)
        """
        from datetime import datetime

        # Build base query
        query = select(Image)

        # Add search filter if provided
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (Image.title.ilike(search_pattern)) | (Image.description.ilike(search_pattern))
            )

        # Add date filters if provided
        if date_from:
            try:
                from_dt = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
                query = query.where(Image.created_at >= from_dt)
            except ValueError as e:
                logger.warning(f"Invalid date_from format: {date_from}, error: {e}")

        if date_to:
            try:
                to_dt = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
                query = query.where(Image.created_at <= to_dt)
            except ValueError as e:
                logger.warning(f"Invalid date_to format: {date_to}, error: {e}")

        # Get total count
        count_query = select(func.count()).select_from(query.alias())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Get paginated results, ordered by created_at desc
        query = query.order_by(Image.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        images = list(result.scalars().all())

        return images, total

    async def get_image(self, image_id: str) -> Image | None:
        """
        Get a single image by ID.

        Args:
            image_id: Image ID

        Returns:
            Image object or None if not found
        """
        query = select(Image).where(Image.id == image_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_image(
        self,
        image_id: str,
        title: str | None = None,
        description: str | None = None,
    ) -> Image | None:
        """
        Update image metadata.

        Args:
            image_id: Image ID
            title: New title (optional)
            description: New description (optional)

        Returns:
            Updated Image object or None if not found
        """
        query = select(Image).where(Image.id == image_id)
        result = await self.db.execute(query)
        image = result.scalar_one_or_none()

        if not image:
            return None

        # Update fields
        if title is not None:
            image.title = title
        if description is not None:
            image.description = description

        await self.db.commit()
        await self.db.refresh(image)

        logger.info(f"Updated image {image_id}")
        return image

    async def delete_image(self, image_id: str) -> bool:
        """
        Delete an image and its file.

        Args:
            image_id: Image ID

        Returns:
            True if deleted, False if not found
        """
        query = select(Image).where(Image.id == image_id)
        result = await self.db.execute(query)
        image = result.scalar_one_or_none()

        if not image:
            return False

        # Delete file from disk
        file_path = Path(settings.UPLOAD_DIR) / image.file_path
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            # Continue with database deletion even if file deletion fails

        # Delete from database
        await self.db.execute(delete(Image).where(Image.id == image_id))
        await self.db.commit()

        logger.info(f"Deleted image {image_id}")
        return True
