"""Redis client and connection pool management.

This module provides:
- Async Redis connection pool management
- Multiple Redis instances for different purposes (cache, queue, rate limit)
- Connection lifecycle management via lifespan events
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from app.core.config import get_settings
from app.observability.logging import get_logger


if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = get_logger(__name__)

# Global connection pools
_cache_pool: ConnectionPool[Any] | None = None
_queue_pool: ConnectionPool[Any] | None = None
_rate_limit_pool: ConnectionPool[Any] | None = None

# Global clients
_cache_client: Redis[Any] | None = None
_queue_client: Redis[Any] | None = None
_rate_limit_client: Redis[Any] | None = None


async def init_redis_pools() -> None:
    """Initialize Redis connection pools.

    Should be called during application startup (lifespan).
    """
    global _cache_pool, _queue_pool, _rate_limit_pool  # noqa: PLW0603
    global _cache_client, _queue_client, _rate_limit_client  # noqa: PLW0603

    settings = get_settings()

    logger.info(
        "Initializing Redis connections",
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
    )

    # Cache pool
    _cache_pool = ConnectionPool.from_url(
        settings.REDIS_CACHE_URL,
        max_connections=20,
        decode_responses=True,
    )
    _cache_client = redis.Redis(connection_pool=_cache_pool)

    # Queue pool (for ARQ)
    _queue_pool = ConnectionPool.from_url(
        settings.REDIS_QUEUE_URL,
        max_connections=10,
        decode_responses=False,  # ARQ needs bytes
    )
    _queue_client = redis.Redis(connection_pool=_queue_pool)

    # Rate limit pool
    _rate_limit_pool = ConnectionPool.from_url(
        settings.REDIS_RATE_LIMIT_URL,
        max_connections=10,
        decode_responses=True,
    )
    _rate_limit_client = redis.Redis(connection_pool=_rate_limit_pool)

    # Verify connections
    try:
        assert _cache_client is not None
        assert _queue_client is not None
        assert _rate_limit_client is not None
        await _cache_client.ping()
        await _queue_client.ping()
        await _rate_limit_client.ping()
        logger.info("Redis connections established successfully")
    except redis.ConnectionError:
        logger.exception("Failed to connect to Redis")
        raise


async def close_redis_pools() -> None:
    """Close Redis connection pools.

    Should be called during application shutdown (lifespan).
    """
    global _cache_pool, _queue_pool, _rate_limit_pool  # noqa: PLW0603
    global _cache_client, _queue_client, _rate_limit_client  # noqa: PLW0603

    logger.info("Closing Redis connections")

    if _cache_client:
        await _cache_client.close()
        _cache_client = None

    if _queue_client:
        await _queue_client.close()
        _queue_client = None

    if _rate_limit_client:
        await _rate_limit_client.close()
        _rate_limit_client = None

    if _cache_pool:
        await _cache_pool.disconnect()
        _cache_pool = None

    if _queue_pool:
        await _queue_pool.disconnect()
        _queue_pool = None

    if _rate_limit_pool:
        await _rate_limit_pool.disconnect()
        _rate_limit_pool = None

    logger.info("Redis connections closed")


def get_cache_client() -> Redis[Any]:
    """Get the cache Redis client.

    Returns:
        Redis client for caching operations.

    Raises:
        RuntimeError: If Redis is not initialized.
    """
    if _cache_client is None:
        msg = "Redis cache client not initialized. Call init_redis_pools() first."
        raise RuntimeError(msg)
    return _cache_client


def get_queue_client() -> Redis[Any]:
    """Get the queue Redis client.

    Returns:
        Redis client for job queue operations.

    Raises:
        RuntimeError: If Redis is not initialized.
    """
    if _queue_client is None:
        msg = "Redis queue client not initialized. Call init_redis_pools() first."
        raise RuntimeError(msg)
    return _queue_client


def get_rate_limit_client() -> Redis[Any]:
    """Get the rate limit Redis client.

    Returns:
        Redis client for rate limiting operations.

    Raises:
        RuntimeError: If Redis is not initialized.
    """
    if _rate_limit_client is None:
        msg = "Redis rate limit client not initialized. Call init_redis_pools() first."
        raise RuntimeError(msg)
    return _rate_limit_client


async def check_redis_health() -> dict[str, str]:
    """Check health of all Redis connections.

    Returns:
        Dictionary with health status for each Redis instance.
    """
    results: dict[str, str] = {}

    # Check cache
    try:
        if _cache_client:
            await _cache_client.ping()
            results["redis_cache"] = "healthy"
        else:
            results["redis_cache"] = "not_initialized"
    except redis.ConnectionError:
        results["redis_cache"] = "unhealthy"

    # Check queue
    try:
        if _queue_client:
            await _queue_client.ping()
            results["redis_queue"] = "healthy"
        else:
            results["redis_queue"] = "not_initialized"
    except redis.ConnectionError:
        results["redis_queue"] = "unhealthy"

    # Check rate limit
    try:
        if _rate_limit_client:
            await _rate_limit_client.ping()
            results["redis_rate_limit"] = "healthy"
        else:
            results["redis_rate_limit"] = "not_initialized"
    except redis.ConnectionError:
        results["redis_rate_limit"] = "unhealthy"

    return results
