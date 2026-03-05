"""
Pytest configuration and fixtures

This module provides shared fixtures for all test modules:
- async_client: HTTP client for testing FastAPI endpoints
- event_loop: Async event loop for test execution
- test_settings: Test-specific configuration overrides
- clean_db: Database cleanup between tests

IMPORTANT: Environment must be set up before importing app modules.
"""
import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

# Set test environment BEFORE importing app modules
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-not-for-production-12345")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_app.db")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Create async HTTP client for testing.

    Uses ASGITransport to call the FastAPI app directly
    without running a server. This is faster and more
    reliable for testing.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture(scope="function")
def temp_upload_dir(tmp_path: Path) -> Path:
    """
    Create a temporary directory for test uploads.

    This fixture creates a unique temp directory for each test
    to ensure file operations don't interfere between tests.
    """
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Store original and override for test
    original = settings.UPLOAD_DIR
    settings.UPLOAD_DIR = str(upload_dir)

    yield upload_dir

    # Restore original
    settings.UPLOAD_DIR = original


@pytest.fixture(scope="function")
def test_db_path(tmp_path: Path) -> Path:
    """
    Create a temporary database file for testing.

    Each test gets its own database file to ensure isolation.
    """
    return tmp_path / "test.db"
