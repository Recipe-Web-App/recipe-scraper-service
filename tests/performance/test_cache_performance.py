"""Performance benchmarks for cache operations.

Benchmarks cover:
- CacheManager operations with real Redis
- Cache decorator overhead
- Serialization performance

Note: These benchmarks use synchronous Redis client to avoid event loop
conflicts with pytest-benchmark.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
import redis

from app.auth.jwt import create_access_token, decode_token


if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture


pytestmark = pytest.mark.performance


class TestRedisBenchmarks:
    """Benchmarks for Redis operations using sync client."""

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

    def test_redis_set_benchmark(
        self,
        benchmark: BenchmarkFixture,
        redis_client: redis.Redis,
    ) -> None:
        """Benchmark Redis SET operations."""
        counter = [0]

        def do_set() -> bool:
            counter[0] += 1
            return redis_client.set(
                f"bench_key_{counter[0]}",
                f"value_{counter[0]}",
            )

        result = benchmark(do_set)
        assert result is True

    def test_redis_get_benchmark(
        self,
        benchmark: BenchmarkFixture,
        redis_client: redis.Redis,
    ) -> None:
        """Benchmark Redis GET operations."""
        redis_client.set("bench_get_key", "cached_data")

        def do_get() -> str | None:
            return redis_client.get("bench_get_key")

        result = benchmark(do_get)
        assert result == "cached_data"

        redis_client.delete("bench_get_key")

    def test_redis_exists_benchmark(
        self,
        benchmark: BenchmarkFixture,
        redis_client: redis.Redis,
    ) -> None:
        """Benchmark Redis EXISTS operations."""
        redis_client.set("bench_exists_key", "value")

        def do_exists() -> int:
            return redis_client.exists("bench_exists_key")

        result = benchmark(do_exists)
        assert result == 1

        redis_client.delete("bench_exists_key")

    def test_redis_delete_benchmark(
        self,
        benchmark: BenchmarkFixture,
        redis_client: redis.Redis,
    ) -> None:
        """Benchmark Redis DELETE operations."""
        counter = [0]

        def do_delete() -> int:
            counter[0] += 1
            key = f"bench_del_{counter[0]}"
            redis_client.set(key, "value")
            return redis_client.delete(key)

        result = benchmark(do_delete)
        assert result == 1

    def test_redis_ping_benchmark(
        self,
        benchmark: BenchmarkFixture,
        redis_client: redis.Redis,
    ) -> None:
        """Benchmark Redis PING latency."""

        def ping() -> bool:
            return redis_client.ping()

        result = benchmark(ping)
        assert result is True

    def test_redis_pipeline_benchmark(
        self,
        benchmark: BenchmarkFixture,
        redis_client: redis.Redis,
    ) -> None:
        """Benchmark Redis pipeline operations."""

        def pipeline_ops() -> list:
            pipe = redis_client.pipeline(transaction=True)
            pipe.set("pipe_1", "value1")
            pipe.set("pipe_2", "value2")
            pipe.set("pipe_3", "value3")
            pipe.get("pipe_1")
            pipe.get("pipe_2")
            pipe.get("pipe_3")
            return pipe.execute()

        result = benchmark(pipeline_ops)
        assert len(result) == 6

        redis_client.delete("pipe_1", "pipe_2", "pipe_3")

    def test_redis_mget_benchmark(
        self,
        benchmark: BenchmarkFixture,
        redis_client: redis.Redis,
    ) -> None:
        """Benchmark Redis MGET operations."""
        for i in range(10):
            redis_client.set(f"mget_key_{i}", f"value_{i}")

        def mget_ops() -> list:
            keys = [f"mget_key_{i}" for i in range(10)]
            return redis_client.mget(keys)

        result = benchmark(mget_ops)
        assert len(result) == 10

        for i in range(10):
            redis_client.delete(f"mget_key_{i}")


class TestRedisSerializationBenchmarks:
    """Benchmarks for Redis with JSON serialization."""

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

    def test_small_json_roundtrip(
        self,
        benchmark: BenchmarkFixture,
        redis_client: redis.Redis,
    ) -> None:
        """Benchmark small JSON payload roundtrip."""
        small_data = {"id": 1, "name": "test"}

        def roundtrip() -> dict:
            redis_client.set("small_key", json.dumps(small_data))
            return json.loads(redis_client.get("small_key"))

        result = benchmark(roundtrip)
        assert result == small_data

    def test_medium_json_roundtrip(
        self,
        benchmark: BenchmarkFixture,
        redis_client: redis.Redis,
    ) -> None:
        """Benchmark medium JSON payload roundtrip."""
        medium_data = {
            "items": [{"id": i, "value": f"item_{i}"} for i in range(100)],
            "metadata": {"count": 100, "page": 1},
        }

        def roundtrip() -> dict:
            redis_client.set("medium_key", json.dumps(medium_data))
            return json.loads(redis_client.get("medium_key"))

        result = benchmark(roundtrip)
        assert result["metadata"]["count"] == 100

    def test_large_json_roundtrip(
        self,
        benchmark: BenchmarkFixture,
        redis_client: redis.Redis,
    ) -> None:
        """Benchmark large JSON payload roundtrip."""
        large_data = {
            "items": [
                {"id": i, "data": "x" * 1000, "nested": {"value": i}}
                for i in range(100)
            ],
        }

        def roundtrip() -> dict:
            redis_client.set("large_key", json.dumps(large_data))
            return json.loads(redis_client.get("large_key"))

        result = benchmark(roundtrip)
        assert len(result["items"]) == 100


class TestJWTWithRedisBenchmarks:
    """Benchmarks combining JWT operations with Redis caching."""

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

    def test_jwt_create_and_cache(
        self,
        benchmark: BenchmarkFixture,
        redis_client: redis.Redis,
    ) -> None:
        """Benchmark creating JWT and caching in Redis."""
        counter = [0]

        def create_and_cache() -> bool:
            counter[0] += 1
            token = create_access_token(
                subject=f"user-{counter[0]}",
                roles=["user"],
                permissions=["read"],
            )
            return redis_client.set(f"token_cache_{counter[0]}", token, ex=3600)

        result = benchmark(create_and_cache)
        assert result is True

    def test_jwt_cache_hit_and_decode(
        self,
        benchmark: BenchmarkFixture,
        redis_client: redis.Redis,
    ) -> None:
        """Benchmark retrieving cached JWT and decoding."""
        # Setup: cache a token
        token = create_access_token(
            subject="bench-user",
            roles=["user"],
            permissions=["read"],
        )
        redis_client.set("cached_token", token)

        def fetch_and_decode() -> object:
            cached = redis_client.get("cached_token")
            return decode_token(cached)

        result = benchmark(fetch_and_decode)
        assert result.sub == "bench-user"

        redis_client.delete("cached_token")

    def test_full_auth_flow_simulation(
        self,
        benchmark: BenchmarkFixture,
        redis_client: redis.Redis,
    ) -> None:
        """Benchmark simulated auth flow: create token, cache, fetch, validate."""
        counter = [0]

        def auth_flow() -> bool:
            counter[0] += 1
            user_id = f"user-{counter[0]}"

            # Create token
            token = create_access_token(
                subject=user_id,
                roles=["user"],
                permissions=["read", "write"],
            )

            # Cache token
            cache_key = f"session:{user_id}"
            redis_client.set(cache_key, token, ex=1800)

            # Fetch and validate (simulating next request)
            cached_token = redis_client.get(cache_key)
            payload = decode_token(cached_token)

            # Cleanup
            redis_client.delete(cache_key)

            return payload.sub == user_id

        result = benchmark(auth_flow)
        assert result is True
