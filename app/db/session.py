"""Database session management.

Handles the creation and configuration of database sessions and connections used
throughout the application.
"""

import asyncio
from collections.abc import AsyncGenerator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import DisconnectionError, OperationalError
from sqlalchemy.exc import TimeoutError as SQLTimeoutError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config.config import settings
from app.core.logging import get_logger
from app.exceptions.custom_exceptions import DatabaseUnavailableError

_log = get_logger(__name__)

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
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_size=10,
    max_overflow=20,
    connect_args={
        "connect_timeout": 10,  # 10 second connection timeout
    },
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async engine and session maker with enhanced connection pooling
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_size=10,
    max_overflow=20,
    connect_args={
        "server_settings": {
            "jit": "off",  # Disable JIT for better connection stability
        },
        "command_timeout": 10,  # 10 second query timeout
    },
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Dependency to get database session with connection retry logic.

    This function attempts to create a database session with retry logic.
    If the database is unavailable, it raises DatabaseUnavailableError
    which will be caught by the global exception handler.

    Yields:
        AsyncSession: Database session for async operations

    Raises:
        DatabaseUnavailableError: If database connection cannot be established
    """
    max_retries = 3
    retry_delay = 0.5  # Start with 500ms

    for attempt in range(max_retries):
        try:
            # Attempt to create session
            async with AsyncSessionLocal() as session:
                # Test the connection with a simple query
                await session.execute(text("SELECT 1"))
                yield session
                return  # Success, exit the retry loop

        except (
            OperationalError,
            DisconnectionError,
            SQLTimeoutError,
            ConnectionError,
            TimeoutError,
        ) as e:
            _log.warning(
                "Database connection attempt {} failed: {} ({})",
                attempt + 1,
                str(e)[:200],
                type(e).__name__,
            )

            # If this is the last attempt, raise DatabaseUnavailableException
            if attempt == max_retries - 1:
                _log.error(
                    "Database connection failed after {} attempts, giving up",
                    max_retries,
                )
                raise DatabaseUnavailableError(
                    reason="Connection failed after multiple attempts",
                    original_error=e,
                ) from e

            # Wait before retrying with exponential backoff
            await asyncio.sleep(retry_delay)
            retry_delay *= 2  # Double the delay for next attempt

        except Exception as e:
            # For unexpected errors, don't retry and raise immediately
            _log.error(
                "Unexpected database error: {} ({})",
                str(e)[:200],
                type(e).__name__,
                exc_info=True,
            )
            raise DatabaseUnavailableError(
                reason="Unexpected database error",
                original_error=e,
            ) from e


async def check_database_health() -> bool:
    """Check if the database is available and responding.

    Returns:
        bool: True if database is healthy, False otherwise
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        _log.debug("Database health check failed: {} ({})", str(e), type(e).__name__)
        return False
