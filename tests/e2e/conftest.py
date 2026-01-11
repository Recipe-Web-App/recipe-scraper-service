"""E2E test fixtures.

Provides fixtures for end-to-end testing with full system integration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from arq import create_pool
from arq.connections import RedisSettings
from httpx import ASGITransport, AsyncClient
from testcontainers.redis import RedisContainer

import app.cache.redis as redis_module
from app.auth.jwt import create_access_token
from app.cache.redis import close_redis_pools, init_redis_pools
from app.core.config import Settings
from app.factory import create_app


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from arq import ArqRedis
    from fastapi import FastAPI


pytestmark = pytest.mark.e2e


@pytest.fixture(scope="session")
def redis_container() -> Generator[RedisContainer]:
    """Start a Redis container for the test session."""
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
    """Create test settings with Redis container URLs."""
    parts = redis_url.replace("redis://", "").split(":")
    redis_host = parts[0]
    redis_port = int(parts[1])

    return Settings(
        APP_NAME="e2e-test-app",
        APP_VERSION="0.0.1-e2e",
        ENVIRONMENT="test",
        DEBUG=True,
        HOST="0.0.0.0",
        PORT=8000,
        JWT_SECRET_KEY="e2e-test-jwt-secret-key",
        JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30,
        JWT_REFRESH_TOKEN_EXPIRE_DAYS=7,
        REDIS_HOST=redis_host,
        REDIS_PORT=redis_port,
        REDIS_PASSWORD="",
        REDIS_CACHE_DB=0,
        REDIS_QUEUE_DB=1,
        REDIS_RATE_LIMIT_DB=2,
        CORS_ORIGINS=["http://localhost:3000"],
        RATE_LIMIT_DEFAULT="100/minute",
        RATE_LIMIT_AUTH="10/minute",
        METRICS_ENABLED=False,
        ENABLE_TRACING=False,
        LOG_LEVEL="DEBUG",
        LOG_FORMAT="json",
    )


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    """Create FastAPI app with test settings."""
    return create_app(test_settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """Create async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
async def authenticated_client(
    client: AsyncClient,
    test_settings: Settings,
) -> AsyncGenerator[AsyncClient]:
    """Create authenticated client with valid access token.

    Since auth endpoints are now handled by the external auth-service,
    we create tokens directly using the JWT module.
    """
    with patch("app.auth.jwt.get_settings", return_value=test_settings):
        token = create_access_token(
            subject="e2e-test-user",
            roles=["user"],
            permissions=["recipe:read", "recipe:write"],
        )
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture
async def arq_pool(redis_url: str) -> AsyncGenerator[ArqRedis]:
    """Create ARQ connection pool for e2e tests."""
    parts = redis_url.replace("redis://", "").split(":")
    host = parts[0]
    port = int(parts[1])

    pool = await create_pool(
        RedisSettings(host=host, port=port, database=1),
    )
    yield pool
    await pool.aclose()


@pytest.fixture
async def initialized_redis(
    test_settings: Settings,
) -> AsyncGenerator[None]:
    """Initialize Redis pools for e2e tests."""
    with patch("app.cache.redis.get_settings", return_value=test_settings):
        await init_redis_pools()

    yield

    await close_redis_pools()


@pytest.fixture(autouse=True)
async def reset_redis_state() -> AsyncGenerator[None]:
    """Reset Redis module state before and after each test."""
    redis_module._cache_pool = None
    redis_module._queue_pool = None
    redis_module._rate_limit_pool = None
    redis_module._cache_client = None
    redis_module._queue_client = None
    redis_module._rate_limit_client = None

    yield

    await close_redis_pools()
