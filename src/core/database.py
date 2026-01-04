from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from fastapi_users.db import SQLAlchemyUserDatabase

from src.models import Base, User
from src.core.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def create_db_and_tables():
    """Create database tables based on SQLAlchemy models."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get an async database session.
    
    Yields:
        AsyncSession: The database session.
    """
    async with SessionLocal() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    """
    Dependency to get the FastAPI Users database adapter.
    
    Args:
        session (AsyncSession): The database session.
        
    Yields:
        SQLAlchemyUserDatabase: The user database adapter.
    """
    yield SQLAlchemyUserDatabase(session, User)
