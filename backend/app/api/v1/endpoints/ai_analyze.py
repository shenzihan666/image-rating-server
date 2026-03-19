"""
AI Analyze endpoints - Manage AI analysis models and analyze images
"""
import json
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.models.image import Image
from app.schemas.analyze import ImageAnalyzeRequest, ImageAnalyzeResponse
from app.schemas.batch import BatchAnalyzeRequest, BatchAnalyzeResponse
from app.services.ai import (
    AIModelConnectionTestResponse,
    AIModelDetail,
    AIModelInfo,
    SetActiveModelRequest,
    UpdateAIModelConfigRequest,
)
from app.services.ai.registry import AIModelRegistry
from app.services.ai.store import (
    deactivate_model,
    get_active_model,
    get_model_detail,
    list_models,
    set_active_model,
    test_model_connection,
    update_model_config,
)
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
    if result["status"] == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model not found: {request.model_name}",
        )
    if result["status"] == "not_configured":
        missing_fields = ", ".join(result.get("missing_fields", []))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{request.model_name}' is not configured: {missing_fields}",
        )
    if result["status"] != "ok":
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


@router.get("/models/{model_name}", response_model=AIModelDetail)
async def get_model_detail_endpoint(
    model_name: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIModelDetail:
    """Get detailed information for a specific AI model."""
    model = await get_model_detail(db, model_name)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model not found: {model_name}",
        )
    return AIModelDetail(**model)


@router.put("/models/{model_name}/config", response_model=AIModelDetail)
async def update_model_config_endpoint(
    model_name: str,
    request: UpdateAIModelConfigRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIModelDetail:
    """Persist configuration for a model and sync it to runtime state."""
    model = await update_model_config(db, model_name, request.config)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model not found: {model_name}",
        )
    return AIModelDetail(**model)


@router.post(
    "/models/{model_name}/test-connection",
    response_model=AIModelConnectionTestResponse,
)
async def test_model_connection_endpoint(
    model_name: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIModelConnectionTestResponse:
    """Test connectivity for a configured model without activating it."""
    result = await test_model_connection(db, model_name)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model not found: {model_name}",
        )
    return AIModelConnectionTestResponse(**result)


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
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BatchAnalyzeResponse:
    """
    Analyze multiple images in batch using the active AI model.

    Args:
        request: Batch analysis request with image IDs
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
    db: Annotated[AsyncSession, Depends(get_db)],
    request: ImageAnalyzeRequest = ImageAnalyzeRequest(),
) -> ImageAnalyzeResponse:
    """
    Analyze an image using the active AI model.

    Args:
        image_id: ID of the image to analyze
        db: Database session
        request: Analysis request options

    Returns:
        ImageAnalyzeResponse with analysis results

    Raises:
        HTTPException: If no active model, image not found, or analysis fails
    """
    # Find the image
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
            cached_details = json.loads(cached.details) if cached.details else {}
            if cached.prompt_version_id and "prompt" not in cached_details:
                cached_details["prompt"] = {
                    "prompt_version_id": cached.prompt_version_id,
                    "prompt_name": cached.prompt_name,
                    "prompt_version_number": cached.prompt_version_number,
                }
            return ImageAnalyzeResponse(
                image_id=image_id,
                model=model.name,
                score=cached.score,
                details=cached_details,
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
        prompt_meta = analysis_result.get("prompt")
        prompt_version_id = None
        prompt_name = None
        prompt_version_number = None
        if isinstance(prompt_meta, dict):
            prompt_version_id = prompt_meta.get("prompt_version_id")
            prompt_name = prompt_meta.get("prompt_name")
            raw_version_number = prompt_meta.get("prompt_version_number")
            if isinstance(raw_version_number, int):
                prompt_version_number = raw_version_number
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

        return ImageAnalyzeResponse(
            image_id=image_id,
            model=model.name,
            score=analysis_result.get("score"),
            details=analysis_result,
            created_at=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.exception(
            "Analysis failed for image {} with model {}: {}",
            image_id,
            model.name,
            e.__class__.__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        )
