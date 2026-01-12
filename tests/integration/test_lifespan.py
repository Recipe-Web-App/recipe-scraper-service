"""Integration tests for application lifespan events.

Tests cover:
- Application startup initialization
- Redis pool initialization during startup
- Application shutdown cleanup
- Graceful handling of unavailable services
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient

import app.cache.redis as redis_module
from app.core.config.settings import RedisSettings
from app.factory import create_app


if TYPE_CHECKING:
    from app.core.config import Settings


pytestmark = pytest.mark.integration


class TestApplicationStartup:
    """Tests for application startup behavior."""

    @pytest.mark.asyncio
    async def test_app_starts_successfully(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> None:
        """Should start application and respond to requests."""

        app = create_app(test_settings)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_ready_endpoint_returns_dependencies(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> None:
        """Should return dependency status in ready endpoint."""

        app = create_app(test_settings)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/recipe-scraper/ready")
            data = response.json()

            # Ready endpoint should return status and dependencies
            assert "status" in data
            assert "dependencies" in data
            assert data["status"] in ("ready", "degraded")

    @pytest.mark.asyncio
    async def test_app_continues_without_redis(
        self,
        test_settings: Settings,
    ) -> None:
        """Should start even if Redis is unavailable."""
        # Create settings with invalid Redis host
        invalid_redis_settings = test_settings.model_copy(
            update={"redis": RedisSettings(host="invalid-host", port=9999)}
        )

        app = create_app(invalid_redis_settings)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # App should still respond
            response = await client.get("/")
            assert response.status_code == 200

            # Health check should show degraded status
            response = await client.get("/api/v1/recipe-scraper/ready")
            data = response.json()
            # App may be degraded but should still respond
            assert data["status"] in ("ready", "degraded")


class TestApplicationShutdown:
    """Tests for application shutdown behavior."""

    @pytest.mark.asyncio
    async def test_multiple_startup_shutdown_cycles(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> None:
        """Should handle multiple startup/shutdown cycles cleanly."""

        # Run multiple cycles
        for _ in range(3):
            app = create_app(test_settings)

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/")
                assert response.status_code == 200

            # Reset module state between cycles
            redis_module._cache_pool = None
            redis_module._queue_pool = None
            redis_module._rate_limit_pool = None
            redis_module._cache_client = None
            redis_module._queue_client = None
            redis_module._rate_limit_client = None


class TestLifespanGracefulDegradation:
    """Tests for graceful degradation when services are unavailable."""

    @pytest.mark.asyncio
    async def test_app_responds_in_degraded_state(
        self,
        test_settings: Settings,
    ) -> None:
        """Should respond to requests even when dependencies unavailable."""
        # Create settings with invalid Redis to force degraded state
        invalid_redis_settings = test_settings.model_copy(
            update={"redis": RedisSettings(host="invalid-host", port=9999)}
        )

        app = create_app(invalid_redis_settings)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Root endpoint should work
            response = await client.get("/")
            assert response.status_code == 200

            # Health endpoint should work
            response = await client.get("/api/v1/recipe-scraper/health")
            assert response.status_code == 200

            # Ready endpoint should return degraded but not error
            response = await client.get("/api/v1/recipe-scraper/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ("ready", "degraded")
