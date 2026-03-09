"""
Tests for /api/v1/ai/analyze endpoints.
"""
import json
import sys
import types
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, async_session_maker, engine
from app.core.security import create_access_token, hash_password
from app.models.ai_model import AIModel
from app.models.ai_prompt import AIPrompt, AIPromptVersion
from app.models.analysis_result import AnalysisResult
from app.models.image import Image
from app.models.user import User
from app.core.config import settings
from app.services.ai.models.qwen_vl import QwenVLAnalyzer
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
            "prompt": {
                "prompt_version_id": "prompt-version-1",
                "prompt_name": "Default Prompt",
                "prompt_version_number": 1,
            },
        }


@pytest.fixture
def reset_ai_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Ensure tests start with a clean in-memory AI model registry.
    """
    monkeypatch.setattr(AIModelRegistry, "_models", {})
    monkeypatch.setattr(AIModelRegistry, "_active_model", None)


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
    assert saved.prompt_version_id == "prompt-version-1"
    assert saved.prompt_name == "Default Prompt"
    assert saved.prompt_version_number == 1


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


@pytest.mark.asyncio
async def test_get_model_detail_masks_secret_config(
    async_client: AsyncClient,
    db_session: AsyncSession,
    reset_ai_registry: None,
) -> None:
    """
    GET /api/v1/ai/models/{model_name} should not expose the raw API key.
    """
    analyzer = QwenVLAnalyzer()
    await AIModelRegistry.register(analyzer)

    db_session.add(
        AIModel(
            name="qwen3-vl",
            description=analyzer.description,
            is_active=False,
            config_json=json.dumps(
                {
                    "api_key": "top-secret-key",
                    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "model_name": "qwen3-vl-plus",
                }
            ),
        )
    )
    await db_session.commit()

    response = await async_client.get("/api/v1/ai/models/qwen3-vl")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "qwen3-vl"
    assert payload["config"]["api_key"] == ""
    assert payload["config"]["base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert payload["config"]["model_name"] == "qwen3-vl-plus"
    assert payload["configured_secret_fields"] == ["api_key"]
    assert payload["configured"] is True


@pytest.mark.asyncio
async def test_update_model_config_preserves_existing_secret_when_blank(
    async_client: AsyncClient,
    db_session: AsyncSession,
    reset_ai_registry: None,
) -> None:
    """
    PUT /api/v1/ai/models/{model_name}/config should keep existing secret values
    when the client submits an empty string for a password field.
    """
    analyzer = QwenVLAnalyzer()
    await AIModelRegistry.register(analyzer)

    record = AIModel(
        name="qwen3-vl",
        description=analyzer.description,
        is_active=False,
        config_json=json.dumps(
            {
                "api_key": "persist-me",
                "base_url": "https://old.example.com/v1",
                "model_name": "old-model",
            }
        ),
    )
    db_session.add(record)
    await db_session.commit()

    response = await async_client.put(
        "/api/v1/ai/models/qwen3-vl/config",
        json={
            "config": {
                "api_key": "",
                "base_url": "https://new.example.com/v1",
                "model_name": "qwen3-vl-plus",
            }
        },
    )

    assert response.status_code == 200

    await db_session.refresh(record)
    saved_config = json.loads(record.config_json or "{}")
    assert saved_config["api_key"] == "persist-me"
    assert saved_config["base_url"] == "https://new.example.com/v1"
    assert saved_config["model_name"] == "qwen3-vl-plus"


@pytest.mark.asyncio
async def test_set_active_model_requires_qwen_configuration(
    async_client: AsyncClient,
    db_session: AsyncSession,
    reset_ai_registry: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    POST /api/v1/ai/models/active should reject Qwen3-VL when API credentials
    have not been configured yet.
    """
    monkeypatch.setattr(settings, "QWEN3_VL_API_KEY", None)
    monkeypatch.setattr(settings, "QWEN3_VL_BASE_URL", None)
    monkeypatch.setattr(settings, "QWEN3_VL_MODEL_NAME", None)

    analyzer = QwenVLAnalyzer()
    await AIModelRegistry.register(analyzer)

    db_session.add(
        AIModel(
            name="qwen3-vl",
            description=analyzer.description,
            is_active=False,
        )
    )
    await db_session.commit()

    response = await async_client.post(
        "/api/v1/ai/models/active",
        json={"model_name": "qwen3-vl"},
    )

    assert response.status_code == 400
    assert "not configured" in response.json()["detail"]


