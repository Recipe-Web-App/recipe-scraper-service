"""End-to-end tests for /metrics Prometheus endpoint.

Tests cover full system integration including middleware stack,
response format, and metric accuracy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from httpx import AsyncClient


pytestmark = pytest.mark.e2e


class TestMetricsEndpointE2E:
    """E2E tests for metrics endpoint with full system stack."""

    @pytest.mark.asyncio
    async def test_metrics_full_middleware_stack(self, client: AsyncClient) -> None:
        """Should return metrics through full middleware stack."""
        response = await client.get("/metrics")

        assert response.status_code == 200

        # Verify middleware headers are present
        assert "x-request-id" in response.headers
        assert "x-process-time" in response.headers

    @pytest.mark.asyncio
    async def test_metrics_security_headers_present(self, client: AsyncClient) -> None:
        """Should include security headers from middleware."""
        response = await client.get("/metrics")

        assert response.status_code == 200

        # SecurityHeadersMiddleware should add these
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers

    @pytest.mark.asyncio
    async def test_metrics_records_api_requests(self, client: AsyncClient) -> None:
        """Should record metrics for API requests."""
        # Make some API requests
        await client.get("/")
        await client.get("/api/v1/recipe-scraper/health")

        # Get metrics
        response = await client.get("/metrics")
        content = response.text

        # Should have recorded endpoints
        assert response.status_code == 200
        assert "recipe_scraper" in content

    @pytest.mark.asyncio
    async def test_metrics_request_duration_histogram(
        self, client: AsyncClient
    ) -> None:
        """Should include request duration histogram."""
        await client.get("/")

        response = await client.get("/metrics")
        content = response.text

        # Should contain duration metrics (histogram type)
        assert response.status_code == 200
        # The default metrics include duration histogram
        assert "duration" in content.lower() or "latency" in content.lower()

    @pytest.mark.asyncio
    async def test_metrics_request_counter(self, client: AsyncClient) -> None:
        """Should include request counter metrics."""
        # Make multiple requests
        for _ in range(3):
            await client.get("/")

        response = await client.get("/metrics")
        content = response.text

        assert response.status_code == 200
        # Should contain counter metrics (total suffix or count)
        assert "total" in content.lower() or "count" in content.lower()

    @pytest.mark.asyncio
    async def test_metrics_no_authentication_required(
        self, client: AsyncClient
    ) -> None:
        """Should be accessible without authentication."""
        # Don't set any auth headers
        response = await client.get("/metrics")

        # Should succeed without auth
        assert response.status_code == 200
        assert "# HELP" in response.text

    @pytest.mark.asyncio
    async def test_metrics_inprogress_gauge(self, client: AsyncClient) -> None:
        """Should include in-progress request gauge."""
        response = await client.get("/metrics")
        content = response.text

        assert response.status_code == 200
        assert "inprogress" in content.lower()

    @pytest.mark.asyncio
    async def test_metrics_request_id_tracking(self, client: AsyncClient) -> None:
        """Should include request ID for tracing."""
        response = await client.get("/metrics")

        assert response.status_code == 200

        # RequestIDMiddleware should add this
        request_id = response.headers.get("x-request-id")
        assert request_id is not None
        assert len(request_id) > 0

    @pytest.mark.asyncio
    async def test_multiple_metrics_requests_succeed(self, client: AsyncClient) -> None:
        """Should handle multiple sequential requests."""
        for _ in range(5):
            response = await client.get("/metrics")
            assert response.status_code == 200
            assert "# HELP" in response.text

    @pytest.mark.asyncio
    async def test_metrics_response_is_not_empty(self, client: AsyncClient) -> None:
        """Should return non-empty metrics response."""
        response = await client.get("/metrics")

        assert response.status_code == 200
        content = response.text

        # Response should have meaningful content
        assert len(content) > 100  # At minimum, has several metric definitions
        assert content.strip()  # Not just whitespace
