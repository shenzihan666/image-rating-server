"""
Tests for lightweight database schema migrations.
"""

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.database import _apply_schema_migrations


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

    await engine.dispose()
