"""
Auto-analyze service — runs image analysis after upload without an HTTP round-trip.

Called by the upload endpoint when auto_analyze=true is requested.
Errors in analysis never propagate back as upload failures.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.image import Image
from app.services.ai.registry import AIModelRegistry
from app.services.analysis_result import AnalysisResultService


async def run_auto_analyze(image_id: str, db: AsyncSession) -> bool:
    """
    Analyze a single image using the currently active AI model.

    Args:
        image_id: ID of the image to analyze.
        db: Database session (shared with upload transaction so the image row
            is already visible).

    Returns:
        True if analysis completed successfully, False otherwise.
    """
    try:
        model = await AIModelRegistry.get_active()
        if model is None:
            logger.info(
                f"auto_analyze skipped for image {image_id}: no active model"
            )
            return False

        # Load image record — it was just committed by the upload service.
        result = await db.execute(select(Image).where(Image.id == image_id))
        image = result.scalar_one_or_none()
        if image is None:
            logger.warning(
                f"auto_analyze skipped for image {image_id}: record not found"
            )
            return False

        image_path = Path(settings.UPLOAD_DIR) / image.file_path
        if not image_path.exists():
            logger.warning(
                f"auto_analyze skipped for image {image_id}: file not found at {image_path}"
            )
            return False

        logger.info(f"auto_analyze: analyzing image {image_id} with model {model.name}")
        analysis_result = await model.analyze(str(image_path))

        distribution = analysis_result.get("distribution")
        details = {k: v for k, v in analysis_result.items() if k != "distribution"}

        prompt_meta = analysis_result.get("prompt")
        prompt_version_id = None
        prompt_name = None
        prompt_version_number = None
        if isinstance(prompt_meta, dict):
            prompt_version_id = prompt_meta.get("prompt_version_id")
            prompt_name = prompt_meta.get("prompt_name")
            raw_version = prompt_meta.get("prompt_version_number")
            if isinstance(raw_version, int):
                prompt_version_number = raw_version

        analysis_service = AnalysisResultService(db)
        await analysis_service.save_result(
            image_id,
            model.name,
            analysis_result.get("score"),
            distribution,
            details,
            prompt_version_id=prompt_version_id,
            prompt_name=prompt_name,
            prompt_version_number=prompt_version_number,
        )

        logger.info(
            f"auto_analyze: completed for image {image_id}, "
            f"score={analysis_result.get('score')}"
        )
        return True

    except Exception as exc:
        logger.warning(
            f"auto_analyze failed for image {image_id} (upload still succeeds): {exc}"
        )
        return False
