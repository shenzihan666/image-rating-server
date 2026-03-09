"""
Tests for lightweight database schema migrations.
"""

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

import app.models  # noqa: F401
from app.core.database import LATEST_SCHEMA_VERSION, Base, _apply_schema_migrations


async def _get_schema_version(conn) -> int:
    result = await conn.exec_driver_sql("SELECT version FROM schema_version WHERE id = 1")
    row = result.fetchone()
    assert row is not None
    return int(row[0])


@pytest.mark.asyncio
async def test_apply_schema_migrations_adds_images_hash_column(tmp_path) -> None:
    """
    Ensure legacy images table gets hash_sha256 column and index.
    """
    db_path = tmp_path / "legacy.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    async with engine.begin() as conn:
        # Simulate legacy schema without hash_sha256.
        await conn.exec_driver_sql(
            """
            CREATE TABLE images (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                file_path VARCHAR(500) NOT NULL,
                file_size INTEGER NOT NULL,
                width INTEGER,
                height INTEGER,
                mime_type VARCHAR(100) NOT NULL,
                average_rating FLOAT,
                rating_count INTEGER,
                created_at DATETIME,
                updated_at DATETIME
            )
            """
        )

        await _apply_schema_migrations(conn)

        cols_result = await conn.exec_driver_sql('PRAGMA table_info("images")')
        cols = [row[1] for row in cols_result.fetchall()]
        assert "hash_sha256" in cols

        idx_result = await conn.exec_driver_sql('PRAGMA index_list("images")')
        indexes = [row[1] for row in idx_result.fetchall()]
        assert "ix_images_hash_sha256" in indexes

        assert await _get_schema_version(conn) == LATEST_SCHEMA_VERSION

    await engine.dispose()


@pytest.mark.asyncio
async def test_apply_schema_migrations_adds_ai_models_config_column(tmp_path) -> None:
    """
    Ensure legacy ai_models table gets config_json column.
    """
    db_path = tmp_path / "legacy_ai_models.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    async with engine.begin() as conn:
        await conn.exec_driver_sql(
            """
            CREATE TABLE ai_models (
                id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME,
                updated_at DATETIME
            )
            """
        )

        await _apply_schema_migrations(conn)

        cols_result = await conn.exec_driver_sql('PRAGMA table_info("ai_models")')
        cols = [row[1] for row in cols_result.fetchall()]
        assert "config_json" in cols

        assert await _get_schema_version(conn) == LATEST_SCHEMA_VERSION

    await engine.dispose()


@pytest.mark.asyncio
async def test_apply_schema_migrations_marks_fresh_database_as_latest(tmp_path) -> None:
    """
    Ensure a fresh schema is marked with the latest version at startup.
    """
    db_path = tmp_path / "fresh.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _apply_schema_migrations(conn)

        assert await _get_schema_version(conn) == LATEST_SCHEMA_VERSION

    await engine.dispose()


@pytest.mark.asyncio
async def test_apply_schema_migrations_creates_ai_prompt_tables(tmp_path) -> None:
    """
    Ensure AI prompt tables and indexes are created for legacy databases.
    """
    db_path = tmp_path / "legacy_prompts.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    async with engine.begin() as conn:
        await _apply_schema_migrations(conn)

        tables_result = await conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('ai_prompts', 'ai_prompt_versions')"
        )
        tables = {row[0] for row in tables_result.fetchall()}
        assert tables == {"ai_prompts", "ai_prompt_versions"}

        idx_result = await conn.exec_driver_sql('PRAGMA index_list("ai_prompt_versions")')
        indexes = [row[1] for row in idx_result.fetchall()]
        assert "ix_ai_prompt_versions_prompt_id" in indexes

        assert await _get_schema_version(conn) == LATEST_SCHEMA_VERSION

    await engine.dispose()


@pytest.mark.asyncio
async def test_apply_schema_migrations_adds_prompt_metadata_to_analysis_results(tmp_path) -> None:
    """
    Ensure legacy analysis_results table gets prompt tracking columns.
    """
    db_path = tmp_path / "legacy_analysis_results.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    async with engine.begin() as conn:
        await conn.exec_driver_sql(
            """
            CREATE TABLE analysis_results (
                id VARCHAR(36) PRIMARY KEY,
                image_id VARCHAR(36) NOT NULL,
                model VARCHAR(100) NOT NULL,
                score FLOAT,
                min_score FLOAT,
                max_score FLOAT,
                distribution TEXT,
                details TEXT,
                created_at DATETIME
            )
            """
        )

        await _apply_schema_migrations(conn)

        cols_result = await conn.exec_driver_sql('PRAGMA table_info("analysis_results")')
        cols = [row[1] for row in cols_result.fetchall()]
        assert "prompt_version_id" in cols
        assert "prompt_name" in cols
        assert "prompt_version_number" in cols

        assert await _get_schema_version(conn) == LATEST_SCHEMA_VERSION

    await engine.dispose()
