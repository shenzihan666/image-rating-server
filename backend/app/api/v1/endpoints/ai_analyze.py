"""
AI Analyze endpoints - Manage AI analysis models
"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.ai import AIModelInfo, SetActiveModelRequest
from app.services.ai.store import (
    deactivate_model,
    get_active_model,
    list_models,
    set_active_model,
)

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
