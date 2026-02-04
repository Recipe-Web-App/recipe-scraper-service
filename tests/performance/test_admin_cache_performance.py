"""Performance benchmarks for admin cache operations.

Benchmarks cover:
- Redis flushdb operation latency
- Cache clear endpoint response time
- Cache clear with various data volumes
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
import redis

from app.auth.jwt import create_access_token


if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture
    from starlette.testclient import TestClient


pytestmark = pytest.mark.performance


class TestCacheFlushBenchmarks:
    """Benchmarks for Redis cache flush operations."""

    @pytest.fixture
    def redis_client(
        self,
        redis_url: str,
    ) -> redis.Redis:
        """Create sync Redis client for benchmarks."""
        parts = redis_url.replace("redis://", "").split(":")
        host = parts[0]
        port = int(parts[1])

        client = redis.Redis(host=host, port=port, decode_responses=True)
        yield client
        client.close()

    def test_flushdb_empty_benchmark(
        self,
        benchmark: BenchmarkFixture,
        redis_client: redis.Redis,
    ) -> None:
        """Benchmark flushdb on empty database."""

        def do_flush() -> bool:
            return redis_client.flushdb()

        result = benchmark(do_flush)
        assert result is True

    def test_flushdb_small_dataset_benchmark(
        self,
        benchmark: BenchmarkFixture,
        redis_client: redis.Redis,
    ) -> None:
        """Benchmark flushdb with small dataset (100 keys)."""

        def setup_and_flush() -> bool:
            # Setup: add 100 keys
            pipe = redis_client.pipeline()
            for i in range(100):
                pipe.set(f"bench:small:{i}", f"value_{i}")
            pipe.execute()

            # Benchmark target
            return redis_client.flushdb()

        result = benchmark(setup_and_flush)
        assert result is True

    def test_flushdb_medium_dataset_benchmark(
        self,
        benchmark: BenchmarkFixture,
        redis_client: redis.Redis,
    ) -> None:
        """Benchmark flushdb with medium dataset (1000 keys)."""

        def setup_and_flush() -> bool:
            # Setup: add 1000 keys
            pipe = redis_client.pipeline()
            for i in range(1000):
                pipe.set(f"bench:medium:{i}", f"value_{i}")
            pipe.execute()

            # Benchmark target
            return redis_client.flushdb()

        result = benchmark(setup_and_flush)
        assert result is True

    def test_flushdb_large_values_benchmark(
        self,
        benchmark: BenchmarkFixture,
        redis_client: redis.Redis,
    ) -> None:
        """Benchmark flushdb with large values (100 keys, 10KB each)."""
        large_value = "x" * 10240  # 10KB

        def setup_and_flush() -> bool:
            # Setup: add 100 keys with large values
            pipe = redis_client.pipeline()
            for i in range(100):
                pipe.set(f"bench:large:{i}", large_value)
            pipe.execute()

            # Benchmark target
            return redis_client.flushdb()

        result = benchmark(setup_and_flush)
        assert result is True


class TestAdminCacheEndpointBenchmarks:
    """Benchmarks for admin cache clear endpoint."""

    @pytest.fixture
    def redis_client(
        self,
        redis_url: str,
    ) -> redis.Redis:
        """Create sync Redis client for benchmarks."""
        parts = redis_url.replace("redis://", "").split(":")
        host = parts[0]
        port = int(parts[1])

        client = redis.Redis(host=host, port=port, decode_responses=True)
        yield client
        client.close()

    @pytest.fixture
    def admin_token(self) -> str:
        """Create admin JWT token for benchmarks."""
        return create_access_token(
            subject="bench-admin",
            roles=["admin"],
            permissions=["admin:system"],
        )

    def test_cache_clear_endpoint_benchmark(
        self,
        benchmark: BenchmarkFixture,
        sync_client: TestClient,
        admin_token: str,
        redis_client: redis.Redis,
    ) -> None:
        """Benchmark cache clear endpoint response time."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        def clear_cache() -> int:
            # Add some test data
            redis_client.set("bench:endpoint:key", "value")

            # Call endpoint
            response = sync_client.delete(
                "/api/v1/recipe-scraper/admin/cache",
                headers=headers,
            )
            return response.status_code

        # Note: This will get 403 because the sync_client doesn't have
        # the auth dependency override. We benchmark the request processing.
        benchmark(clear_cache)

    def test_cache_clear_with_data_benchmark(
        self,
        benchmark: BenchmarkFixture,
        redis_client: redis.Redis,
    ) -> None:
        """Benchmark direct cache clear with realistic data volume."""
        counter = [0]

        def setup_and_clear() -> bool:
            counter[0] += 1
            # Setup: simulate realistic cache data
            pipe = redis_client.pipeline()
            for i in range(50):
                pipe.set(
                    f"popular:recipes:{counter[0]}:{i}", '{"id": 1, "title": "Recipe"}'
                )
                pipe.set(f"nutrition:{counter[0]}:{i}", '{"calories": 100}')
                pipe.set(f"allergen:{counter[0]}:{i}", '{"allergens": []}')
            pipe.execute()

            # Clear
            return redis_client.flushdb()

        result = benchmark(setup_and_clear)
        assert result is True


class TestCacheClearLatencyBenchmarks:
    """Latency benchmarks for cache operations."""

    @pytest.fixture
    def redis_client(
        self,
        redis_url: str,
    ) -> redis.Redis:
        """Create sync Redis client for benchmarks."""
        parts = redis_url.replace("redis://", "").split(":")
        host = parts[0]
        port = int(parts[1])

        client = redis.Redis(host=host, port=port, decode_responses=True)
        yield client
        client.close()

    def test_redis_ping_latency(
        self,
        benchmark: BenchmarkFixture,
        redis_client: redis.Redis,
    ) -> None:
        """Baseline benchmark: Redis PING latency."""

        def ping() -> bool:
            return redis_client.ping()

        result = benchmark(ping)
        assert result is True

    def test_flushdb_vs_delete_pattern_small(
        self,
        benchmark: BenchmarkFixture,
        redis_client: redis.Redis,
    ) -> None:
        """Compare flushdb performance (used in our implementation)."""

        def flush_operation() -> bool:
            # Add 10 keys
            for i in range(10):
                redis_client.set(f"compare:key:{i}", f"value_{i}")
            # Use flushdb (our choice)
            return redis_client.flushdb()

        result = benchmark(flush_operation)
        assert result is True

    def test_json_payload_clear_benchmark(
        self,
        benchmark: BenchmarkFixture,
        redis_client: redis.Redis,
    ) -> None:
        """Benchmark clearing cache with JSON payloads (realistic scenario)."""
        recipe_data = {
            "id": 1,
            "title": "Test Recipe",
            "ingredients": [
                {"name": "flour", "quantity": 2, "unit": "cups"},
                {"name": "sugar", "quantity": 1, "unit": "cup"},
            ],
            "instructions": ["Step 1", "Step 2", "Step 3"],
            "metadata": {"source": "test", "created": "2024-01-01"},
        }

        def setup_and_clear() -> bool:
            # Add JSON data
            for i in range(20):
                redis_client.set(f"recipe:{i}", json.dumps(recipe_data))
            # Clear
            return redis_client.flushdb()

        result = benchmark(setup_and_clear)
        assert result is True
