"""
AI Analyze endpoints - Manage AI analysis models and analyze images
"""
import json
from datetime import datetime
from pathlib import Path
from collections.abc import AsyncGenerator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import ActiveUser, get_db
from app.core.config import settings
from app.schemas.analyze import ImageAnalyzeRequest, ImageAnalyzeResponse
from app.schemas.batch import BatchAnalyzeRequest, BatchAnalyzeResponse
from app.services.ai import AIModelInfo, SetActiveModelRequest
from app.services.ai.registry import AIModelRegistry
from app.services.ai.store import (
    deactivate_model,
    get_active_model,
    list_models,
    set_active_model,
)
from app.models.image import Image
from app.services.analysis_result import AnalysisResultService
from app.services.concurrent_analyze import get_concurrent_analyze_service

router = APIRouter()


@router.get("/models", response_model=list[AIModelInfo])
async def list_models_endpoint(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AIModelInfo]:
    """
    List all available AI models.

    Returns:
        List of AI model information including status
    """
    models = await list_models(db)
    return [AIModelInfo(**model) for model in models]


@router.post("/models/active", status_code=status.HTTP_200_OK)
async def set_active_model_endpoint(
    request: SetActiveModelRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """
    Set the active AI model. Only one model can be active at a time.

    Args:
        request: Request containing the model name to activate

    Returns:
        Success message with active model name

    Raises:
        HTTPException: If model not found or failed to activate
    """
    result = await set_active_model(db, request.model_name)
    if result == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model not found: {request.model_name}",
        )
    if result != "ok":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate model: {request.model_name}",
        )

    logger.info(f"Activated AI model: {request.model_name}")

    return {
        "message": f"Model '{request.model_name}' activated successfully",
        "active_model": request.model_name,
    }


@router.get("/models/active", response_model=AIModelInfo | None)
async def get_active_model_endpoint(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIModelInfo | None:
    """
    Get the currently active AI model.

    Returns:
        Active model information or None if no model is active
    """
    model = await get_active_model(db)
    if model is None:
        return None

    models = await list_models(db)
    for item in models:
        if item["name"] == model.name:
            return AIModelInfo(**item)

    return None


@router.delete("/models/active", status_code=status.HTTP_200_OK)
async def deactivate_model_endpoint(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """
    Deactivate the current active model.

    Returns:
        Success message
    """
    active_model = await get_active_model(db)
    if active_model:
        await deactivate_model(db)
        return {"message": f"Model '{active_model.name}' deactivated successfully"}
    return {"message": "No active model to deactivate"}


@router.post("/analyze/batch", response_model=BatchAnalyzeResponse)
async def batch_analyze(
    request: BatchAnalyzeRequest,
    current_user: ActiveUser = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> BatchAnalyzeResponse:
    """
    Analyze multiple images in batch using the active AI model.

    Args:
        request: Batch analysis request with image IDs
        current_user: Current authenticated user
        db: Database session

    Returns:
        BatchAnalyzeResponse with batch analysis results

    Raises:
        HTTPException: If no active model
    """
    # Verify active model exists
    model = await AIModelRegistry.get_active()
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active AI model. Please activate a model first.",
        )

    # Create session factory for concurrent tasks
    async def session_factory() -> AsyncGenerator[AsyncSession, None]:
        async for session in get_db():
            yield session

    # Process batch analysis
    service = get_concurrent_analyze_service()
    return await service.process_batch_analyze(
        session_factory=session_factory,
        image_ids=request.image_ids,
        force_new=request.force_new,
    )


@router.post("/analyze/{image_id}", response_model=ImageAnalyzeResponse)
async def analyze_image(
    image_id: str,
    request: ImageAnalyzeRequest = ImageAnalyzeRequest(),
    current_user: ActiveUser = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> ImageAnalyzeResponse:
    """
    Analyze an image using the active AI model.

    Args:
        image_id: ID of the image to analyze
        request: Analysis request options
        current_user: Current authenticated user
        db: Database session

    Returns:
        ImageAnalyzeResponse with analysis results

    Raises:
        HTTPException: If no active model, image not found, or analysis fails
    """
    import json

    # Verify user owns the image
    result = await db.execute(
        select(Image).where(Image.id == image_id)
    )
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    # Get active model
    model = await AIModelRegistry.get_active()
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active AI model. Please activate a model first.",
        )

    # Check for cached result if not forcing new analysis
    analysis_service = AnalysisResultService(db)
    if not request.force_new:
        cached = await analysis_service.get_latest(image_id, model.name)
        if cached:
            logger.info(f"Using cached analysis for image {image_id}")
            return ImageAnalyzeResponse(
                image_id=image_id,
                model=model.name,
                score=cached.score,
                details=json.loads(cached.details) if cached.details else {},
                created_at=cached.created_at.isoformat(),
            )

    # Get full image path
    image_path = Path(settings.UPLOAD_DIR) / image.file_path
    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file not found",
        )

    # Analyze the image
    try:
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

        return ImageAnalyzeResponse(
            image_id=image_id,
            model=model.name,
            score=analysis_result.get("score"),
            details=analysis_result,
            created_at=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Analysis failed for image {image_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        )
