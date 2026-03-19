"""
Upload API endpoint
"""
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.upload import UploadResponse
from app.services.concurrent_upload import (
    ConcurrentUploadService,
    get_concurrent_upload_service,
)

router = APIRouter()


@router.post("", response_model=UploadResponse)
async def upload_images(
    _db: Annotated[AsyncSession, Depends(get_db)],
    images: Annotated[list[UploadFile], File(description="Image files to upload")] = [],
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
    return await upload_service.process_batch_upload(
        session_factory=get_db,
        files=images,
        hashes_json=hashes,
        auto_analyze=auto_analyze,
    )
