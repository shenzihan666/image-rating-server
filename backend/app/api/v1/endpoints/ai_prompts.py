"""
AI prompt management endpoints.
"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.ai import (
    AIPromptDetail,
    AIPromptSummary,
    AIPromptVersionDetail,
    AIPromptVersionSummary,
    CreateAIPromptRequest,
    CreateAIPromptVersionRequest,
    UpdateAIPromptRequest,
)
from app.services.ai.prompt_store import (
    create_prompt,
    create_prompt_version,
    delete_prompt,
    get_prompt,
    get_prompt_version,
    list_prompt_versions,
    list_prompts,
    update_prompt,
)

router = APIRouter()


@router.get("/prompts", response_model=list[AIPromptSummary])
async def list_ai_prompts(
    db: Annotated[AsyncSession, Depends(get_db)],
    model_name: str | None = Query(None),
) -> list[AIPromptSummary]:
    prompts = await list_prompts(db, model_name=model_name)
    return [AIPromptSummary(**prompt) for prompt in prompts]


@router.post(
    "/prompts",
    response_model=AIPromptDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_ai_prompt(
    request: CreateAIPromptRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIPromptDetail:
    prompt = await create_prompt(
        db,
        model_name=request.model_name,
        name=request.name,
        description=request.description,
        system_prompt=request.system_prompt,
        user_prompt=request.user_prompt,
        commit_message=request.commit_message,
        created_by=request.created_by,
        is_active=request.is_active,
    )
    if prompt is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create prompt",
        )
    return AIPromptDetail(**prompt)


@router.get("/prompts/{prompt_id}", response_model=AIPromptDetail)
async def get_ai_prompt(
    prompt_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIPromptDetail:
    prompt = await get_prompt(db, prompt_id)
    if prompt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt not found: {prompt_id}",
        )
    return AIPromptDetail(**prompt)


@router.patch("/prompts/{prompt_id}", response_model=AIPromptDetail)
async def update_ai_prompt(
    prompt_id: str,
    request: UpdateAIPromptRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIPromptDetail:
    prompt = await update_prompt(
        db,
        prompt_id,
        request.model_dump(exclude_unset=True),
    )
    if prompt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt not found: {prompt_id}",
        )
    return AIPromptDetail(**prompt)


@router.delete("/prompts/{prompt_id}")
async def delete_ai_prompt(
    prompt_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    deleted = await delete_prompt(db, prompt_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt not found: {prompt_id}",
        )
    return {"deleted": True, "prompt_id": prompt_id}


@router.get(
    "/prompts/{prompt_id}/versions",
    response_model=list[AIPromptVersionSummary],
)
async def list_ai_prompt_versions(
    prompt_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AIPromptVersionSummary]:
    versions = await list_prompt_versions(db, prompt_id)
    return [AIPromptVersionSummary(**version) for version in versions]


@router.post(
    "/prompts/{prompt_id}/versions",
    response_model=AIPromptVersionDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_ai_prompt_version(
    prompt_id: str,
    request: CreateAIPromptVersionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIPromptVersionDetail:
    version = await create_prompt_version(
        db,
        prompt_id,
        system_prompt=request.system_prompt,
        user_prompt=request.user_prompt,
        commit_message=request.commit_message,
        created_by=request.created_by,
    )
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt not found: {prompt_id}",
        )
    return AIPromptVersionDetail(**version)


@router.get(
    "/prompts/{prompt_id}/versions/{version_id}",
    response_model=AIPromptVersionDetail,
)
async def get_ai_prompt_version(
    prompt_id: str,
    version_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIPromptVersionDetail:
    version = await get_prompt_version(db, prompt_id, version_id)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt version not found: {version_id}",
        )
    return AIPromptVersionDetail(**version)
