"""
Concurrent analysis control service for batch AI analysis
"""
import asyncio
import json
from collections.abc import AsyncGenerator, Callable

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.analyze import ImageAnalyzeResponse
from app.schemas.batch import BatchAnalyzeResponse
from app.services.ai.registry import AIModelRegistry
from app.services.analysis_result import AnalysisResultService

# Type alias for session factory
SessionFactory = Callable[[], AsyncGenerator[AsyncSession, None]]


class ConcurrentAnalyzeService:
    """Service for handling concurrent batch AI analysis."""

    def __init__(
        self,
        max_concurrent: int = 3,
    ) -> None:
        """
        Initialize concurrent analyze service.

        Args:
            max_concurrent: Maximum concurrent analyses
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)
        logger.info(f"ConcurrentAnalyzeService initialized with max_concurrent={max_concurrent}")

    async def _process_with_semaphore(
        self,
        session_factory: SessionFactory,
        image_id: str,
        model_name: str,
        force_new: bool,
    ) -> tuple[str, ImageAnalyzeResponse | None, str | None]:
        """
        Process single analysis with semaphore control.

        Each concurrent task creates its own database session to avoid
        race conditions with shared session state.

        Args:
            session_factory: Factory function to create new database sessions
            image_id: Image ID to analyze
            model_name: Name of the AI model to use
            force_new: Whether to force re-analysis

        Returns:
            Tuple of (image_id, ImageAnalyzeResponse or None, error_message or None)
        """
        async with self.semaphore:
            # Create a new session for this specific analysis task
            async for db in session_factory():
                try:
                    from datetime import datetime
                    from pathlib import Path

                    from sqlalchemy import select

                    from app.core.config import settings
                    from app.models.image import Image

                    # Verify image exists and get path
                    result = await db.execute(select(Image).where(Image.id == image_id))
                    image = result.scalar_one_or_none()

                    if not image:
                        return (image_id, None, "Image not found")

                    # Get full image path
                    image_path = Path(settings.UPLOAD_DIR) / image.file_path
                    if not image_path.exists():
                        return (image_id, None, "Image file not found")

                    # Check if we have a cached result (unless force_new)
                    analysis_service = AnalysisResultService(db)
                    if not force_new:
                        cached = await analysis_service.get_latest(image_id, model_name)
                        if cached:
                            logger.info(f"Using cached analysis for image {image_id}")
                            return (
                                image_id,
                                ImageAnalyzeResponse(
                                    image_id=image_id,
                                    model=model_name,
                                    score=cached.score,
                                    details=json.loads(cached.details) if cached.details else {},
                                    created_at=cached.created_at.isoformat(),
                                ),
                                None,
                            )

                    # Get model and analyze
                    model = await AIModelRegistry.get_active()
                    if model is None:
                        return (image_id, None, "No active AI model")

                    if model.name != model_name:
                        return (image_id, None, f"Active model is {model.name}, not {model_name}")

                    logger.info(f"Analyzing image {image_id} with model {model.name}")
                    analysis_result = await model.analyze(str(image_path))

                    # Save result to database
                    distribution = analysis_result.get("distribution")
                    details = {k: v for k, v in analysis_result.items() if k != "distribution"}
                    await analysis_service.save_result(
                        image_id,
                        model.name,
                        analysis_result.get("score"),
                        distribution,
                        details,
                    )

                    response = ImageAnalyzeResponse(
                        image_id=image_id,
                        model=model.name,
                        score=analysis_result.get("score"),
                        details=analysis_result,
                        created_at=datetime.utcnow().isoformat(),
                    )

                    return (image_id, response, None)

                except Exception as e:
                    logger.exception(
                        "Error analyzing image {} with model {} in batch analyze: {}",
                        image_id,
                        model_name,
                        e.__class__.__name__,
                    )
                    return (image_id, None, str(e))

            # This should never be reached
            return (image_id, None, "Failed to create database session")

    async def process_batch_analyze(
        self,
        session_factory: SessionFactory,
        image_ids: list[str],
        force_new: bool = False,
    ) -> BatchAnalyzeResponse:
        """
        Process batch analysis with concurrent control.

        Each concurrent analysis task gets its own database session to ensure
        thread-safety and avoid race conditions with shared session state.

        Args:
            session_factory: Factory function to create new database sessions
            image_ids: List of image IDs to analyze
            force_new: Whether to force re-analysis

        Returns:
            BatchAnalyzeResponse with batch results
        """

        # Handle empty list
        if not image_ids:
            return BatchAnalyzeResponse(
                success=True,
                total=0,
                succeeded=0,
                failed=0,
                results=[],
                message="No images to analyze",
            )

        # Get active model name
        model = await AIModelRegistry.get_active()
        if model is None:
            return BatchAnalyzeResponse(
                success=False,
                total=len(image_ids),
                succeeded=0,
                failed=len(image_ids),
                results=[],
                message="No active AI model",
            )

        model_name = model.name

        # Create tasks for concurrent processing
        tasks = [
            self._process_with_semaphore(
                session_factory=session_factory,
                image_id=image_id,
                model_name=model_name,
                force_new=force_new,
            )
            for image_id in image_ids
        ]

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)

        # Aggregate results
        succeeded = 0
        failed = 0
        response_results: list[ImageAnalyzeResponse] = []
        errors: list[str] = []

        for image_id, response, error in results:
            if response:
                succeeded += 1
                response_results.append(response)
            else:
                failed += 1
                errors.append(f"{image_id}: {error}")

        # Build message
        message_parts = []
        if succeeded > 0:
            message_parts.append(f"成功 {succeeded} 个")
        if failed > 0:
            message_parts.append(f"失败 {failed} 个")
        message = "，".join(message_parts) if message_parts else "无图片分析"

        logger.info(
            f"Batch analyze completed: total={len(image_ids)}, "
            f"succeeded={succeeded}, failed={failed}"
        )

        return BatchAnalyzeResponse(
            success=failed == 0,
            total=len(image_ids),
            succeeded=succeeded,
            failed=failed,
            results=response_results,
            message=message,
        )


# Singleton instance
_concurrent_service: ConcurrentAnalyzeService | None = None


def get_concurrent_analyze_service() -> ConcurrentAnalyzeService:
    """Get or create concurrent analyze service singleton."""
    global _concurrent_service
    if _concurrent_service is None:
        _concurrent_service = ConcurrentAnalyzeService()
    return _concurrent_service
