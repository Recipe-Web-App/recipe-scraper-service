"""Integration tests for Redis operations.

Tests cover:
- Redis pool initialization with real Redis
- Health checks
- Basic operations
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from app.cache.redis import (
    check_redis_health,
    close_redis_pools,
    get_cache_client,
    get_queue_client,
    get_rate_limit_client,
    init_redis_pools,
)


if TYPE_CHECKING:
    from app.core.config import Settings


pytestmark = pytest.mark.integration


class TestRedisPoolInitialization:
    """Tests for Redis pool initialization with real Redis."""

    @pytest.mark.asyncio
    async def test_init_creates_all_pools(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> None:
        """Should initialize all Redis pools successfully."""
        with patch("app.cache.redis.get_settings", return_value=test_settings):
            await init_redis_pools()

            # All clients should be available
            cache_client = get_cache_client()
            queue_client = get_queue_client()
            rate_limit_client = get_rate_limit_client()

            assert cache_client is not None
            assert queue_client is not None
            assert rate_limit_client is not None

            # Cleanup
            await close_redis_pools()

    @pytest.mark.asyncio
    async def test_ping_works_after_init(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> None:
        """Should be able to ping Redis after initialization."""

        with patch("app.cache.redis.get_settings", return_value=test_settings):
            await init_redis_pools()

            cache_client = get_cache_client()
            result = await cache_client.ping()

            assert result is True

            await close_redis_pools()


class TestRedisHealthCheck:
    """Tests for Redis health checks with real Redis."""

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> None:
        """Should return healthy status when Redis is connected."""

        with patch("app.cache.redis.get_settings", return_value=test_settings):
            await init_redis_pools()

            health = await check_redis_health()

            assert health["redis_cache"] == "healthy"
            assert health["redis_queue"] == "healthy"
            assert health["redis_rate_limit"] == "healthy"

            await close_redis_pools()

    @pytest.mark.asyncio
    async def test_health_check_returns_not_initialized(self) -> None:
        """Should return not_initialized when pools not created."""
        health = await check_redis_health()

        assert health["redis_cache"] == "not_initialized"
        assert health["redis_queue"] == "not_initialized"
        assert health["redis_rate_limit"] == "not_initialized"


class TestRedisBasicOperations:
    """Tests for basic Redis operations with real Redis."""

    @pytest.mark.asyncio
    async def test_set_and_get_value(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> None:
        """Should be able to set and get values."""

        with patch("app.cache.redis.get_settings", return_value=test_settings):
            await init_redis_pools()

            cache_client = get_cache_client()

            # Set a value
            await cache_client.set("test_key", "test_value")

            # Get the value
            result = await cache_client.get("test_key")

            assert result == "test_value"

            # Cleanup
            await cache_client.delete("test_key")
            await close_redis_pools()

    @pytest.mark.asyncio
    async def test_set_with_expiration(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> None:
        """Should be able to set values with TTL."""

        with patch("app.cache.redis.get_settings", return_value=test_settings):
            await init_redis_pools()

            cache_client = get_cache_client()

            # Set a value with TTL
            await cache_client.set("test_ttl_key", "test_value", ex=60)

            # Check TTL
            ttl = await cache_client.ttl("test_ttl_key")

            assert ttl > 0
            assert ttl <= 60

            # Cleanup
            await cache_client.delete("test_ttl_key")
            await close_redis_pools()

    @pytest.mark.asyncio
    async def test_delete_value(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> None:
        """Should be able to delete values."""

        with patch("app.cache.redis.get_settings", return_value=test_settings):
            await init_redis_pools()

            cache_client = get_cache_client()

            # Set and then delete
            await cache_client.set("to_delete", "value")
            await cache_client.delete("to_delete")

            # Should be None
            result = await cache_client.get("to_delete")

            assert result is None

            await close_redis_pools()
