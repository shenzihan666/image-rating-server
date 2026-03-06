"""
Tests for /api/v1/auth endpoints.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, async_session_maker, engine
from app.core.security import create_access_token, hash_password
from app.models.user import User


@pytest.fixture(scope="function")
async def db_session() -> AsyncSession:
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
        id="auth-test-user-id",
        email="auth-test@example.com",
        full_name="Auth Test User",
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


@pytest.mark.asyncio
async def test_auth_me_returns_current_user(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """
    GET /api/v1/auth/me should return the authenticated user's profile.
    """
    response = await async_client.get("/api/v1/auth/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["user_id"] == "auth-test-user-id"
    assert response.json()["email"] == "auth-test@example.com"
    assert response.json()["full_name"] == "Auth Test User"