@pytest.mark.asyncio
async def test_set_active_model_activates_configured_qwen(
    async_client: AsyncClient,
    db_session: AsyncSession,
    reset_ai_registry: None,
) -> None:
    """
    POST /api/v1/ai/models/active should activate Qwen3-VL once its required
    runtime configuration has been saved.
    """
    analyzer = QwenVLAnalyzer()
    await AIModelRegistry.register(analyzer)

    db_session.add(
        AIModel(
            name="qwen3-vl",
            description=analyzer.description,
            is_active=False,
            config_json=json.dumps({"api_key": "configured-secret"}),
        )
    )
    await db_session.commit()

    response = await async_client.post(
        "/api/v1/ai/models/active",
        json={"model_name": "qwen3-vl"},
    )

    assert response.status_code == 200
    active_name = await AIModelRegistry.get_active_name()
    assert active_name == "qwen3-vl"


@pytest.mark.asyncio
async def test_get_model_detail_uses_env_defaults_for_qwen_configuration(
    async_client: AsyncClient,
    db_session: AsyncSession,
    reset_ai_registry: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    GET /api/v1/ai/models/{model_name} should reflect env-backed qwen defaults.
    """
    monkeypatch.setattr(settings, "QWEN3_VL_API_KEY", "env-secret")
    monkeypatch.setattr(settings, "QWEN3_VL_BASE_URL", "https://env.example.com/v1")
    monkeypatch.setattr(settings, "QWEN3_VL_MODEL_NAME", "qwen3-vl-max")

    analyzer = QwenVLAnalyzer()
    await AIModelRegistry.register(analyzer)

    db_session.add(
        AIModel(
            name="qwen3-vl",
            description=analyzer.description,
            is_active=False,
        )
    )
    await db_session.commit()

    response = await async_client.get("/api/v1/ai/models/qwen3-vl")

    assert response.status_code == 200
    payload = response.json()
    assert payload["configured"] is True
    assert payload["config"]["base_url"] == "https://env.example.com/v1"
    assert payload["config"]["model_name"] == "qwen3-vl-max"
    assert payload["configured_secret_fields"] == ["api_key"]


@pytest.mark.asyncio
async def test_qwen_analyzer_uses_active_prompt_version(
    db_session: AsyncSession,
    temp_upload_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Qwen analyzer should resolve prompts from the prompt store instead of using
    hard-coded prompt text.
    """
    image_path = temp_upload_dir / "prompted.jpg"
    image_path.write_bytes(b"fake-image-bytes")

    prompt = AIPrompt(
        id="prompt-1",
        model_name="qwen3-vl",
        name="Managed Prompt",
        description="Managed",
        is_active=True,
    )
    version = AIPromptVersion(
        id="prompt-version-1",
        prompt_id=prompt.id,
        version_number=1,
        system_prompt="Managed system prompt",
        user_prompt="Analyze {{image_name}} with {{model_name}} as {{mime_type}}",
        created_by="tester",
    )
    prompt.current_version_id = version.id
    db_session.add(prompt)
    db_session.add(version)
    await db_session.commit()

    captured: dict[str, object] = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured["messages"] = kwargs["messages"]
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=types.SimpleNamespace(content='{"score": 8.8, "summary": "ok"}'))],
                usage={"prompt_tokens": 12, "completion_tokens": 5, "total_tokens": 17},
                model="qwen3-vl-plus",
            )

    class FakeOpenAI:
        def __init__(self, api_key: str, base_url: str) -> None:
            captured["api_key"] = api_key
            captured["base_url"] = base_url
            self.chat = types.SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))

    analyzer = QwenVLAnalyzer()
    await analyzer.on_config_updated({"api_key": "runtime-secret"})
    assert await analyzer.load() is True

    result = await analyzer.analyze(str(image_path))

    assert result["score"] == 8.8
    assert result["prompt"]["prompt_version_id"] == "prompt-version-1"
    messages = captured["messages"]
    assert isinstance(messages, list)
    assert messages[0]["content"] == "Managed system prompt"
    user_parts = messages[1]["content"]
    assert user_parts[0]["text"] == "Analyze prompted.jpg with qwen3-vl-plus as image/jpeg"
