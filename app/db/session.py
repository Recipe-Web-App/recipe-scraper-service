"""Database session management.

Handles the creation and configuration of database sessions and connections used
throughout the application.
"""

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config.config import settings

DATABASE_URL = (
    f"postgresql://{settings.recipe_scraper_db_user}:{settings.recipe_scraper_db_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
)

# Async database URL for AsyncSession
ASYNC_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.recipe_scraper_db_user}:{settings.recipe_scraper_db_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
)

# Sync engine and session (for existing code)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async engine and session maker
async_engine = create_async_engine(ASYNC_DATABASE_URL, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session.

    Yields:     AsyncSession: Database session for async operations
    """

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
