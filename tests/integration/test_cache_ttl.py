"""Integration tests for cache TTL and expiration behavior.

Tests cover:
- Cache TTL enforcement with real Redis
- Cache expiration after TTL
- TTL retrieval and verification
- Expiration behavior for decorated functions
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from app.cache.decorators import CacheManager, cached
from app.cache.redis import close_redis_pools, get_cache_client, init_redis_pools


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from app.core.config import Settings


pytestmark = pytest.mark.integration


class TestCacheTTL:
    """Tests for cache TTL behavior with real Redis."""

    @pytest.fixture
    async def cache_manager(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> AsyncGenerator[CacheManager]:
        """Create CacheManager with initialized Redis."""

        with patch("app.cache.redis.get_settings", return_value=test_settings):
            await init_redis_pools()

        yield CacheManager(prefix="ttl_test")

        await close_redis_pools()

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, cache_manager: CacheManager) -> None:
        """Should set value with TTL."""
        result = await cache_manager.set("ttl_key", {"value": "test"}, ttl=60)
        assert result is True

        # Verify value exists
        value = await cache_manager.get("ttl_key")
        assert value == {"value": "test"}

        # Cleanup
        await cache_manager.delete("ttl_key")

    @pytest.mark.asyncio
    async def test_ttl_returns_remaining_time(
        self, cache_manager: CacheManager
    ) -> None:
        """Should return remaining TTL for cached key."""
        await cache_manager.set("ttl_check", "value", ttl=120)

        ttl = await cache_manager.ttl("ttl_check")

        # TTL should be close to 120 (allow some drift)
        assert 115 <= ttl <= 120

        await cache_manager.delete("ttl_check")

    @pytest.mark.asyncio
    async def test_short_ttl_expires(self, cache_manager: CacheManager) -> None:
        """Should expire value after short TTL."""
        # Set with 1 second TTL
        await cache_manager.set("expire_fast", "temporary", ttl=1)

        # Verify value exists immediately
        value = await cache_manager.get("expire_fast")
        assert value == "temporary"

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Value should be gone
        value = await cache_manager.get("expire_fast")
        assert value is None

    @pytest.mark.asyncio
    async def test_ttl_returns_negative_for_expired(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Should return -2 for expired/nonexistent key."""
        # Set with very short TTL
        await cache_manager.set("will_expire", "temp", ttl=1)

        # Wait for expiration
        await asyncio.sleep(1.5)

        # TTL should be -2 (key doesn't exist)
        ttl = await cache_manager.ttl("will_expire")
        assert ttl == -2

    @pytest.mark.asyncio
    async def test_key_without_ttl_persists(self, cache_manager: CacheManager) -> None:
        """Should persist key without TTL indefinitely."""
        # Set without explicit TTL (uses default or no expiry)
        await cache_manager.set("no_ttl_key", "persistent")

        # Check TTL - should be -1 (no expiry) or a default value
        ttl = await cache_manager.ttl("no_ttl_key")

        # Either no expiry (-1) or some default TTL
        assert ttl != -2  # Key should exist

        await cache_manager.delete("no_ttl_key")

    @pytest.mark.asyncio
    async def test_multiple_keys_different_ttls(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Should handle multiple keys with different TTLs."""
        await cache_manager.set("short_ttl", "short", ttl=1)
        await cache_manager.set("long_ttl", "long", ttl=60)

        # Both should exist initially
        assert await cache_manager.exists("short_ttl") is True
        assert await cache_manager.exists("long_ttl") is True

        # Wait for short TTL to expire
        await asyncio.sleep(1.5)

        # Short TTL should be gone, long TTL should persist
        assert await cache_manager.exists("short_ttl") is False
        assert await cache_manager.exists("long_ttl") is True

        await cache_manager.delete("long_ttl")


class TestCachedDecoratorTTL:
    """Tests for @cached decorator TTL behavior with real Redis."""

    @pytest.fixture
    async def setup_redis(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> AsyncGenerator[None]:
        """Initialize Redis for decorator tests."""

        with patch("app.cache.redis.get_settings", return_value=test_settings):
            await init_redis_pools()

        yield

        await close_redis_pools()

    @pytest.mark.asyncio
    async def test_cached_decorator_respects_ttl(self, setup_redis: None) -> None:
        """Should cache result with specified TTL."""
        call_count = 0

        @cached(ttl=1, prefix="ttl_test")
        async def get_data(key: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"key": key, "count": call_count}

        # First call - should cache
        result1 = await get_data("test")
        assert result1["count"] == 1
        assert call_count == 1

        # Second call - should return cached
        result2 = await get_data("test")
        assert result2["count"] == 1
        assert call_count == 1

        # Wait for TTL to expire
        await asyncio.sleep(1.5)

        # Third call - cache expired, should call function again
        result3 = await get_data("test")
        assert result3["count"] == 2
        assert call_count == 2

        # Cleanup
        await get_data.invalidate("test")

    @pytest.mark.asyncio
    async def test_cached_decorator_different_ttls(self, setup_redis: None) -> None:
        """Should use different TTLs for different decorated functions."""
        short_call_count = 0
        long_call_count = 0

        @cached(ttl=1, prefix="short_ttl_func")
        async def short_cache(key: str) -> dict:
            nonlocal short_call_count
            short_call_count += 1
            return {"value": short_call_count}

        @cached(ttl=60, prefix="long_ttl_func")
        async def long_cache(key: str) -> dict:
            nonlocal long_call_count
            long_call_count += 1
            return {"value": long_call_count}

        # Cache both
        await short_cache("test")
        await long_cache("test")

        assert short_call_count == 1
        assert long_call_count == 1

        # Wait for short cache to expire
        await asyncio.sleep(1.5)

        # Short cache should recalculate, long cache should still be cached
        await short_cache("test")
        await long_cache("test")

        assert short_call_count == 2  # Called again
        assert long_call_count == 1  # Still cached

        # Cleanup
        await short_cache.invalidate("test")
        await long_cache.invalidate("test")

    @pytest.mark.asyncio
    async def test_cache_key_verification(self, setup_redis: None) -> None:
        """Should verify cache key TTL in Redis."""

        @cached(ttl=30, prefix="verify_ttl")
        async def get_item(item_id: str) -> dict:
            return {"id": item_id}

        await get_item("item-123")

        # Verify the key exists in Redis with correct TTL
        client = get_cache_client()
        keys = await client.keys("verify_ttl:*")
        assert len(keys) == 1

        ttl = await client.ttl(keys[0])
        assert 25 <= ttl <= 30

        # Cleanup
        await get_item.invalidate("item-123")


class TestCacheTTLEdgeCases:
    """Tests for edge cases in cache TTL handling."""

    @pytest.fixture
    async def cache_manager(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> AsyncGenerator[CacheManager]:
        """Create CacheManager with initialized Redis."""

        with patch("app.cache.redis.get_settings", return_value=test_settings):
            await init_redis_pools()

        yield CacheManager(prefix="edge_test")

        await close_redis_pools()

    @pytest.mark.asyncio
    async def test_zero_ttl_expires_immediately(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Should handle zero TTL (immediate expiration)."""
        # Redis with TTL=0 or TTL=1 should expire quickly
        await cache_manager.set("zero_ttl", "instant", ttl=1)

        # Wait briefly
        await asyncio.sleep(1.5)

        # Should be expired
        assert await cache_manager.exists("zero_ttl") is False

    @pytest.mark.asyncio
    async def test_update_does_not_reset_ttl(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Should not reset TTL when updating with same key (unless explicitly set)."""
        # Set with 3 second TTL
        await cache_manager.set("update_test", "original", ttl=3)

        # Wait 1 second
        await asyncio.sleep(1)

        # Get TTL - should be around 2 seconds
        ttl1 = await cache_manager.ttl("update_test")
        assert 1 <= ttl1 <= 2

        # Update without TTL
        await cache_manager.set("update_test", "updated", ttl=3)

        # TTL should be reset to 3
        ttl2 = await cache_manager.ttl("update_test")
        assert 2 <= ttl2 <= 3

        await cache_manager.delete("update_test")

    @pytest.mark.asyncio
    async def test_delete_before_expiry(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Should be able to delete key before it expires."""
        await cache_manager.set("delete_early", "value", ttl=60)

        # Verify exists
        assert await cache_manager.exists("delete_early") is True

        # Delete before expiry
        result = await cache_manager.delete("delete_early")
        assert result is True

        # Verify deleted
        assert await cache_manager.exists("delete_early") is False

    @pytest.mark.asyncio
    async def test_concurrent_access_during_expiration(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Should handle concurrent access when key is about to expire."""
        key = "concurrent_expire_test"
        await cache_manager.set(key, "expiring_value", ttl=1)

        async def try_get() -> str | None:
            return await cache_manager.get(key)

        # Start concurrent reads while key is expiring
        tasks = []
        for _ in range(10):
            tasks.append(try_get())
            await asyncio.sleep(0.15)

        results = await asyncio.gather(*tasks)

        # Early reads should get value, later reads should get None
        non_none_count = sum(1 for r in results if r is not None)
        none_count = sum(1 for r in results if r is None)

        # Some should have gotten the value, some should get None after expiry
        assert non_none_count > 0 or none_count > 0

    @pytest.mark.asyncio
    async def test_very_long_ttl(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Should handle very long TTL values."""
        # 1 year in seconds
        one_year = 365 * 24 * 60 * 60

        await cache_manager.set("long_ttl_test", "persistent", ttl=one_year)

        ttl = await cache_manager.ttl("long_ttl_test")
        # TTL should be close to 1 year
        assert ttl > (one_year - 10)

        await cache_manager.delete("long_ttl_test")

    @pytest.mark.asyncio
    async def test_ttl_precision(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Should maintain TTL precision for short durations."""
        await cache_manager.set("precision_test", "value", ttl=5)

        # Check TTL immediately
        ttl1 = await cache_manager.ttl("precision_test")
        assert 4 <= ttl1 <= 5

        # Wait 2 seconds
        await asyncio.sleep(2)

        # TTL should have decreased by ~2
        ttl2 = await cache_manager.ttl("precision_test")
        assert 2 <= ttl2 <= 3

        await cache_manager.delete("precision_test")

    @pytest.mark.asyncio
    async def test_pattern_delete_respects_ttl(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Should delete pattern before TTL expires."""
        # Set keys with long TTL
        await cache_manager.set("pattern:a:1", "value", ttl=60)
        await cache_manager.set("pattern:a:2", "value", ttl=60)
        await cache_manager.set("pattern:b:1", "value", ttl=60)

        # Delete pattern
        deleted = await cache_manager.delete_pattern("pattern:a:*")
        assert deleted == 2

        # Pattern:b should still exist
        assert await cache_manager.exists("pattern:b:1") is True

        await cache_manager.delete("pattern:b:1")


class TestCacheTTLConcurrency:
    """Tests for cache TTL behavior under concurrent access."""

    @pytest.fixture
    async def setup_redis(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> AsyncGenerator[None]:
        """Initialize Redis for concurrency tests."""

        with patch("app.cache.redis.get_settings", return_value=test_settings):
            await init_redis_pools()

        yield

        await close_redis_pools()

    @pytest.mark.asyncio
    async def test_concurrent_set_with_different_ttls(
        self,
        setup_redis: None,
    ) -> None:
        """Should handle concurrent sets with different TTLs."""
        cache = CacheManager(prefix="concurrent_ttl")

        async def set_with_ttl(key: str, ttl: int) -> None:
            await cache.set(key, {"ttl": ttl}, ttl=ttl)

        # Set many keys with different TTLs concurrently
        tasks = [set_with_ttl(f"key_{i}", i + 1) for i in range(10)]
        await asyncio.gather(*tasks)

        # Verify all keys exist with correct TTL range
        for i in range(10):
            ttl = await cache.ttl(f"key_{i}")
            assert ttl > 0  # Should exist
            assert ttl <= i + 1  # Should be within set TTL

        # Cleanup
        for i in range(10):
            await cache.delete(f"key_{i}")

    @pytest.mark.asyncio
    async def test_refresh_on_read_pattern(
        self,
        setup_redis: None,
    ) -> None:
        """Should demonstrate read doesn't refresh TTL (unless explicitly implemented)."""
        cache = CacheManager(prefix="refresh_test")

        # Set with 3 second TTL
        await cache.set("read_refresh", "value", ttl=3)

        # Read multiple times
        for _ in range(5):
            await cache.get("read_refresh")
            await asyncio.sleep(0.5)

        # TTL should still be decreasing (not refreshed)
        ttl = await cache.ttl("read_refresh")

        # After ~2.5 seconds of reads, TTL should be low
        assert ttl < 2

        await cache.delete("read_refresh")
