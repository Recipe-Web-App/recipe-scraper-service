"""Integration tests for admin endpoints.

Tests cover:
- Cache clear with real Redis
- Authentication flow
- Error scenarios
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.cache.redis import (
    close_redis_pools,
    get_cache_client,
    init_redis_pools,
)


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import FastAPI

    from app.core.config import Settings


pytestmark = pytest.mark.integration


# Mock users for testing
MOCK_ADMIN_USER = CurrentUser(
    id="admin-user-123",
    roles=["admin"],
    permissions=["admin:system"],
)

MOCK_REGULAR_USER = CurrentUser(
    id="regular-user-456",
    roles=["user"],
    permissions=["recipe:read"],
)


@pytest.fixture
async def admin_cache_client(
    app: FastAPI,
    test_settings: Settings,
) -> AsyncGenerator[AsyncClient]:
    """Create client with admin user for cache operations."""

    async def mock_get_current_user() -> CurrentUser:
        return MOCK_ADMIN_USER

    app.dependency_overrides[get_current_user] = mock_get_current_user

    # Initialize Redis
    with patch("app.cache.redis.get_settings", return_value=test_settings):
        await init_redis_pools()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await close_redis_pools()


@pytest.fixture
async def regular_user_client(
    app: FastAPI,
    test_settings: Settings,
) -> AsyncGenerator[AsyncClient]:
    """Create client with regular user for testing 403."""

    async def mock_get_current_user() -> CurrentUser:
        return MOCK_REGULAR_USER

    app.dependency_overrides[get_current_user] = mock_get_current_user

    # Initialize Redis
    with patch("app.cache.redis.get_settings", return_value=test_settings):
        await init_redis_pools()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await close_redis_pools()


class TestCacheClearEndpoint:
    """Integration tests for DELETE /admin/cache endpoint."""

    @pytest.mark.asyncio
    async def test_returns_403_for_non_admin(
        self,
        regular_user_client: AsyncClient,
    ) -> None:
        """Should return 403 for users without admin permission."""
        response = await regular_user_client.delete(
            "/api/v1/recipe-scraper/admin/cache",
        )
        assert response.status_code == 403
        data = response.json()
        assert data["message"] == "Insufficient permissions"

    @pytest.mark.asyncio
    async def test_clears_cache_with_admin_user(
        self,
        admin_cache_client: AsyncClient,
    ) -> None:
        """Should clear cache with admin authentication."""
        # Add some test data to cache
        cache_client = get_cache_client()
        await cache_client.set("test:key1", "value1")
        await cache_client.set("test:key2", "value2")

        # Verify data exists
        assert await cache_client.exists("test:key1") == 1
        assert await cache_client.exists("test:key2") == 1

        # Clear cache via endpoint
        response = await admin_cache_client.delete(
            "/api/v1/recipe-scraper/admin/cache",
        )

        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Cache cleared successfully"

        # Verify cache is empty
        assert await cache_client.exists("test:key1") == 0
        assert await cache_client.exists("test:key2") == 0

    @pytest.mark.asyncio
    async def test_cache_clear_is_idempotent(
        self,
        admin_cache_client: AsyncClient,
    ) -> None:
        """Should succeed even when cache is already empty."""
        # Clear twice
        response1 = await admin_cache_client.delete(
            "/api/v1/recipe-scraper/admin/cache",
        )
        response2 = await admin_cache_client.delete(
            "/api/v1/recipe-scraper/admin/cache",
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

    @pytest.mark.asyncio
    async def test_response_has_correct_content_type(
        self,
        admin_cache_client: AsyncClient,
    ) -> None:
        """Should return JSON response with correct content type."""
        response = await admin_cache_client.delete(
            "/api/v1/recipe-scraper/admin/cache",
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
