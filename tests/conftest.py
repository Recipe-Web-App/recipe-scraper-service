"""Root pytest configuration and fixtures.

This module provides shared fixtures for all tests including:
- Test settings with environment overrides
- FastAPI test application
- Async HTTP client
- Authentication helpers
- Redis mocking utilities
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.jwt import create_access_token
from app.core.config import Settings
from app.factory import create_app


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from fastapi import FastAPI


# =============================================================================
# Event Loop Configuration
# =============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Settings Fixtures
# =============================================================================


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with safe defaults.

    Returns settings configured for testing:
    - ENVIRONMENT set to 'testing'
    - Test JWT secret
    - Local Redis (for integration tests)
    """
    return Settings(
        ENVIRONMENT="testing",
        DEBUG=True,
        JWT_SECRET_KEY="test-secret-key-for-testing-only-32chars",
        JWT_ACCESS_TOKEN_EXPIRE_MINUTES=5,
        JWT_REFRESH_TOKEN_EXPIRE_DAYS=1,
        REDIS_HOST="localhost",
        REDIS_PORT=6379,
        REDIS_PASSWORD="",
        LOG_LEVEL="DEBUG",
        LOG_FORMAT="text",
        ENABLE_TRACING=False,
        METRICS_ENABLED=False,
        CORS_ORIGINS=["http://localhost:3000"],
        SERVICE_API_KEYS=["test-api-key-12345"],
    )


@pytest.fixture
def mock_settings(test_settings: Settings) -> Generator[Settings]:
    """Patch get_settings to return test settings."""
    with patch("app.core.config.get_settings", return_value=test_settings):
        yield test_settings


# =============================================================================
# Redis Fixtures
# =============================================================================


@pytest.fixture
def mock_redis() -> MagicMock:
    """Create a mock Redis client for unit tests.

    Returns a MagicMock configured to behave like an async Redis client.
    """
    mock = MagicMock()

    # Async method mocks
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=0)
    mock.ttl = AsyncMock(return_value=-2)
    mock.ping = AsyncMock(return_value=True)
    mock.close = AsyncMock()

    # Scan iterator mock
    async def mock_scan_iter(*args: Any, **kwargs: Any) -> AsyncGenerator[str]:
        for key in []:
            yield key

    mock.scan_iter = mock_scan_iter

    return mock


@pytest.fixture
def mock_redis_pools(mock_redis: MagicMock) -> Generator[None]:
    """Patch Redis pool functions to use mock client."""
    with (
        patch("app.cache.redis.get_cache_client", return_value=mock_redis),
        patch("app.cache.redis.get_queue_client", return_value=mock_redis),
        patch("app.cache.redis.get_rate_limit_client", return_value=mock_redis),
        patch("app.cache.redis.init_redis_pools", new_callable=AsyncMock),
        patch("app.cache.redis.close_redis_pools", new_callable=AsyncMock),
    ):
        yield


# =============================================================================
# Application Fixtures
# =============================================================================


@pytest.fixture
def app(mock_settings: Settings, mock_redis_pools: None) -> FastAPI:
    """Create a FastAPI test application.

    This fixture:
    - Uses test settings
    - Mocks Redis connections
    - Skips real lifespan events
    """
    # Patch lifespan to avoid real startup/shutdown
    with (
        patch("app.core.events.lifespan.init_redis_pools", new_callable=AsyncMock),
        patch("app.core.events.lifespan.get_arq_pool", new_callable=AsyncMock),
    ):
        return create_app(settings=mock_settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """Create an async HTTP client for testing.

    Usage:
        async def test_endpoint(client):
            response = await client.get("/api/v1/health")
            assert response.status_code == 200
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# =============================================================================
# Authentication Fixtures
# =============================================================================


@pytest.fixture
def test_user_id() -> str:
    """Standard test user ID."""
    return "test-user-123"


@pytest.fixture
def test_user_roles() -> list[str]:
    """Standard test user roles."""
    return ["user"]


@pytest.fixture
def access_token(
    test_settings: Settings,
    test_user_id: str,
    test_user_roles: list[str],
) -> str:
    """Create a valid access token for testing.

    Returns a JWT access token with standard test user claims.
    """
    with patch("app.core.config.get_settings", return_value=test_settings):
        return create_access_token(
            subject=test_user_id,
            roles=test_user_roles,
            permissions=["recipe:read", "recipe:create"],
        )


@pytest.fixture
def admin_token(test_settings: Settings) -> str:
    """Create an admin access token for testing."""
    with patch("app.core.config.get_settings", return_value=test_settings):
        return create_access_token(
            subject="admin-user-456",
            roles=["admin"],
            permissions=[],
        )


@pytest.fixture
def auth_headers(access_token: str) -> dict[str, str]:
    """Create authorization headers with test token."""
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def admin_headers(admin_token: str) -> dict[str, str]:
    """Create authorization headers with admin token."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def api_key_headers(test_settings: Settings) -> dict[str, str]:
    """Create headers with test API key."""
    return {"X-API-Key": test_settings.SERVICE_API_KEYS[0]}


# =============================================================================
# Utility Fixtures
# =============================================================================


@pytest.fixture
def sample_recipe_data() -> dict[str, Any]:
    """Sample recipe data for testing."""
    return {
        "id": "recipe-123",
        "title": "Test Recipe",
        "description": "A test recipe for testing",
        "ingredients": ["ingredient 1", "ingredient 2"],
        "instructions": ["Step 1", "Step 2"],
        "prep_time": 10,
        "cook_time": 20,
        "servings": 4,
        "url": "https://example.com/recipe",
    }


@pytest.fixture
def sample_user_data() -> dict[str, Any]:
    """Sample user data for testing."""
    return {
        "id": "user-123",
        "email": "test@example.com",
        "name": "Test User",
        "roles": ["user"],
    }


# =============================================================================
# Async Utilities
# =============================================================================


@pytest.fixture
def anyio_backend() -> str:
    """Specify the async backend for anyio tests."""
    return "asyncio"
