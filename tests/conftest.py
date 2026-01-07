import os
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typing import AsyncGenerator

# Set environment variable before importing application modules
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

# Import from source AFTER setting env
from src.app import app
from src.core.database import engine, Base, get_async_session

# Create session maker for the engine (which is now connected to :memory:)
TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(autouse=True)
async def prepare_database():
    """Create tables before tests run and drop them afterwards."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture that returns an async session.
    """
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
async def client(session) -> AsyncGenerator[AsyncClient, None]:
    """
    Fixture that returns an AsyncClient with the database dependency overridden.
    """
    async def override_get_async_session():
        yield session

    app.dependency_overrides[get_async_session] = override_get_async_session
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.fixture
async def authenticated_client(client, session):
    """
    Fixture that returns an authenticated client and the user.
    """
    email = "test@example.com"
    password = "password123"

    # Register user
    response = await client.post("/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201
    user_id = response.json()["id"]

    # Login to get token
    response = await client.post("/auth/jwt/login", data={"username": email, "password": password})
    assert response.status_code == 200
    token = response.json()["access_token"]

    client.headers = {"Authorization": f"Bearer {token}"}
    return client

@pytest.fixture
async def test_post(authenticated_client, session):
    """
    Fixture that creates a test post.
    """
    from src.models import Post
    import uuid

    # We need to get the user ID from the authenticated client context or just query the DB
    # Since we just created the user in authenticated_client, let's fetch it
    from src.models import User
    from sqlalchemy import select

    result = await session.execute(select(User).where(User.email == "test@example.com"))
    user = result.scalars().first()

    post = Post(
        user_id=user.id,
        caption="Test Post",
        url="http://imagekit.io/test.jpg",
        file_type="image",
        file_name="test.jpg",
        file_id="12345"
    )
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return post
