"""
Concurrent upload control service
"""
import asyncio
import json

from fastapi import UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.upload import UploadResponse, UploadResult, UploadStatus
from app.services.image_upload import ImageUploadService, get_upload_service


class ConcurrentUploadService:
    """Service for handling concurrent batch uploads."""

    def __init__(
        self,
        upload_service: ImageUploadService | None = None,
        max_concurrent: int = 3,
    ) -> None:
        """
        Initialize concurrent upload service.

        Args:
            upload_service: Image upload service instance
            max_concurrent: Maximum concurrent uploads
        """
        self.upload_service = upload_service or get_upload_service()
        self.semaphore = asyncio.Semaphore(max_concurrent)
        logger.info(f"ConcurrentUploadService initialized with max_concurrent={max_concurrent}")

    async def _process_with_semaphore(
        self,
        db: AsyncSession,
        file: UploadFile,
        provided_hash: str | None,
        user_id: str,
    ) -> UploadResult:
        """
        Process single upload with semaphore control.

        Args:
            db: Database session
            file: UploadFile object
            provided_hash: Hash provided by client
            user_id: User ID

        Returns:
            UploadResult
        """
        async with self.semaphore:
            return await self.upload_service.process_single_upload(
                db=db,
                file=file,
                provided_hash=provided_hash,
                user_id=user_id,
            )

    def _parse_hashes(self, hashes_json: str | None, file_count: int) -> list[str | None]:
        """
        Parse hashes JSON string into list.

        Args:
            hashes_json: JSON string of hashes array
            file_count: Number of files for validation

        Returns:
            List of hash strings (or None if not provided)
        """
        if not hashes_json:
            return [None] * file_count

        try:
            hashes = json.loads(hashes_json)
            if not isinstance(hashes, list):
                logger.warning("Hashes is not a list, using None for all files")
                return [None] * file_count

            # Pad with None if fewer hashes than files
            if len(hashes) < file_count:
                hashes.extend([None] * (file_count - len(hashes)))

            return hashes[:file_count]
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse hashes JSON: {e}")
            return [None] * file_count

    async def process_batch_upload(
        self,
        db: AsyncSession,
        files: list[UploadFile],
        hashes_json: str | None,
        user_id: str,
    ) -> UploadResponse:
        """
        Process batch upload with concurrent control.

        Args:
            db: Database session
            files: List of UploadFile objects
            hashes_json: JSON string of hashes array
            user_id: User ID

        Returns:
            UploadResponse with batch results
        """
        # Validate file count
        if len(files) > settings.UPLOAD_MAX_FILES_PER_REQUEST:
            return UploadResponse(
                success=False,
                total=len(files),
                succeeded=0,
                duplicated=0,
                failed=len(files),
                results=[],
                message=f"Too many files: {len(files)} > {settings.UPLOAD_MAX_FILES_PER_REQUEST}",
            )

        if not files:
            return UploadResponse(
                success=True,
                total=0,
                succeeded=0,
                duplicated=0,
                failed=0,
                results=[],
                message="No files uploaded",
            )

        # Parse hashes
        hashes = self._parse_hashes(hashes_json, len(files))

        # Create tasks for concurrent processing
        tasks = [
            self._process_with_semaphore(
                db=db,
                file=file,
                provided_hash=hash_val,
                user_id=user_id,
            )
            for file, hash_val in zip(files, hashes)
        ]

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)

        # Aggregate results
        succeeded = sum(1 for r in results if r.status == UploadStatus.SUCCESS)
        duplicated = sum(1 for r in results if r.status == UploadStatus.DUPLICATED)
        failed = sum(1 for r in results if r.status == UploadStatus.FAILED)

        # Build message
        message_parts = []
        if succeeded > 0:
            message_parts.append(f"成功 {succeeded} 个")
        if duplicated > 0:
            message_parts.append(f"重复 {duplicated} 个")
        if failed > 0:
            message_parts.append(f"失败 {failed} 个")
        message = "，".join(message_parts) if message_parts else "无文件处理"

        logger.info(
            f"Batch upload completed: total={len(files)}, "
            f"succeeded={succeeded}, duplicated={duplicated}, failed={failed}"
        )

        return UploadResponse(
            success=failed == 0,
            total=len(files),
            succeeded=succeeded,
            duplicated=duplicated,
            failed=failed,
            results=list(results),
            message=message,
        )


# Singleton instance
_concurrent_service: ConcurrentUploadService | None = None


def get_concurrent_upload_service() -> ConcurrentUploadService:
    """Get or create concurrent upload service singleton."""
    global _concurrent_service
    if _concurrent_service is None:
        _concurrent_service = ConcurrentUploadService()
    return _concurrent_service
