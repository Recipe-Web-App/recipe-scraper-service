"""End-to-end tests for root endpoint.

Tests cover full system integration including middleware stack,
navigation to linked endpoints, and response validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from httpx import AsyncClient


pytestmark = pytest.mark.e2e


class TestRootEndpointE2E:
    """E2E tests for root endpoint with full system stack."""

    @pytest.mark.asyncio
    async def test_root_endpoint_full_stack(self, client: AsyncClient) -> None:
        """Should return service info through full middleware stack."""
        response = await client.get("/api/v1/recipe-scraper/")

        assert response.status_code == 200

        # Verify middleware headers are present
        assert "x-request-id" in response.headers
        assert "x-process-time" in response.headers

        data = response.json()
        assert data["status"] == "operational"
        assert "service" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_root_to_health_navigation(self, client: AsyncClient) -> None:
        """Should be able to navigate from root to health endpoint."""
        # Get root
        root_response = await client.get("/api/v1/recipe-scraper/")
        assert root_response.status_code == 200

        # Navigate to health
        health_url = root_response.json()["health"]
        health_response = await client.get(health_url)

        assert health_response.status_code == 200
        assert health_response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_root_service_info_has_valid_values(
        self,
        client: AsyncClient,
    ) -> None:
        """Should return non-empty service info values."""
        response = await client.get("/api/v1/recipe-scraper/")

        assert response.status_code == 200

        data = response.json()
        # Verify service info is populated (not empty)
        assert len(data["service"]) > 0
        assert len(data["version"]) > 0

    @pytest.mark.asyncio
    async def test_root_docs_reports_availability(
        self,
        client: AsyncClient,
    ) -> None:
        """Should report docs availability as either URL or disabled."""
        response = await client.get("/api/v1/recipe-scraper/")

        assert response.status_code == 200

        data = response.json()
        # docs should be either prefixed URL or "disabled" based on environment
        assert data["docs"] in ("/api/v1/recipe-scraper/docs", "disabled")

    @pytest.mark.asyncio
    async def test_root_health_url_format(self, client: AsyncClient) -> None:
        """Should return properly formatted health URL."""
        response = await client.get("/api/v1/recipe-scraper/")

        assert response.status_code == 200

        data = response.json()
        health_url = data["health"]

        # Should start with API prefix
        assert health_url.startswith("/api/v1/")
        assert health_url.endswith("/health")

    @pytest.mark.asyncio
    async def test_root_response_json_format(self, client: AsyncClient) -> None:
        """Should return properly formatted JSON response."""
        response = await client.get("/api/v1/recipe-scraper/")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        # Should parse as valid JSON with expected keys
        data = response.json()
        expected_keys = {"service", "version", "status", "docs", "health"}
        assert set(data.keys()) == expected_keys

    @pytest.mark.asyncio
    async def test_root_security_headers_present(
        self,
        client: AsyncClient,
    ) -> None:
        """Should include security headers from middleware."""
        response = await client.get("/api/v1/recipe-scraper/")

        assert response.status_code == 200

        # SecurityHeadersMiddleware should add these
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers

    @pytest.mark.asyncio
    async def test_root_request_id_tracking(self, client: AsyncClient) -> None:
        """Should include request ID for tracing."""
        response = await client.get("/api/v1/recipe-scraper/")

        assert response.status_code == 200

        # RequestIDMiddleware should add this
        request_id = response.headers.get("x-request-id")
        assert request_id is not None
        assert len(request_id) > 0

    @pytest.mark.asyncio
    async def test_multiple_root_requests_succeed(
        self,
        client: AsyncClient,
    ) -> None:
        """Should handle multiple sequential requests."""
        for _ in range(5):
            response = await client.get("/api/v1/recipe-scraper/")
            assert response.status_code == 200
            assert response.json()["status"] == "operational"
