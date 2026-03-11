"""
Analysis Result service for managing AI analysis results persistence
"""
import json
from uuid import uuid4

from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_result import AnalysisResult


class AnalysisResultService:
    """Service for managing AI analysis results."""

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize analysis result service.

        Args:
            db: Database session
        """
        self.db = db

    async def save_result(
        self,
        image_id: str,
        model: str,
        score: float | None,
        distribution: list[float] | None = None,
        details: dict | None = None,
        prompt_version_id: str | None = None,
        prompt_name: str | None = None,
        prompt_version_number: int | None = None,
    ) -> AnalysisResult:
        """
        Save an analysis result to the database.

        Args:
            image_id: ID of the analyzed image
            model: Name of the AI model used
            score: Mean score (1-10)
            distribution: Optional score distribution array
            details: Optional full analysis details

        Returns:
            Created AnalysisResult
        """
        result = AnalysisResult(
            id=str(uuid4()),
            image_id=image_id,
            model=model,
            score=score,
            min_score=min(distribution) if distribution else None,
            max_score=max(distribution) if distribution else None,
            distribution=json.dumps(distribution) if distribution else None,
            details=json.dumps(details) if details else None,
            prompt_version_id=prompt_version_id,
            prompt_name=prompt_name,
            prompt_version_number=prompt_version_number,
        )

        self.db.add(result)
        await self.db.commit()
        await self.db.refresh(result)

        logger.info(f"Saved analysis result for image {image_id} with score {score}")
        return result

    async def get_latest(
        self,
        image_id: str,
        model: str | None = None,
    ) -> AnalysisResult | None:
        """
        Get the latest analysis result for an image.

        Args:
            image_id: ID of the image
            model: Optional model name filter

        Returns:
            Latest AnalysisResult or None
        """
        query = select(AnalysisResult).where(AnalysisResult.image_id == image_id)

        if model:
            query = query.where(AnalysisResult.model == model)

        query = query.order_by(AnalysisResult.created_at.desc()).limit(1)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def delete_by_image_id(self, image_id: str) -> int:
        """
        Delete all analysis results for an image.

        Args:
            image_id: ID of the image

        Returns:
            Number of deleted results
        """
        result = await self.db.execute(
            delete(AnalysisResult).where(AnalysisResult.image_id == image_id)
        )
        await self.db.commit()

        count = result.rowcount
        if count:
            logger.info(f"Deleted {count} analysis results for image {image_id}")

        return count

    @staticmethod
    def _extract_decision(record: AnalysisResult) -> str | None:
        """Extract AI decision string from analysis details JSON."""
        if not record.details:
            return None
        try:
            details = json.loads(record.details)
            result_obj = details.get("result")
            if isinstance(result_obj, dict):
                return result_obj.get("decision")
        except (json.JSONDecodeError, TypeError):
            pass
        return None

    async def get_scores_for_images(
        self,
        image_ids: list[str],
        model: str | None = None,
    ) -> dict[str, tuple[float | None, str | None, str | None, str | None]]:
        """
        Get the latest AI scores for multiple images.

        Args:
            image_ids: List of image IDs
            model: Optional model name filter

        Returns:
            Dictionary mapping image_id to (score, model, analyzed_at, decision) tuple
        """
        if not image_ids:
            return {}

        result_map: dict[str, tuple[float | None, str | None, str | None, str | None]] = {}

        for image_id in image_ids:
            latest = await self.get_latest(image_id, model)
            if latest:
                result_map[image_id] = (
                    latest.score,
                    latest.model,
                    latest.created_at.isoformat() if latest.created_at else None,
                    self._extract_decision(latest),
                )
            else:
                result_map[image_id] = (None, None, None, None)

        return result_map

    async def get_latest_score_for_image(
        self,
        image_id: str,
    ) -> tuple[float | None, str | None, str | None, str | None]:
        """
        Get the latest score for a single image.

        Args:
            image_id: ID of the image

        Returns:
            Tuple of (score, model, analyzed_at, decision) or (None, None, None, None)
        """
        result = await self.get_latest(image_id)
        if result:
            return (
                result.score,
                result.model,
                result.created_at.isoformat() if result.created_at else None,
                self._extract_decision(result),
            )
        return (None, None, None, None)
