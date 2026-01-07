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
