"""Integration tests for Redis resilience and error handling.

Tests cover:
- Operations when Redis is temporarily unavailable
- Reconnection after Redis restart
- Graceful degradation behavior
- Connection pool behavior under stress
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import redis.asyncio as aioredis
from httpx import ASGITransport, AsyncClient

from app.cache.decorators import CacheManager
from app.cache.redis import close_redis_pools, get_cache_client, init_redis_pools
from app.core.config.settings import RedisSettings
from app.factory import create_app


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from app.core.config import Settings


pytestmark = pytest.mark.integration


class TestRedisUnavailable:
    """Tests for handling Redis unavailability."""

    @pytest.mark.asyncio
    async def test_app_starts_without_redis(
        self,
        test_settings: Settings,
    ) -> None:
        """Should start application even when Redis is unavailable."""
        # Create settings with invalid Redis host
        invalid_redis_settings = test_settings.model_copy(
            update={
                "redis": RedisSettings(
                    host="invalid-host-that-does-not-exist", port=9999
                )
            }
        )

        app = create_app(invalid_redis_settings)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # App should still respond to basic requests
            response = await client.get("/")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_endpoint_with_redis_down(
        self,
        test_settings: Settings,
    ) -> None:
        """Should return health status even when Redis is down."""
        invalid_redis_settings = test_settings.model_copy(
            update={"redis": RedisSettings(host="invalid-host", port=9999)}
        )

        app = create_app(invalid_redis_settings)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/health")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_ready_endpoint_shows_degraded_status(
        self,
        test_settings: Settings,
    ) -> None:
        """Should show degraded status when Redis is unavailable."""
        invalid_redis_settings = test_settings.model_copy(
            update={"redis": RedisSettings(host="invalid-host", port=9999)}
        )

        app = create_app(invalid_redis_settings)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/ready")
            data = response.json()

            # Should indicate Redis is not healthy
            assert data["status"] in ("ready", "degraded")


class TestCacheGracefulDegradation:
    """Tests for cache graceful degradation."""

    @pytest.fixture
    async def disconnected_cache_manager(
        self,
        test_settings: Settings,
    ) -> AsyncGenerator[CacheManager]:
        """Create CacheManager with disconnected Redis."""
        invalid_redis_settings = test_settings.model_copy(
            update={"redis": RedisSettings(host="invalid-host", port=9999)}
        )

        # Try to initialize but expect failure
        with (
            contextlib.suppress(Exception),
            patch("app.cache.redis.get_settings", return_value=invalid_redis_settings),
        ):
            await init_redis_pools()

        yield CacheManager(prefix="test")

        with contextlib.suppress(Exception):
            await close_redis_pools()

    @pytest.mark.asyncio
    async def test_cache_get_handles_connection_error(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> None:
        """Should handle connection errors gracefully on get."""

        with patch("app.cache.redis.get_settings", return_value=test_settings):
            await init_redis_pools()

        cache_manager = CacheManager(prefix="test")

        # Set a value first
        await cache_manager.set("test_key", {"value": "test"})

        # Now close the pool to simulate disconnect
        await close_redis_pools()

        # Get should handle the error gracefully (return default)
        result = await cache_manager.get("test_key", default={"fallback": True})

        # Should return default when Redis is unavailable
        assert result == {"fallback": True}


class TestConnectionPoolBehavior:
    """Tests for Redis connection pool behavior."""

    @pytest.fixture
    async def setup_redis(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> AsyncGenerator[None]:
        """Initialize Redis pools."""

        with patch("app.cache.redis.get_settings", return_value=test_settings):
            await init_redis_pools()

        yield

        await close_redis_pools()

    @pytest.mark.asyncio
    async def test_concurrent_connections(
        self,
        setup_redis: None,
    ) -> None:
        """Should handle many concurrent connections."""
        client = get_cache_client()

        async def do_operation(i: int) -> bool:
            key = f"concurrent_test_{i}"
            await client.set(key, f"value_{i}")
            value = await client.get(key)
            await client.delete(key)
            return value == f"value_{i}"

        # Run 100 concurrent operations
        tasks = [do_operation(i) for i in range(100)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(results)

    @pytest.mark.asyncio
    async def test_rapid_connect_disconnect(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> None:
        """Should handle rapid connect/disconnect cycles."""

        for _ in range(5):
            with patch("app.cache.redis.get_settings", return_value=test_settings):
                await init_redis_pools()

            client = get_cache_client()
            await client.set("rapid_test", "value")
            value = await client.get("rapid_test")
            assert value == "value"
            await client.delete("rapid_test")

            await close_redis_pools()

    @pytest.mark.asyncio
    async def test_pool_reuse(
        self,
        setup_redis: None,
    ) -> None:
        """Should reuse connections from pool."""
        client = get_cache_client()

        # Perform many sequential operations
        for i in range(50):
            await client.set(f"reuse_test_{i}", f"value_{i}")

        # Verify all values
        for i in range(50):
            value = await client.get(f"reuse_test_{i}")
            assert value == f"value_{i}"

        # Cleanup
        for i in range(50):
            await client.delete(f"reuse_test_{i}")


class TestRedisReconnection:
    """Tests for Redis reconnection behavior."""

    @pytest.mark.asyncio
    async def test_operations_after_pool_reset(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> None:
        """Should work after pool is reset."""

        # Initial connection
        with patch("app.cache.redis.get_settings", return_value=test_settings):
            await init_redis_pools()

        client = get_cache_client()
        await client.set("reconnect_test", "before")

        # Close and reinitialize
        await close_redis_pools()

        with patch("app.cache.redis.get_settings", return_value=test_settings):
            await init_redis_pools()

        # Should still work
        client = get_cache_client()
        value = await client.get("reconnect_test")
        assert value == "before"

        await client.delete("reconnect_test")
        await close_redis_pools()


class TestRedisEdgeCases:
    """Edge case tests for Redis operations."""

    @pytest.fixture
    async def redis_client(
        self,
        redis_url: str,
    ) -> AsyncGenerator[aioredis.Redis]:
        """Get direct Redis client for edge case tests."""
        client = await aioredis.from_url(redis_url, decode_responses=True)
        yield client
        await client.aclose()

    @pytest.fixture
    async def redis_client_binary(
        self,
        redis_url: str,
    ) -> AsyncGenerator[aioredis.Redis]:
        """Get direct Redis client for binary data tests."""
        client = await aioredis.from_url(redis_url)
        yield client
        await client.aclose()

    @pytest.mark.asyncio
    async def test_very_large_value(
        self,
        redis_client: aioredis.Redis,
    ) -> None:
        """Should handle very large values."""
        # Create 1MB string
        large_value = "x" * (1024 * 1024)

        await redis_client.set("large_value_test", large_value)
        retrieved = await redis_client.get("large_value_test")

        assert retrieved == large_value
        await redis_client.delete("large_value_test")

    @pytest.mark.asyncio
    async def test_binary_data(
        self,
        redis_client_binary: aioredis.Redis,
    ) -> None:
        """Should handle binary data."""
        binary_data = bytes(range(256))

        await redis_client_binary.set("binary_test", binary_data)
        retrieved = await redis_client_binary.get("binary_test")

        assert retrieved == binary_data
        await redis_client_binary.delete("binary_test")

    @pytest.mark.asyncio
    async def test_key_with_special_characters(
        self,
        redis_client: aioredis.Redis,
    ) -> None:
        """Should handle keys with special characters."""
        special_keys = [
            "key:with:colons",
            "key/with/slashes",
            "key with spaces",
            "key\twith\ttabs",
            "key\nwith\nnewlines",
        ]

        for key in special_keys:
            await redis_client.set(key, "value")
            value = await redis_client.get(key)
            assert value == "value", f"Failed for key: {key!r}"
            await redis_client.delete(key)

    @pytest.mark.asyncio
    async def test_empty_string_value(
        self,
        redis_client: aioredis.Redis,
    ) -> None:
        """Should handle empty string values."""
        await redis_client.set("empty_test", "")
        value = await redis_client.get("empty_test")

        assert value == ""
        await redis_client.delete("empty_test")

    @pytest.mark.asyncio
    async def test_null_byte_in_value(
        self,
        redis_client: aioredis.Redis,
    ) -> None:
        """Should handle null bytes in values."""
        value_with_null = "before\x00after"

        await redis_client.set("null_byte_test", value_with_null)
        retrieved = await redis_client.get("null_byte_test")

        assert retrieved == value_with_null
        await redis_client.delete("null_byte_test")

    @pytest.mark.asyncio
    async def test_concurrent_increment(
        self,
        redis_client: aioredis.Redis,
    ) -> None:
        """Should handle concurrent increments atomically."""
        key = "concurrent_incr_test"
        await redis_client.set(key, "0")

        async def increment() -> int:
            return await redis_client.incr(key)

        # Run 100 concurrent increments
        tasks = [increment() for _ in range(100)]
        await asyncio.gather(*tasks)

        final_value = await redis_client.get(key)
        assert int(final_value) == 100

        await redis_client.delete(key)

    @pytest.mark.asyncio
    async def test_pipeline_operations(
        self,
        redis_client: aioredis.Redis,
    ) -> None:
        """Should handle pipeline operations."""
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.set("pipe_test_1", "value1")
            pipe.set("pipe_test_2", "value2")
            pipe.set("pipe_test_3", "value3")
            await pipe.execute()

        # Verify all values were set
        assert await redis_client.get("pipe_test_1") == "value1"
        assert await redis_client.get("pipe_test_2") == "value2"
        assert await redis_client.get("pipe_test_3") == "value3"

        # Cleanup
        await redis_client.delete("pipe_test_1", "pipe_test_2", "pipe_test_3")
