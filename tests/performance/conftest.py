"""Performance test fixtures.

Provides fixtures for benchmarking with pytest-benchmark.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient
from testcontainers.redis import RedisContainer

import app.cache.redis as redis_module
from app.cache.redis import close_redis_pools, init_redis_pools
from app.core.config import Settings
from app.core.config.settings import (
    ApiSettings,
    AppSettings,
    AuthSettings,
    LoggingSettings,
    ObservabilitySettings,
    RateLimitingSettings,
    RedisSettings,
    ServerSettings,
)
from app.factory import create_app


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from fastapi import FastAPI


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
        APP_ENV="test",
        JWT_SECRET_KEY="perf-test-jwt-secret-key",
        REDIS_PASSWORD="",
        app=AppSettings(
            name="perf-test-app",
            version="0.0.1-perf",
            debug=False,  # Disable debug for realistic benchmarks
        ),
        server=ServerSettings(
            host="0.0.0.0",
            port=8000,
        ),
        api=ApiSettings(
            cors_origins=["http://localhost:3000"],
        ),
        auth=AuthSettings(
            mode="disabled",
        ),
        redis=RedisSettings(
            host=redis_host,
            port=redis_port,
            cache_db=0,
            queue_db=1,
            rate_limit_db=2,
        ),
        rate_limiting=RateLimitingSettings(
            default="1000/minute",
            auth="100/minute",
        ),
        logging=LoggingSettings(
            level="WARNING",  # Reduce logging for benchmarks
            format="json",
        ),
        observability=ObservabilitySettings(),
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


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    """Create FastAPI app with test settings for performance tests."""
    return create_app(test_settings)


@pytest.fixture
def sync_client(app: FastAPI) -> Generator[TestClient]:
    """Create a sync HTTP client for performance benchmarks.

    Uses Starlette TestClient to avoid event loop conflicts with pytest-benchmark.
    """
    with TestClient(app) as client:
        yield client
