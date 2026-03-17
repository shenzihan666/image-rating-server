"""
Tests for upload endpoint with auto_analyze parameter.

Covers:
- Upload without auto_analyze (original behaviour unchanged)
- Upload with auto_analyze=false (explicit opt-out)
- Upload with auto_analyze=true but no active model (should still succeed)
- Upload with auto_analyze=true and an active FakeAnalyzer (triggers analysis)
- auto_analyze only runs for newly uploaded files, not duplicates
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import Base, async_session_maker, engine
from app.core.security import create_access_token
from app.models.analysis_result import AnalysisResult
from app.models.image import Image
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers / shared bytes
# ---------------------------------------------------------------------------

_MINIMAL_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00H\x00H\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82"
    b"<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff"
    b"\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n"
    b"\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xf5\x14P\x00\xff\xd9"
)


def _unique_jpeg(tag: str) -> bytes:
    """Return a slightly different JPEG bytes so each has a unique hash."""
    return _MINIMAL_JPEG + tag.encode("utf-8")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_maker() as session:
        yield session
        await session.rollback()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    from app.core.security import hash_password

    user = User(
        id="aa-test-user",
        email="aa@example.com",
        full_name="AA Test User",
        hashed_password=hash_password("password"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    token = create_access_token(data={"sub": test_user.id, "email": test_user.email})
    return {"Authorization": f"Bearer {token}"}


# Monkeypatch upload dir so tests don't pollute the real filesystem.
# We must also patch the FileStorageService singleton because it captures
# upload_dir at initialisation time (before monkeypatch runs).
@pytest.fixture(autouse=True)
def patch_upload_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.storage import get_storage_service

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    temp_dir = upload_dir / "temp"
    temp_dir.mkdir()

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))

    # Patch the live singleton instance so atomic writes land in the temp dir
    storage = get_storage_service()
    monkeypatch.setattr(storage, "upload_dir", upload_dir)
    monkeypatch.setattr(storage, "temp_dir", temp_dir)


# ---------------------------------------------------------------------------
# Fake model helper
# ---------------------------------------------------------------------------


class _FakeAnalyzer:
    """Minimal analyzer stub that returns a fixed analysis payload."""

    name = "fake-model"
    description = "Fake model for tests"

    def is_loaded(self) -> bool:
        return True

    async def load(self) -> bool:
        return True

    async def unload(self) -> None:
        pass

    async def analyze(self, image_path: str) -> dict[str, Any]:
        return {
            "score": 7.5,
            "distribution": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "result": {"decision": "pass"},
        }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAutoAnalyzeFlag:
    """Upload with and without auto_analyze."""

    @pytest.mark.asyncio
    async def test_upload_without_auto_analyze_succeeds(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Baseline: no auto_analyze param → upload still works."""
        files = {"images": ("img.jpg", _unique_jpeg("no_aa"), "image/jpeg")}
        resp = await async_client.post("/api/v1/upload", files=files, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["succeeded"] == 1

    @pytest.mark.asyncio
    async def test_upload_with_auto_analyze_false_succeeds(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Explicit auto_analyze=false → same as default."""
        files = {"images": ("img.jpg", _unique_jpeg("aa_false"), "image/jpeg")}
        data = {"auto_analyze": "false"}
        resp = await async_client.post(
            "/api/v1/upload", files=files, data=data, headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["succeeded"] == 1

    @pytest.mark.asyncio
    async def test_upload_with_auto_analyze_true_no_model_still_succeeds(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """auto_analyze=true but no active model → upload succeeds, analysis skipped."""
        with patch(
            "app.services.auto_analyze.AIModelRegistry.get_active",
            new=AsyncMock(return_value=None),
        ):
            files = {"images": ("img.jpg", _unique_jpeg("aa_no_model"), "image/jpeg")}
            data = {"auto_analyze": "true"}
            resp = await async_client.post(
                "/api/v1/upload", files=files, data=data, headers=auth_headers
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["succeeded"] == 1

    @pytest.mark.asyncio
    async def test_upload_with_auto_analyze_true_and_active_model_saves_result(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        db_session: AsyncSession,
    ) -> None:
        """auto_analyze=true with active model → analysis result saved in DB."""
        fake_model = _FakeAnalyzer()

        with patch(
            "app.services.auto_analyze.AIModelRegistry.get_active",
            new=AsyncMock(return_value=fake_model),
        ):
            files = {"images": ("img.jpg", _unique_jpeg("aa_with_model"), "image/jpeg")}
            data = {"auto_analyze": "true"}
            resp = await async_client.post(
                "/api/v1/upload", files=files, data=data, headers=auth_headers
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["succeeded"] == 1

        image_id = body["results"][0]["metadata"]["image_id"]

        # Give the async analyze task a moment to commit
        import asyncio
        await asyncio.sleep(0.1)

        result = await db_session.execute(
            select(AnalysisResult).where(AnalysisResult.image_id == image_id)
        )
        record = result.scalar_one_or_none()
        assert record is not None, "AnalysisResult should be persisted after auto_analyze"
        assert record.score == 7.5
        assert record.model == "fake-model"

    @pytest.mark.asyncio
    async def test_auto_analyze_skips_duplicates(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        db_session: AsyncSession,
    ) -> None:
        """auto_analyze=true should NOT trigger analysis for duplicate uploads."""
        fake_model = _FakeAnalyzer()
        img_bytes = _unique_jpeg("dup_test")

        # First upload — succeeds and triggers analysis
        with patch(
            "app.services.auto_analyze.AIModelRegistry.get_active",
            new=AsyncMock(return_value=fake_model),
        ):
            files = {"images": ("img.jpg", img_bytes, "image/jpeg")}
            data = {"auto_analyze": "true"}
            resp1 = await async_client.post(
                "/api/v1/upload", files=files, data=data, headers=auth_headers
            )
        assert resp1.json()["succeeded"] == 1

        import asyncio
        await asyncio.sleep(0.1)

        # Count analysis results after first upload
        r1 = await db_session.execute(select(AnalysisResult))
        count_after_first = len(r1.scalars().all())

        # Second upload of same image — should be detected as duplicate
        with patch(
            "app.services.auto_analyze.AIModelRegistry.get_active",
            new=AsyncMock(return_value=fake_model),
        ):
            files = {"images": ("img.jpg", img_bytes, "image/jpeg")}
            data = {"auto_analyze": "true"}
            resp2 = await async_client.post(
                "/api/v1/upload", files=files, data=data, headers=auth_headers
            )
        assert resp2.json()["duplicated"] == 1

        await asyncio.sleep(0.1)

        r2 = await db_session.execute(select(AnalysisResult))
        count_after_second = len(r2.scalars().all())

        # No new analysis results should have been created for the duplicate
        assert count_after_second == count_after_first


class TestAutoAnalyzeUploadClientStandalone:
    """Unit tests for the wecom-side image_review_client (no network)."""

    @pytest.mark.asyncio
    async def test_upload_skipped_when_no_server_url(self, tmp_path: Path) -> None:
        """Client returns False immediately when server URL is empty."""
        import sys
        import importlib

        # Ensure the module loads cleanly without a real settings backend
        if "services.image_review_client" in sys.modules:
            del sys.modules["services.image_review_client"]

        # We test the module logic by calling it with an explicit empty server_url
        # (bypasses settings lookup)
        img = tmp_path / "test.jpg"
        img.write_bytes(_MINIMAL_JPEG)

        # Dynamically load the module from the wecom backend path so we don't
        # need the full wecom package installed in this test environment.
        import importlib.util
        client_path = Path(
            r"d:\Project\welike\android_run_test-backup\wecom-desktop\backend"
            r"\services\image_review_client.py"
        )
        spec = importlib.util.spec_from_file_location("image_review_client", client_path)
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]

        result = await mod.upload_image_for_review(img, server_url="")
        assert result is False

    @pytest.mark.asyncio
    async def test_upload_skipped_for_missing_file(self, tmp_path: Path) -> None:
        """Client returns False when the file does not exist."""
        import importlib.util

        client_path = Path(
            r"d:\Project\welike\android_run_test-backup\wecom-desktop\backend"
            r"\services\image_review_client.py"
        )
        spec = importlib.util.spec_from_file_location("image_review_client", client_path)
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]

        result = await mod.upload_image_for_review(
            tmp_path / "nonexistent.jpg",
            server_url="http://fake-server:8000",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_upload_sends_correct_multipart_and_returns_true(
        self, tmp_path: Path
    ) -> None:
        """Client sends multipart request and returns True on HTTP 200."""
        import importlib.util
        from unittest.mock import AsyncMock, MagicMock

        img = tmp_path / "test.jpg"
        img.write_bytes(_MINIMAL_JPEG)

        client_path = Path(
            r"d:\Project\welike\android_run_test-backup\wecom-desktop\backend"
            r"\services\image_review_client.py"
        )
        spec = importlib.util.spec_from_file_location("image_review_client", client_path)
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]

        # Build a mock httpx response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"succeeded": 1, "total": 1, "failed": 0}

        # Mock the async context manager returned by httpx.AsyncClient
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_async_cm = AsyncMock()
        mock_async_cm.__aenter__ = AsyncMock(return_value=mock_client)
        mock_async_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_async_cm):
            result = await mod.upload_image_for_review(
                img,
                server_url="http://fake-server:8000",
                token="test-token",
                auto_analyze=True,
            )

        assert result is True

        # Verify post was called with the right URL
        call_kwargs = mock_client.post.call_args
        assert call_kwargs is not None
        url = call_kwargs.args[0] if call_kwargs.args else call_kwargs.kwargs.get("url")
        assert url == "http://fake-server:8000/api/v1/upload"

        # Verify auto_analyze was set to 'true'
        sent_data = call_kwargs.kwargs.get("data", {})
        assert sent_data.get("auto_analyze") == "true"

    @pytest.mark.asyncio
    async def test_upload_returns_false_on_http_error(self, tmp_path: Path) -> None:
        """Client returns False when server returns non-200."""
        import importlib.util
        from unittest.mock import AsyncMock, MagicMock

        img = tmp_path / "test.jpg"
        img.write_bytes(_MINIMAL_JPEG)

        client_path = Path(
            r"d:\Project\welike\android_run_test-backup\wecom-desktop\backend"
            r"\services\image_review_client.py"
        )
        spec = importlib.util.spec_from_file_location("image_review_client", client_path)
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_async_cm = AsyncMock()
        mock_async_cm.__aenter__ = AsyncMock(return_value=mock_client)
        mock_async_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_async_cm):
            result = await mod.upload_image_for_review(
                img,
                server_url="http://fake-server:8000",
                token="bad-token",
            )

        assert result is False
