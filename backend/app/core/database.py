"""
Database configuration and session management
"""
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass

from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Create async engine for SQLite
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    future=True,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


@dataclass(frozen=True)
class SchemaMigration:
    """Single schema migration step."""

    version: int
    name: str
    apply: Callable[[AsyncConnection], Awaitable[bool]]


LATEST_SCHEMA_VERSION = 5


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for dependency injection.

    Yields:
        AsyncSession: Database session
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables and apply startup migrations."""
    # Ensure all models are imported so Base has table metadata
    import app.models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _apply_schema_migrations(conn)


async def _apply_schema_migrations(conn: AsyncConnection) -> None:
    """
    Apply versioned in-app migrations for existing SQLite databases.

    Keep startup self-healing for local deployments while avoiding a
    heavier Alembic-style migration stack for now. To add a future
    migration, append a new SchemaMigration to _SCHEMA_MIGRATIONS.
    """
    await _ensure_schema_version_table(conn)
    current_version = await _get_schema_version(conn)

    if current_version > LATEST_SCHEMA_VERSION:
        logger.warning(
            "Database schema version {} is newer than supported version {}",
            current_version,
            LATEST_SCHEMA_VERSION,
        )
        return

    for migration in _SCHEMA_MIGRATIONS:
        if migration.version <= current_version:
            continue

        changed = await migration.apply(conn)
        await _set_schema_version(conn, migration.version)
        current_version = migration.version

        action = "Applied" if changed else "Verified"
        logger.info("Schema migration v{} {}: {}", migration.version, action.lower(), migration.name)


async def _migration_v1_add_images_hash(conn: AsyncConnection) -> bool:
    """Add upload deduplication hash column and index."""
    if not await _has_table(conn, "images"):
        return False

    changed = False

    if not await _has_column(conn, "images", "hash_sha256"):
        await conn.exec_driver_sql("ALTER TABLE images ADD COLUMN hash_sha256 VARCHAR(64)")
        changed = True

    if not await _has_index(conn, "images", "ix_images_hash_sha256"):
        try:
            await conn.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_images_hash_sha256 ON images (hash_sha256)"
            )
            changed = True
        except SQLAlchemyError as e:
            logger.warning(f"Could not create unique index ix_images_hash_sha256: {e}")

    return changed


async def _migration_v2_create_analysis_results(conn: AsyncConnection) -> bool:
    """Create analysis result persistence table and indexes."""
    if not await _has_table(conn, "images"):
        return False

    changed = False

    if not await _has_table(conn, "analysis_results"):
        await conn.exec_driver_sql("""
            CREATE TABLE analysis_results (
                id VARCHAR(36) PRIMARY KEY,
                image_id VARCHAR(36) NOT NULL REFERENCES images(id) ON DELETE CASCADE,
                model VARCHAR(100) NOT NULL,
                score FLOAT,
                min_score FLOAT,
                max_score FLOAT,
                distribution TEXT,
                details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        changed = True

    index_statements = {
        "ix_analysis_results_image_id": "CREATE INDEX IF NOT EXISTS ix_analysis_results_image_id ON analysis_results (image_id)",
        "ix_analysis_results_model": "CREATE INDEX IF NOT EXISTS ix_analysis_results_model ON analysis_results (model)",
        "ix_analysis_results_created_at": "CREATE INDEX IF NOT EXISTS ix_analysis_results_created_at ON analysis_results (created_at)",
    }
    for index_name, statement in index_statements.items():
        if not await _has_index(conn, "analysis_results", index_name):
            await conn.exec_driver_sql(statement)
            changed = True

    return changed


async def _migration_v3_add_ai_model_config(conn: AsyncConnection) -> bool:
    """Add JSON config storage for AI models."""
    if not await _has_table(conn, "ai_models"):
        return False

    if await _has_column(conn, "ai_models", "config_json"):
        return False

    await conn.exec_driver_sql("ALTER TABLE ai_models ADD COLUMN config_json TEXT")
    return True


async def _migration_v4_create_ai_prompt_tables(conn: AsyncConnection) -> bool:
    """Create AI prompt and version tables."""
    changed = False

    if not await _has_table(conn, "ai_prompts"):
        await conn.exec_driver_sql(
            """
            CREATE TABLE ai_prompts (
                id VARCHAR(36) PRIMARY KEY,
                model_name VARCHAR(100) NOT NULL,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                current_version_id VARCHAR(36),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                CONSTRAINT uq_ai_prompts_model_name_name UNIQUE (model_name, name)
            )
            """
        )
        changed = True

    if not await _has_table(conn, "ai_prompt_versions"):
        await conn.exec_driver_sql(
            """
            CREATE TABLE ai_prompt_versions (
                id VARCHAR(36) PRIMARY KEY,
                prompt_id VARCHAR(36) NOT NULL REFERENCES ai_prompts(id) ON DELETE CASCADE,
                version_number INTEGER NOT NULL,
                system_prompt TEXT NOT NULL,
                user_prompt TEXT NOT NULL,
                commit_message TEXT,
                created_by VARCHAR(100),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                CONSTRAINT uq_ai_prompt_versions_prompt_id_version_number UNIQUE (prompt_id, version_number)
            )
            """
        )
        changed = True

    index_statements = {
        "ix_ai_prompts_model_name": "CREATE INDEX IF NOT EXISTS ix_ai_prompts_model_name ON ai_prompts (model_name)",
        "ix_ai_prompt_versions_prompt_id": "CREATE INDEX IF NOT EXISTS ix_ai_prompt_versions_prompt_id ON ai_prompt_versions (prompt_id)",
    }
    for index_name, statement in index_statements.items():
        if not await _has_index(conn, index_name):
            await conn.exec_driver_sql(statement)
            changed = True

    return changed


async def _migration_v5_add_analysis_prompt_metadata(conn: AsyncConnection) -> bool:
    """Track which prompt version produced an analysis result."""
    if not await _has_table(conn, "analysis_results"):
        return False

    changed = False
    columns = {
        "prompt_version_id": "ALTER TABLE analysis_results ADD COLUMN prompt_version_id VARCHAR(36)",
        "prompt_name": "ALTER TABLE analysis_results ADD COLUMN prompt_name VARCHAR(255)",
        "prompt_version_number": "ALTER TABLE analysis_results ADD COLUMN prompt_version_number INTEGER",
    }
    for column_name, statement in columns.items():
        if not await _has_column(conn, "analysis_results", column_name):
            await conn.exec_driver_sql(statement)
            changed = True

    if not await _has_index(conn, "ix_analysis_results_prompt_version_id"):
        await conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_analysis_results_prompt_version_id ON analysis_results (prompt_version_id)"
        )
        changed = True

    return changed


