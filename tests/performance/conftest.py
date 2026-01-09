"""Performance test fixtures.

Provides fixtures for benchmarking with pytest-benchmark.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from testcontainers.redis import RedisContainer

import app.cache.redis as redis_module
from app.cache.redis import close_redis_pools, init_redis_pools
from app.core.config import Settings


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator


pytestmark = pytest.mark.performance


@pytest.fixture(scope="session")
def redis_container() -> Generator[RedisContainer]:
    """Start a Redis container for performance tests."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


@pytest.fixture(scope="session")
def redis_url(redis_container: RedisContainer) -> str:
    """Get the Redis URL from the container."""
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    return f"redis://{host}:{port}"


@pytest.fixture
def test_settings(redis_url: str) -> Settings:
    """Create test settings for performance tests."""
    parts = redis_url.replace("redis://", "").split(":")
    redis_host = parts[0]
    redis_port = int(parts[1])

    return Settings(
        APP_NAME="perf-test-app",
        APP_VERSION="0.0.1-perf",
        ENVIRONMENT="test",
        DEBUG=False,  # Disable debug for realistic benchmarks
        HOST="0.0.0.0",
        PORT=8000,
        JWT_SECRET_KEY="perf-test-jwt-secret-key",
        JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30,
        JWT_REFRESH_TOKEN_EXPIRE_DAYS=7,
        REDIS_HOST=redis_host,
        REDIS_PORT=redis_port,
        REDIS_PASSWORD="",
        REDIS_CACHE_DB=0,
        REDIS_QUEUE_DB=1,
        REDIS_RATE_LIMIT_DB=2,
        CORS_ORIGINS=["http://localhost:3000"],
        RATE_LIMIT_DEFAULT="1000/minute",
        RATE_LIMIT_AUTH="100/minute",
        METRICS_ENABLED=False,
        ENABLE_TRACING=False,
        LOG_LEVEL="WARNING",  # Reduce logging for benchmarks
        LOG_FORMAT="json",
    )


@pytest.fixture
async def initialized_redis(
    test_settings: Settings,
) -> AsyncGenerator[None]:
    """Initialize Redis pools for performance tests."""
    with patch("app.cache.redis.get_settings", return_value=test_settings):
        await init_redis_pools()

    yield

    await close_redis_pools()


@pytest.fixture(autouse=True)
async def reset_redis_state() -> AsyncGenerator[None]:
    """Reset Redis module state between tests."""
    redis_module._cache_pool = None
    redis_module._queue_pool = None
    redis_module._rate_limit_pool = None
    redis_module._cache_client = None
    redis_module._queue_client = None
    redis_module._rate_limit_client = None

    yield

    await close_redis_pools()
