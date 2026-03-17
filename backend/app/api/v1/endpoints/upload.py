"""
Upload API endpoint
"""
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OptionalUser, get_db
from app.models.user import User
from app.schemas.upload import UploadResponse
from app.services.concurrent_upload import (
    ConcurrentUploadService,
    get_concurrent_upload_service,
)

router = APIRouter()


async def resolve_upload_user_id(
    db: AsyncSession,
    current_user: dict | None,
) -> str:
    """Resolve a valid owner user for uploads when auth is omitted."""
    if current_user and current_user.get("user_id"):
        return current_user["user_id"]

    demo_user = await db.execute(
        select(User.id).where(
            User.email == "demo@example.com",
            User.is_active.is_(True),
        )
    )
    demo_user_id = demo_user.scalars().first()
    if demo_user_id:
        return demo_user_id

    result = await db.execute(
        select(User.id)
        .where(User.is_active.is_(True))
        .order_by(User.created_at)
    )
    fallback_user_id = result.scalars().first()
    if fallback_user_id:
        return fallback_user_id

    raise HTTPException(
        status_code=500,
        detail="No active user available for upload ownership",
    )


@router.post("", response_model=UploadResponse)
async def upload_images(
    current_user: OptionalUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    images: Annotated[list[UploadFile], File(description="Image files to upload")],
    hashes: Annotated[str | None, Form(description="JSON array of SHA256 hashes")] = None,
    auto_analyze: Annotated[
        bool,
        Form(
            description=(
                "If true, newly uploaded images are automatically analyzed "
                "by the active AI model immediately after upload. "
                "Analysis failures do not affect upload success status."
            )
        ),
    ] = False,
    upload_service: ConcurrentUploadService = Depends(get_concurrent_upload_service),
) -> UploadResponse:
    """
    Upload multiple images with hash verification.

    This endpoint accepts multiple image files along with their SHA256 hashes
    for verification and deduplication purposes.

    - **images**: List of image files (max 10 per request)
    - **hashes**: JSON array of SHA256 hashes corresponding to each image
                 (e.g., '["abc123...", "def456..."]')
    - **auto_analyze**: If true, trigger AI analysis automatically for each
                        newly uploaded image (not duplicates). Requires an
                        active model to be configured.

    Returns a summary of the upload operation including:
    - Number of successful uploads
    - Number of duplicated files (already in system)
    - Number of failed uploads
    - Detailed results for each file
    """
    user_id = await resolve_upload_user_id(db, current_user)

    # Pass get_db as session factory - each concurrent upload task
    # will create its own session to avoid race conditions
    return await upload_service.process_batch_upload(
        session_factory=get_db,
        files=images,
        hashes_json=hashes,
        user_id=user_id,
        auto_analyze=auto_analyze,
    )
