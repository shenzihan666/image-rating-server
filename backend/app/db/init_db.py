"""
Database initialization script
Run this to create all tables and seed initial data
"""
import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.database import close_db, init_db
from app.core.security import hash_password
from app.models.user import User


async def create_tables():
    """Create all database tables."""
    print("Creating database tables...")
    await init_db()
    print("✓ Tables created successfully")


async def seed_test_user() -> None:
    """Create a test user for development."""
    from sqlalchemy import select

    from app.core.database import engine

    print("Checking for test user...")

    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        # Check if demo user exists
        result = await session.execute(
            select(User).where(User.email == "demo@example.com")
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print("✓ Demo user already exists")
            return

        # Create demo user
        demo_user = User(
            email="demo@example.com",
            hashed_password=hash_password("password123"),
            full_name="Demo User",
            is_active=True,
            is_superuser=True,
        )

        session.add(demo_user)
        await session.commit()
        print("✓ Demo user created (demo@example.com / password123)")


async def main():
    """Initialize database with tables and seed data."""
    print("=" * 50)
    print("Database Initialization")
    print("=" * 50)
    print()

    try:
        # Create tables
        await create_tables()
        print()

        # Seed test data
        await seed_test_user()
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
