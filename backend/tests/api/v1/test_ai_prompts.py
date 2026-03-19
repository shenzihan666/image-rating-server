"""
Tests for qwen3-vl prompt management endpoints.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, async_session_maker, engine


@pytest.fixture(scope="function")
async def db_session() -> AsyncSession:
    """Create a clean database session for prompt API tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.mark.asyncio
async def test_create_prompt_creates_initial_version(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """POST /api/v1/ai/prompts should create v1 immediately."""
    response = await async_client.post(
        "/api/v1/ai/prompts",
        json={
            "model_name": "qwen3-vl",
            "name": "Editorial Scoring",
            "description": "Main production prompt",
            "system_prompt": "System prompt",
            "user_prompt": "Analyze {{image_name}}",
            "commit_message": "Initial",
            "created_by": "tester",
            "is_active": True,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "Editorial Scoring"
    assert payload["current_version"]["version_number"] == 1
    assert payload["current_version"]["system_prompt"] == "System prompt"
    assert payload["current_version"]["user_prompt"] == "Analyze {{image_name}}"


@pytest.mark.asyncio
async def test_create_prompt_version_updates_current_version(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """POST /versions should increment version number and mark it current."""
    create_response = await async_client.post(
        "/api/v1/ai/prompts",
        json={
            "model_name": "qwen3-vl",
            "name": "Versioned Prompt",
            "system_prompt": "v1 system",
            "user_prompt": "v1 user",
            "commit_message": "Initial",
            "is_active": True,
        },
    )
    prompt_id = create_response.json()["id"]

    version_response = await async_client.post(
        f"/api/v1/ai/prompts/{prompt_id}/versions",
        json={
            "system_prompt": "v2 system",
            "user_prompt": "v2 user",
            "commit_message": "Refine tone",
            "created_by": "tester",
        },
    )

    assert version_response.status_code == 201
    assert version_response.json()["version_number"] == 2

    prompt_response = await async_client.get(f"/api/v1/ai/prompts/{prompt_id}")
    assert prompt_response.status_code == 200
    assert prompt_response.json()["current_version_number"] == 2
    assert prompt_response.json()["current_version"]["system_prompt"] == "v2 system"


@pytest.mark.asyncio
async def test_activating_prompt_deactivates_previous_prompt(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """Activating one prompt should deactivate other prompts for the model."""
    first = await async_client.post(
        "/api/v1/ai/prompts",
        json={
            "model_name": "qwen3-vl",
            "name": "Primary",
            "system_prompt": "first",
            "user_prompt": "first",
            "is_active": True,
        },
    )
    second = await async_client.post(
        "/api/v1/ai/prompts",
        json={
            "model_name": "qwen3-vl",
            "name": "Secondary",
            "system_prompt": "second",
            "user_prompt": "second",
            "is_active": False,
        },
    )

    second_id = second.json()["id"]
    activate_response = await async_client.patch(
        f"/api/v1/ai/prompts/{second_id}",
        json={"is_active": True},
    )

    assert activate_response.status_code == 200
    prompts_response = await async_client.get("/api/v1/ai/prompts?model_name=qwen3-vl")
    prompts = prompts_response.json()
    active_names = [prompt["name"] for prompt in prompts if prompt["is_active"]]
    assert active_names == ["Secondary"]

