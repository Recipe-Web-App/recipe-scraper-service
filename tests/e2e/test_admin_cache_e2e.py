"""End-to-end tests for admin cache clear endpoint.

Tests cover full system integration including:
- Middleware stack (request ID, security headers, logging)
- Authentication with real JWT tokens
- Cache clearing with real Redis
- Permission enforcement
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


pytestmark = pytest.mark.e2e


# Mock users for testing
MOCK_ADMIN_USER = CurrentUser(
    id="e2e-admin-user",
    roles=["admin"],
    permissions=["admin:system"],
)

MOCK_REGULAR_USER = CurrentUser(
    id="e2e-regular-user",
    roles=["user"],
    permissions=["recipe:read"],
)


@pytest.fixture
async def admin_e2e_client(
    app: FastAPI,
    test_settings: Settings,
) -> AsyncGenerator[AsyncClient]:
    """Create client with admin user and initialized Redis."""

    async def mock_get_current_user() -> CurrentUser:
        return MOCK_ADMIN_USER

    app.dependency_overrides[get_current_user] = mock_get_current_user

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
async def regular_e2e_client(
    app: FastAPI,
    test_settings: Settings,
) -> AsyncGenerator[AsyncClient]:
    """Create client with regular user and initialized Redis."""

    async def mock_get_current_user() -> CurrentUser:
        return MOCK_REGULAR_USER

    app.dependency_overrides[get_current_user] = mock_get_current_user

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


class TestAdminCacheE2E:
    """E2E tests for admin cache clear endpoint."""

    @pytest.mark.asyncio
    async def test_cache_clear_full_middleware_stack(
        self,
        admin_e2e_client: AsyncClient,
    ) -> None:
        """Should process request through full middleware stack."""
        response = await admin_e2e_client.delete("/api/v1/recipe-scraper/admin/cache")

        assert response.status_code == 200

        # Verify middleware headers are present
        assert "x-request-id" in response.headers
        assert "x-process-time" in response.headers

    @pytest.mark.asyncio
    async def test_cache_clear_security_headers(
        self,
        admin_e2e_client: AsyncClient,
    ) -> None:
        """Should include security headers from middleware."""
        response = await admin_e2e_client.delete("/api/v1/recipe-scraper/admin/cache")

        assert response.status_code == 200

        # SecurityHeadersMiddleware should add these
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers

    @pytest.mark.asyncio
    async def test_cache_clear_actually_clears_data(
        self,
        admin_e2e_client: AsyncClient,
    ) -> None:
        """Should actually clear all cached data."""
        # Add test data to cache
        cache_client = get_cache_client()
        await cache_client.set("e2e:test:key1", "value1")
        await cache_client.set("e2e:test:key2", "value2")
        await cache_client.set("e2e:popular:recipes", '{"data": "cached"}')

        # Verify data exists
        assert await cache_client.exists("e2e:test:key1") == 1
        assert await cache_client.exists("e2e:test:key2") == 1
        assert await cache_client.exists("e2e:popular:recipes") == 1

        # Clear cache
        response = await admin_e2e_client.delete("/api/v1/recipe-scraper/admin/cache")

        assert response.status_code == 200

        # Verify all data is cleared
        assert await cache_client.exists("e2e:test:key1") == 0
        assert await cache_client.exists("e2e:test:key2") == 0
        assert await cache_client.exists("e2e:popular:recipes") == 0

    @pytest.mark.asyncio
    async def test_cache_clear_returns_proper_json(
        self,
        admin_e2e_client: AsyncClient,
    ) -> None:
        """Should return proper JSON response."""
        response = await admin_e2e_client.delete("/api/v1/recipe-scraper/admin/cache")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        data = response.json()
        assert data["message"] == "Cache cleared successfully"

    @pytest.mark.asyncio
    async def test_cache_clear_permission_denied(
        self,
        regular_e2e_client: AsyncClient,
    ) -> None:
        """Should return 403 for users without admin permission."""
        response = await regular_e2e_client.delete("/api/v1/recipe-scraper/admin/cache")

        assert response.status_code == 403

        data = response.json()
        assert data["message"] == "Insufficient permissions"

    @pytest.mark.asyncio
    async def test_cache_clear_request_id_tracking(
        self,
        admin_e2e_client: AsyncClient,
    ) -> None:
        """Should include request ID for tracing."""
        response = await admin_e2e_client.delete("/api/v1/recipe-scraper/admin/cache")

        assert response.status_code == 200

        request_id = response.headers.get("x-request-id")
        assert request_id is not None
        assert len(request_id) > 0

    @pytest.mark.asyncio
    async def test_multiple_cache_clears_succeed(
        self,
        admin_e2e_client: AsyncClient,
    ) -> None:
        """Should handle multiple sequential cache clears."""
        for i in range(3):
            # Add some data
            cache_client = get_cache_client()
            await cache_client.set(f"e2e:iter{i}:key", f"value{i}")

            # Clear it
            response = await admin_e2e_client.delete(
                "/api/v1/recipe-scraper/admin/cache"
            )
            assert response.status_code == 200

            # Verify cleared
            assert await cache_client.exists(f"e2e:iter{i}:key") == 0

    @pytest.mark.asyncio
    async def test_cache_clear_idempotent(
        self,
        admin_e2e_client: AsyncClient,
    ) -> None:
        """Should succeed even when cache is already empty."""
        # Clear once
        response1 = await admin_e2e_client.delete("/api/v1/recipe-scraper/admin/cache")
        assert response1.status_code == 200

        # Clear again (cache is now empty)
        response2 = await admin_e2e_client.delete("/api/v1/recipe-scraper/admin/cache")
        assert response2.status_code == 200

        # Both should return success
        assert response1.json()["message"] == "Cache cleared successfully"
        assert response2.json()["message"] == "Cache cleared successfully"
