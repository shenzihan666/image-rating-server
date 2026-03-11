"""
Image management endpoints
"""
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from app.api.deps import ActiveUser, get_db
from app.core.config import settings
from app.core.database import AsyncSession
from app.schemas.analyze import ImageAnalyzeResponse
from app.schemas.batch import BatchDeleteRequest, BatchDeleteResponse
from app.schemas.image import ImageListResponse, ImageResponse, ImageUpdate
from app.services.analysis_result import AnalysisResultService
from app.services.image import ImageService

router = APIRouter()


@router.get("/", response_model=ImageListResponse)
async def list_images(
    current_user: ActiveUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(min_length=1)] = None,
    date_from: Annotated[str | None, Query(description="Filter images from this date (ISO format)")] = None,
    date_to: Annotated[str | None, Query(description="Filter images until this date (ISO format)")] = None,
) -> ImageListResponse:
    """
    List current user's images with pagination.

    Args:
        current_user: Current authenticated user
        db: Database session
        page: Page number (default: 1)
        page_size: Items per page (default: 20, max: 100)
        search: Optional search term for title/description
        date_from: Optional start date filter (ISO format)
        date_to: Optional end date filter (ISO format)

    Returns:
        ImageListResponse with paginated image list
    """
    image_service = ImageService(db)
    images, total = await image_service.get_images(
        user_id=current_user["user_id"],
        page=page,
        page_size=page_size,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )

    # Get AI scores for all images
    analysis_service = AnalysisResultService(db)
    image_ids = [img.id for img in images]
    scores_map = await analysis_service.get_scores_for_images(image_ids)

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return ImageListResponse(
        items=[
            ImageResponse(
                id=img.id,
                user_id=img.user_id,
                title=img.title,
                description=img.description,
                file_path=img.file_path,
                file_size=img.file_size,
                width=img.width,
                height=img.height,
                mime_type=img.mime_type,
                hash_sha256=img.hash_sha256,
                average_rating=img.average_rating,
                rating_count=img.rating_count,
                created_at=img.created_at.isoformat(),
                updated_at=img.updated_at.isoformat(),
                ai_score=scores_map.get(img.id, (None, None, None, None))[0],
                ai_model=scores_map.get(img.id, (None, None, None, None))[1],
                ai_analyzed_at=scores_map.get(img.id, (None, None, None, None))[2],
                ai_decision=scores_map.get(img.id, (None, None, None, None))[3],
            )
            for img in images
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{image_id}", response_model=ImageResponse)
async def get_image(
    image_id: str,
    current_user: ActiveUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ImageResponse:
    """
    Get a single image by ID.

    Args:
        image_id: Image ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        ImageResponse with image details

    Raises:
        HTTPException: If image not found
    """
    image_service = ImageService(db)
    image = await image_service.get_image(image_id, current_user["user_id"])

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    # Get latest AI score
    analysis_service = AnalysisResultService(db)
    score, model, analyzed_at, decision = await analysis_service.get_latest_score_for_image(image_id)

    return ImageResponse(
        id=image.id,
        user_id=image.user_id,
        title=image.title,
        description=image.description,
        file_path=image.file_path,
        file_size=image.file_size,
        width=image.width,
        height=image.height,
        mime_type=image.mime_type,
        hash_sha256=image.hash_sha256,
        average_rating=image.average_rating,
        rating_count=image.rating_count,
        created_at=image.created_at.isoformat(),
        updated_at=image.updated_at.isoformat(),
        ai_score=score,
        ai_model=model,
        ai_analyzed_at=analyzed_at,
        ai_decision=decision,
    )


@router.get("/{image_id}/analysis", response_model=ImageAnalyzeResponse)
async def get_image_analysis(
    image_id: str,
    current_user: ActiveUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ImageAnalyzeResponse:
    """
    Get the latest saved AI analysis for an image.

    Args:
        image_id: Image ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        ImageAnalyzeResponse with latest saved analysis

    Raises:
        HTTPException: If image or analysis result not found
    """
    image_service = ImageService(db)
    image = await image_service.get_image(image_id, current_user["user_id"])

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    analysis_service = AnalysisResultService(db)
    latest = await analysis_service.get_latest(image_id)
    if not latest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis result not found",
        )

    details = json.loads(latest.details) if latest.details else {}
    if latest.prompt_version_id and "prompt" not in details:
        details["prompt"] = {
            "prompt_version_id": latest.prompt_version_id,
            "prompt_name": latest.prompt_name,
            "prompt_version_number": latest.prompt_version_number,
        }

    return ImageAnalyzeResponse(
        image_id=image_id,
        model=latest.model,
        score=latest.score,
        details=details,
        created_at=latest.created_at.isoformat(),
    )


@router.patch("/{image_id}", response_model=ImageResponse)
async def update_image(
    image_id: str,
    request: ImageUpdate,
    current_user: ActiveUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ImageResponse:
    """
    Update image metadata (title and/or description).

    Args:
        image_id: Image ID
        request: Update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        ImageResponse with updated image details

    Raises:
        HTTPException: If image not found
    """
    image_service = ImageService(db)
    image = await image_service.update_image(
        image_id=image_id,
        user_id=current_user["user_id"],
        title=request.title,
        description=request.description,
    )

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    # Get latest AI score
    analysis_service = AnalysisResultService(db)
    score, model, analyzed_at, decision = await analysis_service.get_latest_score_for_image(image_id)

    return ImageResponse(
        id=image.id,
        user_id=image.user_id,
        title=image.title,
        description=image.description,
        file_path=image.file_path,
        file_size=image.file_size,
        width=image.width,
        height=image.height,
        mime_type=image.mime_type,
        hash_sha256=image.hash_sha256,
        average_rating=image.average_rating,
        rating_count=image.rating_count,
        created_at=image.created_at.isoformat(),
        updated_at=image.updated_at.isoformat(),
        ai_score=score,
        ai_model=model,
        ai_analyzed_at=analyzed_at,
        ai_decision=decision,
    )


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: str,
    current_user: ActiveUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete an image and its file.

    Args:
        image_id: Image ID
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: If image not found
    """
    image_service = ImageService(db)
    # Delete analysis results first
    analysis_service = AnalysisResultService(db)
    await analysis_service.delete_by_image_id(image_id)

    # Delete image
    success = await image_service.delete_image(image_id, current_user["user_id"])

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )


@router.post("/batch/delete", response_model=BatchDeleteResponse)
async def batch_delete(
    request: BatchDeleteRequest,
    current_user: ActiveUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BatchDeleteResponse:
    """
    Delete multiple images in batch.

    Args:
        request: Batch delete request with image IDs
        current_user: Current authenticated user
        db: Database session

    Returns:
        BatchDeleteResponse with batch deletion results
    """
    image_service = ImageService(db)
    analysis_service = AnalysisResultService(db)

    deleted = 0
    failed = 0
    errors: list[str] = []

    for image_id in request.image_ids:
        # Delete analysis results first
        await analysis_service.delete_by_image_id(image_id)

        # Delete image
        success = await image_service.delete_image(image_id, current_user["user_id"])
        if success:
            deleted += 1
        else:
            failed += 1
            errors.append(f"{image_id}: Image not found")

    # Build message
    message_parts = []
    if deleted > 0:
        message_parts.append(f"成功删除 {deleted} 个")
    if failed > 0:
        message_parts.append(f"失败 {failed} 个")
    message = "，".join(message_parts) if message_parts else "无图片删除"

    logger.info(
        f"Batch delete completed: total={len(request.image_ids)}, "
        f"deleted={deleted}, failed={failed}"
    )

    return BatchDeleteResponse(
        success=failed == 0,
        total=len(request.image_ids),
        deleted=deleted,
        failed=failed,
        errors=errors,
        message=message,
    )
