"""Performance benchmarks for root endpoint.

Benchmarks cover:
- Root endpoint response time
- Throughput under load
- Response parsing overhead

Note: Uses synchronous HTTP client to avoid event loop
conflicts with pytest-benchmark.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture
    from starlette.testclient import TestClient


pytestmark = pytest.mark.performance


class TestRootEndpointBenchmarks:
    """Benchmarks for root endpoint performance."""

    def test_root_endpoint_response_time(
        self,
        benchmark: BenchmarkFixture,
        sync_client: TestClient,
    ) -> None:
        """Benchmark root endpoint response time."""

        def fetch_root() -> dict:
            response = sync_client.get("/api/v1/recipe-scraper/")
            return response.json()

        result = benchmark(fetch_root)
        assert result["status"] == "operational"

    def test_root_endpoint_status_code(
        self,
        benchmark: BenchmarkFixture,
        sync_client: TestClient,
    ) -> None:
        """Benchmark root endpoint status code check."""

        def check_status() -> int:
            response = sync_client.get("/api/v1/recipe-scraper/")
            return response.status_code

        result = benchmark(check_status)
        assert result == 200

    def test_root_endpoint_throughput(
        self,
        benchmark: BenchmarkFixture,
        sync_client: TestClient,
    ) -> None:
        """Benchmark root endpoint for high throughput scenarios."""

        def fetch_multiple() -> int:
            success_count = 0
            for _ in range(10):
                response = sync_client.get("/api/v1/recipe-scraper/")
                if response.status_code == 200:
                    success_count += 1
            return success_count

        result = benchmark(fetch_multiple)
        assert result == 10

    def test_root_endpoint_json_parsing(
        self,
        benchmark: BenchmarkFixture,
        sync_client: TestClient,
    ) -> None:
        """Benchmark JSON parsing overhead for root response."""

        def fetch_and_parse() -> tuple[str, str, str]:
            response = sync_client.get("/api/v1/recipe-scraper/")
            data = response.json()
            return data["service"], data["version"], data["status"]

        result = benchmark(fetch_and_parse)
        assert result[2] == "operational"

    def test_root_endpoint_headers_check(
        self,
        benchmark: BenchmarkFixture,
        sync_client: TestClient,
    ) -> None:
        """Benchmark root endpoint with header verification."""

        def fetch_with_headers() -> tuple[int, bool, bool]:
            response = sync_client.get("/api/v1/recipe-scraper/")
            has_request_id = "x-request-id" in response.headers
            has_process_time = "x-process-time" in response.headers
            return response.status_code, has_request_id, has_process_time

        result = benchmark(fetch_with_headers)
        status_code, has_request_id, has_process_time = result
        assert status_code == 200
        assert has_request_id
        assert has_process_time

    def test_root_then_health_navigation(
        self,
        benchmark: BenchmarkFixture,
        sync_client: TestClient,
    ) -> None:
        """Benchmark navigating from root to health endpoint."""

        def navigate_to_health() -> tuple[str, str]:
            root_response = sync_client.get("/api/v1/recipe-scraper/")
            health_url = root_response.json()["health"]
            health_response = sync_client.get(health_url)
            return root_response.json()["status"], health_response.json()["status"]

        result = benchmark(navigate_to_health)
        assert result[0] == "operational"
        assert result[1] == "healthy"
