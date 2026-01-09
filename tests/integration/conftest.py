"""Integration test fixtures.

Provides fixtures for integration testing with real Redis via testcontainers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient
from testcontainers.redis import RedisContainer

import app.cache.redis as redis_module
from app.cache.redis import close_redis_pools
from app.core.config import Settings
from app.factory import create_app


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from fastapi import FastAPI


pytestmark = pytest.mark.integration


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
    # Parse redis URL to get host/port from testcontainer
    parts = redis_url.replace("redis://", "").split(":")
    redis_host = parts[0]
    redis_port = int(parts[1])

    return Settings(
        APP_NAME="test-app",
        APP_VERSION="0.0.1-test",
        ENVIRONMENT="test",
        DEBUG=True,
        HOST="0.0.0.0",
        PORT=8000,
        JWT_SECRET_KEY="test-jwt-secret-key-for-integration-tests",
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
) -> AsyncGenerator[AsyncClient]:
    """Create authenticated client with valid access token."""
    # Login to get token
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "demo@example.com",
            "password": "demo1234",
        },
    )

    if response.status_code == 200:
        token = response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"

    return client


@pytest.fixture(autouse=True)
async def reset_redis_state() -> AsyncGenerator[None]:
    """Reset Redis module state before and after each test."""
    # Reset global state before test
    redis_module._cache_pool = None
    redis_module._queue_pool = None
    redis_module._rate_limit_pool = None
    redis_module._cache_client = None
    redis_module._queue_client = None
    redis_module._rate_limit_client = None

    yield

    # Close any connections and reset state after test
    await close_redis_pools()
