"""
Persistence helpers for versioned AI prompts.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_prompt import AIPrompt, AIPromptVersion

QWEN3_VL_PROMPT_NAME = "Default Image Analysis Prompt"
DEFAULT_QWEN_SYSTEM_PROMPT = (
    "You are a professional image analysis assistant. "
    "Always return valid JSON only, with no markdown fences or extra commentary."
)
DEFAULT_QWEN_USER_PROMPT = (
    "Analyze the provided image carefully.\n"
    "Use this context when helpful:\n"
    "- image_name: {{image_name}}\n"
    "- mime_type: {{mime_type}}\n"
    "- model_name: {{model_name}}\n\n"
    "Return a JSON object with these keys when they can be inferred:\n"
    "- score: numeric overall score\n"
    "- summary: concise summary\n"
    "- strengths: array of strings\n"
    "- weaknesses: array of strings\n"
    "- tags: array of strings"
)


@dataclass(frozen=True)
class ActivePromptVersion:
    """Resolved prompt version payload used by runtime analyzers."""

    prompt_id: str
    prompt_name: str
    prompt_description: str | None
    prompt_version_id: str
    prompt_version_number: int
    system_prompt: str
    user_prompt: str


def _isoformat(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat()


def _serialize_version(version: AIPromptVersion) -> dict[str, Any]:
    return {
        "id": version.id,
        "prompt_id": version.prompt_id,
        "version_number": version.version_number,
        "system_prompt": version.system_prompt,
        "user_prompt": version.user_prompt,
        "commit_message": version.commit_message,
        "created_by": version.created_by,
        "created_at": _isoformat(version.created_at),
    }


def _serialize_prompt(
    prompt: AIPrompt,
    current_version: AIPromptVersion | None,
) -> dict[str, Any]:
    return {
        "id": prompt.id,
        "model_name": prompt.model_name,
        "name": prompt.name,
        "description": prompt.description,
        "is_active": prompt.is_active,
        "current_version_id": current_version.id if current_version else prompt.current_version_id,
        "current_version_number": current_version.version_number if current_version else None,
        "created_at": _isoformat(prompt.created_at),
        "updated_at": _isoformat(prompt.updated_at),
        "current_version": _serialize_version(current_version) if current_version else None,
    }


async def _get_current_version(
    db: AsyncSession,
    prompt: AIPrompt,
) -> AIPromptVersion | None:
    if prompt.current_version_id:
        result = await db.execute(
            select(AIPromptVersion).where(AIPromptVersion.id == prompt.current_version_id)
        )
        version = result.scalar_one_or_none()
        if version is not None:
            return version

    result = await db.execute(
        select(AIPromptVersion)
        .where(AIPromptVersion.prompt_id == prompt.id)
        .order_by(AIPromptVersion.version_number.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _deactivate_other_prompts(
    db: AsyncSession,
    model_name: str,
    active_prompt_id: str,
) -> None:
    await db.execute(
        update(AIPrompt)
        .where(
            AIPrompt.model_name == model_name,
            AIPrompt.id != active_prompt_id,
            AIPrompt.is_active.is_(True),
        )
        .values(is_active=False)
    )


async def ensure_default_prompts(db: AsyncSession) -> None:
    """Seed default prompt records required by the runtime."""
    existing = await get_active_prompt_version(db, "qwen3-vl")
    if existing is not None:
        return

    prompt_result = await db.execute(
        select(AIPrompt)
        .where(AIPrompt.model_name == "qwen3-vl")
        .order_by(AIPrompt.created_at.asc())
        .limit(1)
    )
    prompt = prompt_result.scalar_one_or_none()
    if prompt is None:
        created = await create_prompt(
            db,
            model_name="qwen3-vl",
            name=QWEN3_VL_PROMPT_NAME,
            description="Default managed prompt for Qwen3-VL image analysis",
            system_prompt=DEFAULT_QWEN_SYSTEM_PROMPT,
            user_prompt=DEFAULT_QWEN_USER_PROMPT,
            commit_message="Initial default prompt",
            created_by="system",
            is_active=True,
        )
        if created is not None:
            return

    if prompt is None:
        return

    versions = await list_prompt_versions(db, prompt.id)
    if not versions:
        await create_prompt_version(
            db,
            prompt.id,
            system_prompt=DEFAULT_QWEN_SYSTEM_PROMPT,
            user_prompt=DEFAULT_QWEN_USER_PROMPT,
            commit_message="Initial default prompt",
            created_by="system",
        )
        prompt.is_active = True
        await db.commit()
        await db.refresh(prompt)

    if not prompt.is_active:
        prompt.is_active = True
        await db.commit()
        await db.refresh(prompt)
    await _deactivate_other_prompts(db, prompt.model_name, prompt.id)
    await db.commit()


async def list_prompts(
    db: AsyncSession,
    model_name: str | None = None,
) -> list[dict[str, Any]]:
    """List prompts for a model."""
    stmt: Select[tuple[AIPrompt]] = select(AIPrompt).order_by(
        AIPrompt.updated_at.desc(),
        AIPrompt.created_at.desc(),
    )
    if model_name:
        stmt = stmt.where(AIPrompt.model_name == model_name)

    result = await db.execute(stmt)
    prompts = result.scalars().all()
    payloads: list[dict[str, Any]] = []
    for prompt in prompts:
        current_version = await _get_current_version(db, prompt)
        payloads.append(_serialize_prompt(prompt, current_version))
    return payloads


async def get_prompt(
    db: AsyncSession,
    prompt_id: str,
) -> dict[str, Any] | None:
    """Fetch a prompt and its current version."""
    result = await db.execute(select(AIPrompt).where(AIPrompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if prompt is None:
        return None

    current_version = await _get_current_version(db, prompt)
    return _serialize_prompt(prompt, current_version)


async def create_prompt(
    db: AsyncSession,
    *,
    model_name: str,
    name: str,
    description: str | None,
    system_prompt: str,
    user_prompt: str,
    commit_message: str | None,
    created_by: str | None,
    is_active: bool,
) -> dict[str, Any] | None:
    """Create a prompt and its initial version."""
    prompt = AIPrompt(
        model_name=model_name,
        name=name.strip(),
        description=description.strip() if isinstance(description, str) and description.strip() else None,
        is_active=is_active,
    )
    db.add(prompt)
    await db.flush()

    version = AIPromptVersion(
        prompt_id=prompt.id,
        version_number=1,
        system_prompt=system_prompt.strip(),
        user_prompt=user_prompt.strip(),
        commit_message=commit_message.strip() if isinstance(commit_message, str) and commit_message.strip() else None,
        created_by=created_by.strip() if isinstance(created_by, str) and created_by.strip() else None,
    )
    db.add(version)
    await db.flush()

    prompt.current_version_id = version.id
    if prompt.is_active:
        await _deactivate_other_prompts(db, prompt.model_name, prompt.id)

    await db.commit()
    await db.refresh(prompt)
    await db.refresh(version)
    return _serialize_prompt(prompt, version)


async def update_prompt(
    db: AsyncSession,
    prompt_id: str,
    updates: dict[str, Any],
) -> dict[str, Any] | None:
    """Update prompt metadata."""
    result = await db.execute(select(AIPrompt).where(AIPrompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if prompt is None:
        return None

    if "name" in updates and updates["name"] is not None:
        prompt.name = str(updates["name"]).strip()

    if "description" in updates:
        description = updates["description"]
        prompt.description = (
            str(description).strip()
            if isinstance(description, str) and description.strip()
            else None
        )

    if "is_active" in updates and updates["is_active"] is not None:
        prompt.is_active = bool(updates["is_active"])
        if prompt.is_active:
            await _deactivate_other_prompts(db, prompt.model_name, prompt.id)

    await db.commit()
    await db.refresh(prompt)
    current_version = await _get_current_version(db, prompt)
    return _serialize_prompt(prompt, current_version)


async def delete_prompt(db: AsyncSession, prompt_id: str) -> bool:
    """Delete a prompt and keep one prompt active when possible."""
    result = await db.execute(select(AIPrompt).where(AIPrompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if prompt is None:
        return False

    model_name = prompt.model_name
    was_active = prompt.is_active
    await db.delete(prompt)
    await db.commit()

    if was_active:
        replacement_result = await db.execute(
            select(AIPrompt)
            .where(AIPrompt.model_name == model_name)
            .order_by(AIPrompt.updated_at.desc(), AIPrompt.created_at.desc())
            .limit(1)
        )
        replacement = replacement_result.scalar_one_or_none()
        if replacement is not None:
            replacement.is_active = True
            await _deactivate_other_prompts(db, replacement.model_name, replacement.id)
            await db.commit()
        elif model_name == "qwen3-vl":
            await ensure_default_prompts(db)

    return True


async def list_prompt_versions(
    db: AsyncSession,
    prompt_id: str,
) -> list[dict[str, Any]]:
    """List versions for a prompt."""
    result = await db.execute(
        select(AIPromptVersion)
        .where(AIPromptVersion.prompt_id == prompt_id)
        .order_by(AIPromptVersion.version_number.desc())
    )
    return [_serialize_version(version) for version in result.scalars().all()]


async def get_prompt_version(
    db: AsyncSession,
    prompt_id: str,
    version_id: str,
) -> dict[str, Any] | None:
    """Fetch a specific version."""
    result = await db.execute(
        select(AIPromptVersion).where(
            AIPromptVersion.prompt_id == prompt_id,
            AIPromptVersion.id == version_id,
        )
    )
    version = result.scalar_one_or_none()
    if version is None:
        return None
    return _serialize_version(version)


async def create_prompt_version(
    db: AsyncSession,
    prompt_id: str,
    *,
    system_prompt: str,
    user_prompt: str,
    commit_message: str | None,
    created_by: str | None,
) -> dict[str, Any] | None:
    """Create a new version and mark it current."""
    result = await db.execute(select(AIPrompt).where(AIPrompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if prompt is None:
        return None

    version_count_result = await db.execute(
        select(func.max(AIPromptVersion.version_number)).where(
            AIPromptVersion.prompt_id == prompt_id
        )
    )
    next_version = (version_count_result.scalar_one_or_none() or 0) + 1
    version = AIPromptVersion(
        prompt_id=prompt_id,
        version_number=next_version,
        system_prompt=system_prompt.strip(),
        user_prompt=user_prompt.strip(),
        commit_message=commit_message.strip() if isinstance(commit_message, str) and commit_message.strip() else None,
        created_by=created_by.strip() if isinstance(created_by, str) and created_by.strip() else None,
    )
    db.add(version)
    await db.flush()

    prompt.current_version_id = version.id
    await db.commit()
    await db.refresh(version)
    return _serialize_version(version)


async def get_active_prompt_version(
    db: AsyncSession,
    model_name: str,
) -> ActivePromptVersion | None:
    """Resolve the active prompt version for a model."""
    result = await db.execute(
        select(AIPrompt)
        .where(AIPrompt.model_name == model_name, AIPrompt.is_active.is_(True))
        .order_by(AIPrompt.updated_at.desc(), AIPrompt.created_at.desc())
        .limit(1)
    )
    prompt = result.scalar_one_or_none()
    if prompt is None:
        return None

    current_version = await _get_current_version(db, prompt)
    if current_version is None:
        return None

    return ActivePromptVersion(
        prompt_id=prompt.id,
        prompt_name=prompt.name,
        prompt_description=prompt.description,
        prompt_version_id=current_version.id,
        prompt_version_number=current_version.version_number,
        system_prompt=current_version.system_prompt,
        user_prompt=current_version.user_prompt,
    )