_SCHEMA_MIGRATIONS = (
    SchemaMigration(version=1, name="images.hash_sha256", apply=_migration_v1_add_images_hash),
    SchemaMigration(version=2, name="analysis_results table", apply=_migration_v2_create_analysis_results),
    SchemaMigration(version=3, name="ai_models.config_json", apply=_migration_v3_add_ai_model_config),
    SchemaMigration(version=4, name="ai prompt tables", apply=_migration_v4_create_ai_prompt_tables),
    SchemaMigration(version=5, name="analysis_results prompt metadata", apply=_migration_v5_add_analysis_prompt_metadata),
)


async def _ensure_schema_version_table(conn: AsyncConnection) -> None:
    """Create the schema version table if it does not exist."""
    await conn.exec_driver_sql("""
        CREATE TABLE IF NOT EXISTS schema_version (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            version INTEGER NOT NULL DEFAULT 0,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)
    await conn.exec_driver_sql(
        "INSERT OR IGNORE INTO schema_version (id, version) VALUES (1, 0)"
    )


async def _get_schema_version(conn: AsyncConnection) -> int:
    """Read the current schema version from the database."""
    result = await conn.exec_driver_sql("SELECT version FROM schema_version WHERE id = 1")
    row = result.fetchone()
    return int(row[0]) if row is not None else 0


async def _set_schema_version(conn: AsyncConnection, version: int) -> None:
    """Persist the current schema version."""
    await conn.exec_driver_sql(
        "UPDATE schema_version SET version = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
        (version,),
    )


async def _has_column(conn: AsyncConnection, table_name: str, column_name: str) -> bool:
    """Check whether a table contains a specific column."""
    result = await conn.exec_driver_sql(f'PRAGMA table_info("{table_name}")')
    return any(row[1] == column_name for row in result.fetchall())


async def _has_index(
    conn: AsyncConnection,
    table_name_or_index_name: str,
    index_name: str | None = None,
) -> bool:
    """Check whether a table contains a specific index."""
    if index_name is None:
        result = await conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
            (table_name_or_index_name,),
        )
        return result.fetchone() is not None

    if not await _has_table(conn, table_name_or_index_name):
        return False

    result = await conn.exec_driver_sql(f'PRAGMA index_list("{table_name_or_index_name}")')
    return any(row[1] == index_name for row in result.fetchall())


async def _has_table(conn: AsyncConnection, table_name: str) -> bool:
    """Check whether a table exists in the database."""
    result = await conn.exec_driver_sql(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    return result.fetchone() is not None


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
