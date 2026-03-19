"""
Database initialization script
Run this to create all tables and apply schema migrations
"""
import asyncio

from app.core.database import close_db, init_db


async def create_tables() -> None:
    """Create all database tables and run in-app migrations."""
    print("Creating database tables...")
    await init_db()
    print("✓ Tables created successfully")


async def main() -> None:
    """Initialize database with tables."""
    print("=" * 50)
    print("Database Initialization")
    print("=" * 50)
    print()

    try:
        await create_tables()
        print()

        print("=" * 50)
        print("Database initialization complete!")
        print("=" * 50)

    except Exception as e:
        print(f"✗ Error: {e}")
        raise
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
