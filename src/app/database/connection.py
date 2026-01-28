"""PostgreSQL connection pool management.

This module provides:
- Async connection pool management via asyncpg
- Connection lifecycle management via lifespan events
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import asyncpg

from app.core.config import get_settings
from app.observability.logging import get_logger


if TYPE_CHECKING:
    from asyncpg import Pool

logger = get_logger(__name__)

# Global connection pool
_pool: Pool | None = None


async def init_database_pool() -> None:
    """Initialize PostgreSQL connection pool.

    Should be called during application startup (lifespan).
    """
    global _pool  # noqa: PLW0603

    settings = get_settings()

    logger.info(
        "Initializing database connection pool",
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
    )

    _pool = await asyncpg.create_pool(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.DATABASE_PASSWORD or None,
        min_size=settings.database.min_pool_size,
        max_size=settings.database.max_pool_size,
        command_timeout=settings.database.command_timeout,
        ssl=settings.database.ssl if settings.database.ssl else None,
    )

    # Verify connection
    try:
        assert _pool is not None
        async with _pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        logger.info("Database connection established successfully")
    except asyncpg.PostgresError:
        logger.exception("Failed to connect to database")
        raise


async def close_database_pool() -> None:
    """Close PostgreSQL connection pool.

    Should be called during application shutdown (lifespan).
    """
    global _pool  # noqa: PLW0603

    logger.info("Closing database connection pool")

    if _pool:
        await _pool.close()
        _pool = None

    logger.info("Database connection pool closed")


def get_database_pool() -> Pool:
    """Get the database connection pool.

    Returns:
        PostgreSQL connection pool.

    Raises:
        RuntimeError: If pool is not initialized.
    """
    if _pool is None:
        msg = "Database pool not initialized. Call init_database_pool() first."
        raise RuntimeError(msg)
    return _pool


async def check_database_health() -> dict[str, str]:
    """Check health of database connection.

    Returns:
        Dictionary with health status.
    """
    results: dict[str, str] = {}

    try:
        if _pool:
            async with _pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            results["database"] = "healthy"
        else:
            results["database"] = "not_initialized"
    except asyncpg.PostgresError:
        results["database"] = "unhealthy"
    except Exception:
        results["database"] = "unhealthy"

    return results
