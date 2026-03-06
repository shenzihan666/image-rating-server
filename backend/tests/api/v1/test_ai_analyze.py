"""
Tests for /api/v1/ai/analyze endpoints.
"""
from pathlib import Path
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, async_session_maker, engine
from app.core.security import create_access_token, hash_password
from app.models.analysis_result import AnalysisResult
from app.models.image import Image
from app.models.user import User
from app.services.ai.registry import AIModelRegistry


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a clean database session for each test function.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """
    Create and return a test user.
    """
    user = User(
        id="ai-test-user-id",
        email="ai-test@example.com",
        full_name="AI Test User",
        hashed_password=hash_password("testpassword123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    """
    Generate authentication headers for a test user.
    """
    token = create_access_token(data={"sub": test_user.id, "email": test_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def test_image(
    db_session: AsyncSession,
    test_user: User,
    temp_upload_dir: Path,
) -> Image:
    """
    Create a test image record and backing file.
    """
    image_path = temp_upload_dir / "sample.jpg"
    image_path.write_bytes(b"fake-image-bytes")

    image = Image(
        id="ai-test-image-id",
        user_id=test_user.id,
        title="Sample",
        description="Sample image",
        file_path="sample.jpg",
        file_size=image_path.stat().st_size,
        width=100,
        height=100,
        mime_type="image/jpeg",
        hash_sha256="abc123",
    )
    db_session.add(image)
    await db_session.commit()
    await db_session.refresh(image)
    return image


class FakeAnalyzer:
    """
    Minimal fake analyzer used for endpoint tests.
    """

    name = "fake-model"

    async def analyze(self, image_path: str) -> dict:
        return {
            "score": 7.5,
            "distribution": [1.0, 7.5, 10.0],
            "label": "good",
            "image_path": image_path,
        }


@pytest.mark.asyncio
async def test_analyze_image_saves_result_without_signature_error(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
    test_image: Image,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    POST /api/v1/ai/analyze/{image_id} should save the result and return 200.
    """

    async def fake_get_active() -> FakeAnalyzer:
        return FakeAnalyzer()

    monkeypatch.setattr(AIModelRegistry, "get_active", fake_get_active)

    response = await async_client.post(
        f"/api/v1/ai/analyze/{test_image.id}",
        headers=auth_headers,
        json={"force_new": True},
    )

    assert response.status_code == 200
    assert response.json()["image_id"] == test_image.id
    assert response.json()["model"] == "fake-model"
    assert response.json()["score"] == 7.5

    result = await db_session.execute(
        select(AnalysisResult).where(AnalysisResult.image_id == test_image.id)
    )
    saved = result.scalar_one_or_none()
    assert saved is not None
    assert saved.model == "fake-model"
    assert saved.score == 7.5


@pytest.mark.asyncio
async def test_batch_analyze_route_is_not_captured_by_single_image_route(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    POST /api/v1/ai/analyze/batch should resolve to the batch endpoint.

    When the batch endpoint handles the request and no active model exists, it
    returns a batch-specific 400 error. If the dynamic single-image route captures
    the path instead, the response would be 404 "Image not found".
    """

    async def fake_get_active() -> None:
        return None

    monkeypatch.setattr(AIModelRegistry, "get_active", fake_get_active)

    response = await async_client.post(
        "/api/v1/ai/analyze/batch",
        headers=auth_headers,
        json={"image_ids": ["img-1", "img-2"], "force_new": False},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "No active AI model. Please activate a model first."
