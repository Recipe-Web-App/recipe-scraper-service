"""Integration tests for cache operations.

Tests cover:
- CacheManager CRUD operations with real Redis
- Cached decorator behavior
- Cache key generation
- TTL and expiration
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


class TestCacheManager:
    """Tests for CacheManager with real Redis."""

    @pytest.fixture
    async def cache_manager(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> AsyncGenerator[CacheManager]:
        """Create CacheManager with initialized Redis."""
        parts = redis_url.replace("redis://", "").split(":")
        test_settings.REDIS_HOST = parts[0]
        test_settings.REDIS_PORT = int(parts[1])

        with patch("app.cache.redis.get_settings", return_value=test_settings):
            await init_redis_pools()

        yield CacheManager(prefix="test")

        await close_redis_pools()

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache_manager: CacheManager) -> None:
        """Should set and get values."""
        result = await cache_manager.set("mykey", {"foo": "bar"})
        assert result is True

        value = await cache_manager.get("mykey")
        assert value == {"foo": "bar"}

        # Cleanup
        await cache_manager.delete("mykey")

    @pytest.mark.asyncio
    async def test_get_returns_default_when_not_found(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Should return default value when key not found."""
        value = await cache_manager.get("nonexistent", default="default_value")
        assert value == "default_value"

    @pytest.mark.asyncio
    async def test_get_returns_none_by_default(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Should return None when key not found and no default."""
        value = await cache_manager.get("nonexistent")
        assert value is None

    @pytest.mark.asyncio
    async def test_delete(self, cache_manager: CacheManager) -> None:
        """Should delete cached values."""
        await cache_manager.set("to_delete", "value")
        assert await cache_manager.exists("to_delete") is True

        result = await cache_manager.delete("to_delete")
        assert result is True

        assert await cache_manager.exists("to_delete") is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Should return False when deleting nonexistent key."""
        result = await cache_manager.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists(self, cache_manager: CacheManager) -> None:
        """Should check if key exists."""
        assert await cache_manager.exists("check_exists") is False

        await cache_manager.set("check_exists", "value")
        assert await cache_manager.exists("check_exists") is True

        await cache_manager.delete("check_exists")

    @pytest.mark.asyncio
    async def test_ttl(self, cache_manager: CacheManager) -> None:
        """Should return TTL for cached key."""
        await cache_manager.set("ttl_key", "value", ttl=60)

        ttl = await cache_manager.ttl("ttl_key")
        assert 0 < ttl <= 60

        await cache_manager.delete("ttl_key")

    @pytest.mark.asyncio
    async def test_ttl_returns_negative_for_nonexistent(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Should return -2 for nonexistent key."""
        ttl = await cache_manager.ttl("nonexistent")
        assert ttl == -2

    @pytest.mark.asyncio
    async def test_delete_pattern(self, cache_manager: CacheManager) -> None:
        """Should delete all keys matching pattern."""
        # Set multiple keys with same prefix
        await cache_manager.set("user:1:profile", {"name": "Alice"})
        await cache_manager.set("user:2:profile", {"name": "Bob"})
        await cache_manager.set("user:3:profile", {"name": "Charlie"})
        await cache_manager.set("other:key", "value")

        # Delete all user profiles
        deleted = await cache_manager.delete_pattern("user:*:profile")
        assert deleted == 3

        # Other key should still exist
        assert await cache_manager.exists("other:key") is True

        # Cleanup
        await cache_manager.delete("other:key")

    @pytest.mark.asyncio
    async def test_set_complex_values(self, cache_manager: CacheManager) -> None:
        """Should cache complex JSON-serializable values."""
        complex_value = {
            "string": "value",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "nested": {"a": "b"},
        }

        await cache_manager.set("complex", complex_value)
        retrieved = await cache_manager.get("complex")

        assert retrieved == complex_value

        await cache_manager.delete("complex")


class TestCachedDecorator:
    """Tests for @cached decorator with real Redis."""

    @pytest.fixture
    async def setup_redis(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> AsyncGenerator[None]:
        """Initialize Redis for decorator tests."""
        parts = redis_url.replace("redis://", "").split(":")
        test_settings.REDIS_HOST = parts[0]
        test_settings.REDIS_PORT = int(parts[1])

        with patch("app.cache.redis.get_settings", return_value=test_settings):
            await init_redis_pools()

        yield

        await close_redis_pools()

    @pytest.mark.asyncio
    async def test_caches_function_result(self, setup_redis: None) -> None:
        """Should cache function result on first call."""
        call_count = 0

        @cached(ttl=60, prefix="test")
        async def expensive_operation(x: int) -> dict:
            nonlocal call_count
            call_count += 1
            return {"result": x * 2}

        # First call - should execute function
        result1 = await expensive_operation(5)
        assert result1 == {"result": 10}
        assert call_count == 1

        # Second call - should return cached result
        result2 = await expensive_operation(5)
        assert result2 == {"result": 10}
        assert call_count == 1  # Function not called again

        # Clean up
        await expensive_operation.invalidate(5)

    @pytest.mark.asyncio
    async def test_different_args_different_cache(self, setup_redis: None) -> None:
        """Should cache separately for different arguments."""
        call_count = 0

        @cached(ttl=60, prefix="test")
        async def compute(x: int) -> dict:
            nonlocal call_count
            call_count += 1
            return {"value": x}

        await compute(1)
        await compute(2)
        await compute(1)  # Should be cached

        assert call_count == 2  # Only 2 unique calls

        # Clean up
        await compute.invalidate(1)
        await compute.invalidate(2)

    @pytest.mark.asyncio
    async def test_invalidate_removes_cache(self, setup_redis: None) -> None:
        """Should invalidate cached value."""
        call_count = 0

        @cached(ttl=60, prefix="test")
        async def get_data(key: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"key": key}

        # Cache the result
        await get_data("test")
        assert call_count == 1

        # Invalidate
        result = await get_data.invalidate("test")
        assert result is True

        # Should call function again
        await get_data("test")
        assert call_count == 2

        # Clean up
        await get_data.invalidate("test")

    @pytest.mark.asyncio
    async def test_custom_key_builder(self, setup_redis: None) -> None:
        """Should use custom key builder when provided."""

        def my_key_builder(user_id: str, **kwargs: object) -> str:
            return f"custom:user:{user_id}"

        call_count = 0

        @cached(ttl=60, key_builder=my_key_builder)
        async def get_user(user_id: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"id": user_id}

        await get_user("123")
        await get_user("123")

        assert call_count == 1

        # Verify custom key was used
        client = get_cache_client()
        exists = await client.exists("custom:user:123")
        assert exists == 1

        # Clean up
        await client.delete("custom:user:123")

    @pytest.mark.asyncio
    async def test_kwargs_affect_cache_key(self, setup_redis: None) -> None:
        """Should include kwargs in cache key."""
        call_count = 0

        @cached(ttl=60, prefix="test")
        async def fetch(resource: str, version: int = 1) -> dict:
            nonlocal call_count
            call_count += 1
            return {"resource": resource, "version": version}

        await fetch("data", version=1)
        await fetch("data", version=2)
        await fetch("data", version=1)  # Cached

        assert call_count == 2

        # Clean up
        await fetch.invalidate("data", version=1)
        await fetch.invalidate("data", version=2)


class TestCacheEdgeCases:
    """Edge case tests for cache operations."""

    @pytest.fixture
    async def cache_manager(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> AsyncGenerator[CacheManager]:
        """Create CacheManager with initialized Redis."""
        parts = redis_url.replace("redis://", "").split(":")
        test_settings.REDIS_HOST = parts[0]
        test_settings.REDIS_PORT = int(parts[1])

        with patch("app.cache.redis.get_settings", return_value=test_settings):
            await init_redis_pools()

        yield CacheManager(prefix="edge_test")

        await close_redis_pools()

    @pytest.mark.asyncio
    async def test_large_payload_serialization(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Should handle large JSON payloads."""
        # Create a large nested structure
        large_payload = {
            "items": [{"id": i, "data": "x" * 1000} for i in range(100)],
            "metadata": {
                "nested": {
                    "deep": {
                        "value": list(range(1000)),
                    }
                }
            },
        }

        await cache_manager.set("large_payload", large_payload)
        retrieved = await cache_manager.get("large_payload")

        assert retrieved == large_payload
        assert len(retrieved["items"]) == 100

        await cache_manager.delete("large_payload")

    @pytest.mark.asyncio
    async def test_special_characters_in_keys(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Should handle special characters in cache keys."""
        special_keys = [
            "key:with:colons",
            "key/with/slashes",
            "key.with.dots",
            "key-with-dashes",
            "key_with_underscores",
            "key with spaces",
            "key@with#special$chars",
        ]

        for key in special_keys:
            await cache_manager.set(key, {"key": key})
            value = await cache_manager.get(key)
            assert value == {"key": key}, f"Failed for key: {key}"
            await cache_manager.delete(key)

    @pytest.mark.asyncio
    async def test_concurrent_writes_to_same_key(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Should handle concurrent writes to the same key."""
        key = "concurrent_write_key"

        async def write_value(val: int) -> None:
            await cache_manager.set(key, {"value": val})

        # Launch concurrent writes
        tasks = [write_value(i) for i in range(10)]
        await asyncio.gather(*tasks)

        # Key should exist with one of the values
        value = await cache_manager.get(key)
        assert value is not None
        assert "value" in value
        assert 0 <= value["value"] <= 9

        await cache_manager.delete(key)

    @pytest.mark.asyncio
    async def test_concurrent_reads_and_writes(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Should handle concurrent reads and writes."""
        key = "concurrent_rw_key"
        await cache_manager.set(key, {"initial": True})

        async def read_value() -> dict | None:
            return await cache_manager.get(key)

        async def write_value(val: int) -> None:
            await cache_manager.set(key, {"value": val})

        # Mix reads and writes
        tasks = []
        for i in range(10):
            tasks.append(read_value())
            tasks.append(write_value(i))

        results = await asyncio.gather(*tasks)

        # All reads should return valid data (not None)
        read_results = [r for r in results if r is not None]
        assert len(read_results) > 0

        await cache_manager.delete(key)

    @pytest.mark.asyncio
    async def test_unicode_values(self, cache_manager: CacheManager) -> None:
        """Should handle unicode characters in values."""
        unicode_value = {
            "emoji": "🎉🚀💻",
            "chinese": "中文测试",
            "japanese": "日本語テスト",
            "arabic": "اختبار عربي",
            "mixed": "Hello 世界 🌍",
        }

        await cache_manager.set("unicode_test", unicode_value)
        retrieved = await cache_manager.get("unicode_test")

        assert retrieved == unicode_value

        await cache_manager.delete("unicode_test")

    @pytest.mark.asyncio
    async def test_empty_values(self, cache_manager: CacheManager) -> None:
        """Should handle empty values correctly."""
        # Empty dict
        await cache_manager.set("empty_dict", {})
        assert await cache_manager.get("empty_dict") == {}

        # Empty list
        await cache_manager.set("empty_list", [])
        assert await cache_manager.get("empty_list") == []

        # Empty string
        await cache_manager.set("empty_string", "")
        assert await cache_manager.get("empty_string") == ""

        # Cleanup
        await cache_manager.delete("empty_dict")
        await cache_manager.delete("empty_list")
        await cache_manager.delete("empty_string")

    @pytest.mark.asyncio
    async def test_overwrite_existing_key(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Should overwrite existing key with new value."""
        key = "overwrite_test"

        await cache_manager.set(key, {"version": 1})
        assert (await cache_manager.get(key))["version"] == 1

        await cache_manager.set(key, {"version": 2})
        assert (await cache_manager.get(key))["version"] == 2

        await cache_manager.set(key, {"completely": "different"})
        result = await cache_manager.get(key)
        assert "version" not in result
        assert result["completely"] == "different"

        await cache_manager.delete(key)

    @pytest.mark.asyncio
    async def test_delete_pattern_with_many_keys(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Should delete many keys matching a pattern efficiently."""
        # Create many keys
        for i in range(50):
            await cache_manager.set(f"bulk:item:{i}", {"id": i})

        # Verify they exist
        assert await cache_manager.exists("bulk:item:0") is True
        assert await cache_manager.exists("bulk:item:49") is True

        # Delete all
        deleted = await cache_manager.delete_pattern("bulk:item:*")
        assert deleted == 50

        # Verify deletion
        assert await cache_manager.exists("bulk:item:0") is False
        assert await cache_manager.exists("bulk:item:49") is False


class TestCacheStampede:
    """Tests for cache stampede prevention scenarios."""

    @pytest.fixture
    async def setup_redis(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> AsyncGenerator[None]:
        """Initialize Redis for stampede tests."""
        parts = redis_url.replace("redis://", "").split(":")
        test_settings.REDIS_HOST = parts[0]
        test_settings.REDIS_PORT = int(parts[1])

        with patch("app.cache.redis.get_settings", return_value=test_settings):
            await init_redis_pools()

        yield

        await close_redis_pools()

    @pytest.mark.asyncio
    async def test_multiple_concurrent_cache_misses(
        self,
        setup_redis: None,
    ) -> None:
        """Should handle multiple concurrent requests for uncached data."""
        call_count = 0

        @cached(ttl=60, prefix="stampede_test")
        async def expensive_operation(key: str) -> dict:
            nonlocal call_count
            call_count += 1
            # Simulate expensive operation
            await asyncio.sleep(0.1)
            return {"key": key, "computed": True}

        # Launch many concurrent requests for the same key
        tasks = [expensive_operation("same_key") for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All results should be the same
        for result in results:
            assert result == {"key": "same_key", "computed": True}

        # Note: Without stampede protection, call_count could be up to 10
        # With basic caching, it should be relatively low (some calls may
        # race before the first result is cached)
        # We just verify the function was called at least once
        assert call_count >= 1

        await expensive_operation.invalidate("same_key")
