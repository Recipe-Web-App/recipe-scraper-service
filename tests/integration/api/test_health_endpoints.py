"""Integration tests for health API endpoints.

Tests cover:
- Health check endpoint
- Readiness check endpoint with Redis status
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from httpx import AsyncClient


pytestmark = pytest.mark.integration


class TestHealthEndpoint:
    """Tests for GET /health."""

    @pytest.mark.asyncio
    async def test_health_returns_healthy(self, client: AsyncClient) -> None:
        """Should return healthy status."""
        response = await client.get("/api/v1/recipe-scraper/health")

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data
        assert "timestamp" in data


class TestReadinessEndpoint:
    """Tests for GET /ready."""

    @pytest.mark.asyncio
    async def test_ready_returns_status(self, client: AsyncClient) -> None:
        """Should return readiness status with dependencies."""
        response = await client.get("/api/v1/recipe-scraper/ready")

        assert response.status_code == 200

        data = response.json()
        assert data["status"] in ("ready", "degraded")
        assert "dependencies" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_ready_includes_redis_status(self, client: AsyncClient) -> None:
        """Should include Redis status in dependencies."""
        response = await client.get("/api/v1/recipe-scraper/ready")

        data = response.json()
        dependencies = data["dependencies"]

        # Should have Redis-related keys
        assert any("redis" in key for key in dependencies)


class TestRootEndpoint:
    """Tests for GET /."""

    @pytest.mark.asyncio
    async def test_root_returns_service_info(self, client: AsyncClient) -> None:
        """Should return basic service information."""
        response = await client.get("/api/v1/recipe-scraper/")

        assert response.status_code == 200

        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "status" in data
        assert "docs" in data
        assert "health" in data

    @pytest.mark.asyncio
    async def test_root_status_is_operational(self, client: AsyncClient) -> None:
        """Should return operational status."""
        response = await client.get("/api/v1/recipe-scraper/")

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "operational"

    @pytest.mark.asyncio
    async def test_root_health_url_is_valid(self, client: AsyncClient) -> None:
        """Should return valid health endpoint URL."""
        response = await client.get("/api/v1/recipe-scraper/")

        assert response.status_code == 200

        data = response.json()
        health_url = data["health"]

        # Verify health URL points to working endpoint
        health_response = await client.get(health_url)
        assert health_response.status_code == 200
        assert health_response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_root_response_has_correct_structure(
        self,
        client: AsyncClient,
    ) -> None:
        """Should return response with correct field types."""
        response = await client.get("/api/v1/recipe-scraper/")

        assert response.status_code == 200

        data = response.json()
        assert isinstance(data["service"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["status"], str)
        assert isinstance(data["docs"], str)
        assert isinstance(data["health"], str)
