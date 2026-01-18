"""Performance benchmarks for /metrics endpoint.

Benchmarks cover:
- Metrics endpoint response time
- Throughput under load
- Response size characteristics

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


class TestMetricsEndpointBenchmarks:
    """Benchmarks for metrics endpoint performance."""

    def test_metrics_endpoint_response_time(
        self,
        benchmark: BenchmarkFixture,
        sync_client: TestClient,
    ) -> None:
        """Benchmark metrics endpoint response time."""

        def fetch_metrics() -> str:
            response = sync_client.get("/metrics")
            return response.text

        result = benchmark(fetch_metrics)
        assert "# HELP" in result

    def test_metrics_endpoint_status_code(
        self,
        benchmark: BenchmarkFixture,
        sync_client: TestClient,
    ) -> None:
        """Benchmark metrics endpoint status code check."""

        def check_status() -> int:
            response = sync_client.get("/metrics")
            return response.status_code

        result = benchmark(check_status)
        assert result == 200

    def test_metrics_endpoint_throughput(
        self,
        benchmark: BenchmarkFixture,
        sync_client: TestClient,
    ) -> None:
        """Benchmark metrics endpoint for high throughput scenarios."""

        def fetch_multiple() -> int:
            success_count = 0
            for _ in range(10):
                response = sync_client.get("/metrics")
                if response.status_code == 200:
                    success_count += 1
            return success_count

        result = benchmark(fetch_multiple)
        assert result == 10

    def test_metrics_after_api_traffic(
        self,
        benchmark: BenchmarkFixture,
        sync_client: TestClient,
    ) -> None:
        """Benchmark metrics endpoint after generating API traffic."""
        # Generate some API traffic first
        for _ in range(100):
            sync_client.get("/")

        def fetch_metrics() -> str:
            response = sync_client.get("/metrics")
            return response.text

        result = benchmark(fetch_metrics)
        assert "recipe_scraper" in result

    def test_metrics_content_size(
        self,
        benchmark: BenchmarkFixture,
        sync_client: TestClient,
    ) -> None:
        """Benchmark metrics response size."""

        def fetch_and_measure() -> int:
            response = sync_client.get("/metrics")
            return len(response.content)

        result = benchmark(fetch_and_measure)
        # Metrics response should be reasonable size
        assert result > 0

    def test_metrics_endpoint_headers_check(
        self,
        benchmark: BenchmarkFixture,
        sync_client: TestClient,
    ) -> None:
        """Benchmark metrics endpoint with header verification."""

        def fetch_with_headers() -> tuple[int, bool, bool]:
            response = sync_client.get("/metrics")
            has_request_id = "x-request-id" in response.headers
            has_process_time = "x-process-time" in response.headers
            return response.status_code, has_request_id, has_process_time

        result = benchmark(fetch_with_headers)
        status_code, has_request_id, has_process_time = result
        assert status_code == 200
        assert has_request_id
        assert has_process_time

    def test_metrics_prometheus_format_validation(
        self,
        benchmark: BenchmarkFixture,
        sync_client: TestClient,
    ) -> None:
        """Benchmark fetching and validating Prometheus format."""

        def fetch_and_validate() -> tuple[bool, bool]:
            response = sync_client.get("/metrics")
            content = response.text
            has_help = "# HELP" in content
            has_type = "# TYPE" in content
            return has_help, has_type

        result = benchmark(fetch_and_validate)
        has_help, has_type = result
        assert has_help
        assert has_type
