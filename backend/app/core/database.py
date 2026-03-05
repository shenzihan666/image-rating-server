"""
Database configuration and session management
"""
from collections.abc import AsyncGenerator

from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker, create_async_engine
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
    """Initialize database tables."""
    # Ensure all models are imported so Base has table metadata
    import app.models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _apply_schema_migrations(conn)


async def _apply_schema_migrations(conn: AsyncConnection) -> None:
    """
    Apply lightweight in-app migrations for existing SQLite databases.

    This keeps backward compatibility when models add new columns but
    the local DB file predates those schema changes.
    """
    # Add missing hash column used by upload deduplication.
    has_hash_column = await _has_column(conn, "images", "hash_sha256")
    if not has_hash_column:
        await conn.exec_driver_sql("ALTER TABLE images ADD COLUMN hash_sha256 VARCHAR(64)")
        logger.info("Applied schema migration: added images.hash_sha256 column")

    # Add index for fast dedup checks. Keep startup resilient if unique index fails.
    try:
        await conn.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_images_hash_sha256 ON images (hash_sha256)"
        )
    except SQLAlchemyError as e:
        logger.warning(f"Could not create unique index ix_images_hash_sha256: {e}")


async def _has_column(conn: AsyncConnection, table_name: str, column_name: str) -> bool:
    """Check whether a table contains a specific column."""
    result = await conn.exec_driver_sql(f'PRAGMA table_info("{table_name}")')
    return any(row[1] == column_name for row in result.fetchall())


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
