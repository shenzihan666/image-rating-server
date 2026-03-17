"""
Concurrent upload control service
"""
import asyncio
import json
from collections.abc import AsyncGenerator, Callable

from fastapi import UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.upload import UploadResponse, UploadResult, UploadStatus
from app.services.image_upload import ImageUploadService, get_upload_service

# Type alias for session factory
SessionFactory = Callable[[], AsyncGenerator[AsyncSession, None]]


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
        session_factory: SessionFactory,
        file: UploadFile,
        provided_hash: str | None,
        user_id: str,
    ) -> UploadResult:
        """
        Process single upload with semaphore control.

        Each concurrent task creates its own database session to avoid
        race conditions with shared session state.

        Args:
            session_factory: Factory function to create new database sessions
            file: UploadFile object
            provided_hash: Hash provided by client
            user_id: User ID

        Returns:
            UploadResult
        """
        async with self.semaphore:
            # Create a new session for this specific upload task
            async for db in session_factory():
                try:
                    return await self.upload_service.process_single_upload(
                        db=db,
                        file=file,
                        provided_hash=provided_hash,
                        user_id=user_id,
                    )
                except Exception as e:
                    logger.error(f"Error in concurrent upload task: {e}")
                    return UploadResult(
                        status=UploadStatus.FAILED,
                        original_filename=file.filename or "unknown",
                        error_message=str(e),
                        is_duplicate=False,
                    )
            # This should never be reached, but satisfy type checker
            return UploadResult(
                status=UploadStatus.FAILED,
                original_filename=file.filename or "unknown",
                error_message="Failed to create database session",
                is_duplicate=False,
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
        session_factory: SessionFactory,
        files: list[UploadFile] | None,
        hashes_json: str | None,
        user_id: str,
        auto_analyze: bool = False,
    ) -> UploadResponse:
        """
        Process batch upload with concurrent control.

        Each concurrent upload task gets its own database session to ensure
        thread-safety and avoid race conditions with shared session state.

        Args:
            session_factory: Factory function to create new database sessions
            files: List of UploadFile objects (None or empty allowed)
            hashes_json: JSON string of hashes array
            user_id: User ID

        Returns:
            UploadResponse with batch results
        """
        # Handle None or empty files
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

        # Parse hashes
        hashes = self._parse_hashes(hashes_json, len(files))

        # Create tasks for concurrent processing
        # Each task will create its own database session from the factory
        tasks = [
            self._process_with_semaphore(
                session_factory=session_factory,
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

        # Trigger auto-analyze for newly uploaded images (not duplicates/failures)
        if auto_analyze and succeeded > 0:
            from app.services.auto_analyze import run_auto_analyze

            new_image_ids = [
                r.metadata.image_id
                for r in results
                if r.status == UploadStatus.SUCCESS and r.metadata is not None
            ]
            if new_image_ids:
                logger.info(
                    f"auto_analyze: triggering analysis for {len(new_image_ids)} new image(s)"
                )
                async for db in session_factory():
                    analyze_tasks = [
                        run_auto_analyze(image_id, db) for image_id in new_image_ids
                    ]
                    await asyncio.gather(*analyze_tasks)

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
