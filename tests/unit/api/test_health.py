"""Unit tests for health endpoints.

Tests cover:
- Health check endpoint
- Readiness check endpoint
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.api.v1.endpoints.health import health_check, readiness_check


pytestmark = pytest.mark.unit


class TestHealthCheck:
    """Tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_returns_healthy_status(self) -> None:
        """Should return healthy status."""
        mock_settings = MagicMock()
        mock_settings.APP_VERSION = "1.0.0"
        mock_settings.ENVIRONMENT = "test"

        result = await health_check(mock_settings)

        assert result.status == "healthy"
        assert result.version == "1.0.0"
        assert result.environment == "test"

    @pytest.mark.asyncio
    async def test_includes_timestamp(self) -> None:
        """Should include timestamp in response."""
        mock_settings = MagicMock()
        mock_settings.APP_VERSION = "1.0.0"
        mock_settings.ENVIRONMENT = "test"

        result = await health_check(mock_settings)

        assert result.timestamp is not None


class TestReadinessCheck:
    """Tests for readiness check endpoint."""

    @pytest.mark.asyncio
    async def test_returns_ready_when_all_healthy(self) -> None:
        """Should return ready status when all dependencies healthy."""
        mock_settings = MagicMock()
        mock_settings.APP_VERSION = "1.0.0"
        mock_settings.ENVIRONMENT = "test"

        with patch(
            "app.api.v1.endpoints.health.check_redis_health",
            return_value={"redis": "healthy"},
        ):
            result = await readiness_check(mock_settings)

        assert result.status == "ready"
        assert result.dependencies == {"redis": "healthy"}

    @pytest.mark.asyncio
    async def test_returns_ready_when_not_initialized(self) -> None:
        """Should return ready status when dependencies not initialized."""
        mock_settings = MagicMock()
        mock_settings.APP_VERSION = "1.0.0"
        mock_settings.ENVIRONMENT = "test"

        with patch(
            "app.api.v1.endpoints.health.check_redis_health",
            return_value={"redis": "not_initialized"},
        ):
            result = await readiness_check(mock_settings)

        assert result.status == "ready"

    @pytest.mark.asyncio
    async def test_returns_degraded_when_unhealthy(self) -> None:
        """Should return degraded status when dependencies unhealthy."""
        mock_settings = MagicMock()
        mock_settings.APP_VERSION = "1.0.0"
        mock_settings.ENVIRONMENT = "test"

        with patch(
            "app.api.v1.endpoints.health.check_redis_health",
            return_value={"redis": "unhealthy"},
        ):
            result = await readiness_check(mock_settings)

        assert result.status == "degraded"
        assert result.dependencies == {"redis": "unhealthy"}
