"""Integration test fixtures.

Provides fixtures for integration testing with real Redis via testcontainers.
"""

from __future__ import annotations

import contextlib
import os
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from prometheus_client import REGISTRY
from redis.asyncio import Redis
from testcontainers.redis import RedisContainer

import app.cache.redis as redis_module
from app.auth.jwt import create_access_token
from app.cache.redis import close_redis_pools
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
async def cache(redis_url: str) -> AsyncGenerator[Redis[bytes]]:
    """Create a Redis client connected to the test container.

    This fixture provides a real Redis client for integration tests.
    """
    client: Redis[bytes] = Redis.from_url(redis_url, decode_responses=False)
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
def test_settings(redis_url: str) -> Settings:
    """Create test settings with Redis container URLs."""
    # Parse redis URL to get host/port from testcontainer
    parts = redis_url.replace("redis://", "").split(":")
    redis_host = parts[0]
    redis_port = int(parts[1])

    return Settings(
        APP_ENV="test",
        JWT_SECRET_KEY="test-jwt-secret-key-for-integration-tests",
        REDIS_PASSWORD="",
        app=AppSettings(
            name="test-app",
            version="0.0.1-test",
            debug=True,
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
            default="100/minute",
            auth="10/minute",
        ),
        logging=LoggingSettings(
            level="DEBUG",
            format="json",
        ),
        observability=ObservabilitySettings(),
    )


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    """Create FastAPI app with test settings.

    Patches get_settings in observability modules to use test settings,
    since those modules call get_settings() directly rather than using
    the settings passed to create_app().

    Also sets METRICS_ENABLED env var since prometheus-fastapi-instrumentator
    checks this when should_respect_env_var=True.
    """

    original_metrics_enabled = os.environ.get("METRICS_ENABLED")
    os.environ["METRICS_ENABLED"] = "true"

    try:
        with (
            patch("app.observability.metrics.get_settings", return_value=test_settings),
            patch("app.observability.tracing.get_settings", return_value=test_settings),
        ):
            return create_app(test_settings)
    finally:
        if original_metrics_enabled is None:
            os.environ.pop("METRICS_ENABLED", None)
        else:
            os.environ["METRICS_ENABLED"] = original_metrics_enabled


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

    Creates a JWT token directly instead of using auth endpoints
    (which are now handled by external auth-service).
    """
    # Create token directly
    token = create_access_token(
        subject="test-user-id",
        roles=["user"],
        permissions=["recipe:read", "recipe:write"],
    )

    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture
async def admin_client(
    client: AsyncClient,
    test_settings: Settings,
) -> AsyncGenerator[AsyncClient]:
    """Create authenticated client with admin privileges."""
    token = create_access_token(
        subject="admin-user-id",
        roles=["admin"],
        permissions=[],  # Admin role grants all permissions
    )

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


@pytest.fixture(autouse=True)
def reset_prometheus_registry() -> Generator[None]:
    """Reset Prometheus registry between tests.

    This prevents 'Duplicated timeseries' errors when creating
    multiple app instances in tests.
    """

    # Collect all collector names before test
    collectors_before = set(REGISTRY._names_to_collectors.keys())

    yield

    # Remove any collectors added during the test
    collectors_to_remove = []
    for name, collector in list(REGISTRY._names_to_collectors.items()):
        if name not in collectors_before:
            collectors_to_remove.append(collector)

    for collector in collectors_to_remove:
        with contextlib.suppress(Exception):
            REGISTRY.unregister(collector)
