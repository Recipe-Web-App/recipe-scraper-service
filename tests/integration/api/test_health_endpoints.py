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
        response = await client.get("/api/v1/health")

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
        response = await client.get("/api/v1/ready")

        assert response.status_code == 200

        data = response.json()
        assert data["status"] in ("ready", "degraded")
        assert "dependencies" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_ready_includes_redis_status(self, client: AsyncClient) -> None:
        """Should include Redis status in dependencies."""
        response = await client.get("/api/v1/ready")

        data = response.json()
        dependencies = data["dependencies"]

        # Should have Redis-related keys
        assert any("redis" in key for key in dependencies)


class TestRootEndpoint:
    """Tests for GET /."""

    @pytest.mark.asyncio
    async def test_root_returns_service_info(self, client: AsyncClient) -> None:
        """Should return basic service information."""
        response = await client.get("/")

        assert response.status_code == 200

        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "docs" in data
