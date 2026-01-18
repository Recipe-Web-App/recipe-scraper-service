"""Integration tests for /metrics Prometheus endpoint.

Tests cover:
- Endpoint accessibility
- Prometheus format response
- Correct content type
- Metrics registration and updates
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from httpx import AsyncClient


pytestmark = pytest.mark.integration


class TestMetricsEndpoint:
    """Tests for GET /metrics."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_accessible(self, client: AsyncClient) -> None:
        """Should return 200 status code."""
        response = await client.get("/metrics")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_metrics_returns_prometheus_format(self, client: AsyncClient) -> None:
        """Should return valid Prometheus metrics format."""
        response = await client.get("/metrics")

        assert response.status_code == 200
        content = response.text

        # Prometheus format includes HELP and TYPE comments
        assert "# HELP" in content
        assert "# TYPE" in content

    @pytest.mark.asyncio
    async def test_metrics_content_type_is_text_plain(
        self, client: AsyncClient
    ) -> None:
        """Should return text/plain content type."""
        response = await client.get("/metrics")

        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "text/plain" in content_type

    @pytest.mark.asyncio
    async def test_metrics_contains_http_metrics(self, client: AsyncClient) -> None:
        """Should contain HTTP request metrics with recipe_scraper namespace."""
        # Make a request to generate metrics
        await client.get("/")

        response = await client.get("/metrics")
        content = response.text

        # Should contain recipe_scraper namespace metrics
        assert "recipe_scraper_http" in content

    @pytest.mark.asyncio
    async def test_metrics_excludes_metrics_endpoint_from_instrumentation(
        self, client: AsyncClient
    ) -> None:
        """Should not instrument the /metrics endpoint itself."""
        # Make multiple requests to /metrics
        for _ in range(5):
            await client.get("/metrics")

        response = await client.get("/metrics")
        content = response.text

        # The /metrics endpoint should not appear in handler labels
        # (it's in excluded_handlers)
        assert 'handler="/metrics"' not in content

    @pytest.mark.asyncio
    async def test_metrics_records_after_api_request(self, client: AsyncClient) -> None:
        """Should record metrics after API requests are made."""
        # Make requests to various endpoints
        await client.get("/")
        await client.get("/api/v1/recipe-scraper/health")

        response = await client.get("/metrics")
        content = response.text

        # Should have recorded requests (counter or histogram present)
        assert "recipe_scraper" in content
        # Should have HTTP-related metrics
        assert "http" in content.lower()
