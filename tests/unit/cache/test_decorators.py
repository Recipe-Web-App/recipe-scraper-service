"""Unit tests for cache decorators.

Tests cover:
- Cache key generation
- @cached decorator behavior
- CacheManager operations
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.cache.decorators import (
    CacheManager,
    _generate_cache_key,
    cache_key,
    cached,
)


pytestmark = pytest.mark.unit


# =============================================================================
# Cache Key Generation Tests
# =============================================================================


class TestGenerateCacheKey:
    """Tests for _generate_cache_key function."""

    def test_includes_prefix(self):
        """Should include prefix in key."""

        def sample_func():
            pass

        key = _generate_cache_key("myprefix", sample_func, (), {})
        assert key.startswith("myprefix:")

    def test_includes_function_name(self):
        """Should include function name in key."""

        def sample_func():
            pass

        key = _generate_cache_key("cache", sample_func, (), {})
        assert "sample_func" in key

    def test_different_args_produce_different_keys(self):
        """Different arguments should produce different keys."""

        def sample_func(x):
            pass

        key1 = _generate_cache_key("cache", sample_func, (1,), {})
        key2 = _generate_cache_key("cache", sample_func, (2,), {})

        assert key1 != key2

    def test_different_kwargs_produce_different_keys(self):
        """Different kwargs should produce different keys."""

        def sample_func(x=None):
            pass

        key1 = _generate_cache_key("cache", sample_func, (), {"x": 1})
        key2 = _generate_cache_key("cache", sample_func, (), {"x": 2})

        assert key1 != key2

    def test_same_args_produce_same_key(self):
        """Same arguments should produce consistent keys."""

        def sample_func(x, y):
            pass

        key1 = _generate_cache_key("cache", sample_func, (1, 2), {})
        key2 = _generate_cache_key("cache", sample_func, (1, 2), {})

        assert key1 == key2

    def test_handles_complex_args(self):
        """Should handle complex argument types."""

        def sample_func(data):
            pass

        # Should not raise
        key = _generate_cache_key("cache", sample_func, ({"nested": "dict"},), {})
        assert key is not None


class TestCacheKeyHelper:
    """Tests for cache_key helper function."""

    def test_joins_parts_with_colon(self):
        """Should join parts with colons."""
        result = cache_key("recipes", "123", "details")
        assert result == "recipes:123:details"

    def test_handles_single_part(self):
        """Should handle single part."""
        result = cache_key("recipes")
        assert result == "recipes"

    def test_converts_to_string(self):
        """Should convert non-string parts to strings."""
        result = cache_key("recipes", 123, True)
        assert result == "recipes:123:True"


# =============================================================================
# @cached Decorator Tests
# =============================================================================


class TestCachedDecorator:
    """Tests for @cached decorator."""

    async def test_returns_cached_value_on_hit(self):
        """Should return cached value without calling function."""
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=json.dumps({"cached": True}))

        with patch("app.cache.decorators.get_cache_client", return_value=mock_redis):

            @cached(ttl=60, prefix="test")
            async def get_data():
                return {"cached": False}

            result = await get_data()

        assert result == {"cached": True}

    async def test_calls_function_on_miss(self):
        """Should call function and cache result on miss."""
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        call_count = 0

        with patch("app.cache.decorators.get_cache_client", return_value=mock_redis):

            @cached(ttl=60, prefix="test")
            async def get_data():
                nonlocal call_count
                call_count += 1
                return {"fresh": True}

            result = await get_data()

        assert result == {"fresh": True}
        assert call_count == 1
        mock_redis.setex.assert_called_once()

    async def test_uses_custom_ttl(self):
        """Should use specified TTL when caching."""
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        with patch("app.cache.decorators.get_cache_client", return_value=mock_redis):

            @cached(ttl=120, prefix="test")
            async def get_data():
                return {"data": True}

            await get_data()

        # Check that setex was called with ttl=120
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 120  # Second positional arg is TTL

    async def test_uses_custom_key_builder(self):
        """Should use custom key builder when provided."""
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        def custom_key_builder(item_id):
            return f"custom:item:{item_id}"

        with patch("app.cache.decorators.get_cache_client", return_value=mock_redis):

            @cached(ttl=60, key_builder=custom_key_builder)
            async def get_item(item_id):
                return {"id": item_id}

            await get_item("123")

        # Check key starts with custom prefix
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "custom:item:123"

    async def test_skips_cache_when_redis_unavailable(self):
        """Should call function directly when Redis is unavailable."""
        with patch(
            "app.cache.decorators.get_cache_client",
            side_effect=RuntimeError("Redis not initialized"),
        ):

            @cached(ttl=60)
            async def get_data():
                return {"direct": True}

            result = await get_data()

        assert result == {"direct": True}

    async def test_handles_cache_read_error(self):
        """Should call function on cache read error."""
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(side_effect=Exception("Read error"))

        with patch("app.cache.decorators.get_cache_client", return_value=mock_redis):

            @cached(ttl=60)
            async def get_data():
                return {"fallback": True}

            result = await get_data()

        assert result == {"fallback": True}

    async def test_invalidate_deletes_cached_value(self):
        """Should provide invalidate method to clear cache."""
        mock_redis = MagicMock()
        mock_redis.delete = AsyncMock(return_value=1)

        with patch("app.cache.decorators.get_cache_client", return_value=mock_redis):

            @cached(ttl=60, prefix="test")
            async def get_data(item_id):
                return {"id": item_id}

            result = await get_data.invalidate("123")

        assert result is True
        mock_redis.delete.assert_called_once()


# =============================================================================
# CacheManager Tests
# =============================================================================


class TestCacheManager:
    """Tests for CacheManager class."""

    @pytest.fixture
    def cache_manager(self):
        """Create a CacheManager instance."""
        return CacheManager(prefix="test")

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        mock = MagicMock()
        mock.get = AsyncMock(return_value=None)
        mock.setex = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=1)
        mock.exists = AsyncMock(return_value=1)
        mock.ttl = AsyncMock(return_value=300)
        return mock

    async def test_get_returns_cached_value(self, cache_manager, mock_redis):
        """Should return deserialized cached value."""
        mock_redis.get = AsyncMock(return_value=json.dumps({"key": "value"}))

        with patch("app.cache.decorators.get_cache_client", return_value=mock_redis):
            result = await cache_manager.get("mykey")

        assert result == {"key": "value"}
        mock_redis.get.assert_called_with("test:mykey")

    async def test_get_returns_default_on_miss(self, cache_manager, mock_redis):
        """Should return default when key not found."""
        mock_redis.get = AsyncMock(return_value=None)

        with patch("app.cache.decorators.get_cache_client", return_value=mock_redis):
            result = await cache_manager.get("missing", default="default_value")

        assert result == "default_value"

    async def test_set_stores_value(self, cache_manager, mock_redis):
        """Should serialize and store value."""
        with patch("app.cache.decorators.get_cache_client", return_value=mock_redis):
            result = await cache_manager.set("mykey", {"data": True}, ttl=600)

        assert result is True
        mock_redis.setex.assert_called_with(
            "test:mykey",
            600,
            json.dumps({"data": True}),
        )

    async def test_delete_removes_key(self, cache_manager, mock_redis):
        """Should delete key from cache."""
        with patch("app.cache.decorators.get_cache_client", return_value=mock_redis):
            result = await cache_manager.delete("mykey")

        assert result is True
        mock_redis.delete.assert_called_with("test:mykey")

    async def test_exists_checks_key(self, cache_manager, mock_redis):
        """Should check if key exists."""
        with patch("app.cache.decorators.get_cache_client", return_value=mock_redis):
            result = await cache_manager.exists("mykey")

        assert result is True
        mock_redis.exists.assert_called_with("test:mykey")

    async def test_ttl_returns_remaining_time(self, cache_manager, mock_redis):
        """Should return remaining TTL."""
        mock_redis.ttl = AsyncMock(return_value=150)

        with patch("app.cache.decorators.get_cache_client", return_value=mock_redis):
            result = await cache_manager.ttl("mykey")

        assert result == 150

    async def test_delete_pattern_removes_matching_keys(
        self, cache_manager, mock_redis
    ):
        """Should delete all keys matching pattern."""

        async def mock_scan_iter(*args, **kwargs):
            for key in ["test:user:1", "test:user:2"]:
                yield key

        mock_redis.scan_iter = mock_scan_iter
        mock_redis.delete = AsyncMock(return_value=2)

        with patch("app.cache.decorators.get_cache_client", return_value=mock_redis):
            result = await cache_manager.delete_pattern("user:*")

        assert result == 2

    async def test_handles_redis_errors_gracefully(self, cache_manager, mock_redis):
        """Should handle Redis errors without raising."""
        mock_redis.get = AsyncMock(side_effect=Exception("Connection error"))

        with patch("app.cache.decorators.get_cache_client", return_value=mock_redis):
            result = await cache_manager.get("mykey", default="fallback")

        assert result == "fallback"

    async def test_set_returns_false_on_redis_error(self, cache_manager, mock_redis):
        """Should return False when set operation fails."""
        mock_redis.setex = AsyncMock(side_effect=Exception("Write error"))

        with patch("app.cache.decorators.get_cache_client", return_value=mock_redis):
            result = await cache_manager.set("mykey", {"data": True})

        assert result is False

    async def test_delete_returns_false_on_redis_error(self, cache_manager, mock_redis):
        """Should return False when delete operation fails."""
        mock_redis.delete = AsyncMock(side_effect=Exception("Delete error"))

        with patch("app.cache.decorators.get_cache_client", return_value=mock_redis):
            result = await cache_manager.delete("mykey")

        assert result is False

    async def test_delete_pattern_returns_zero_on_redis_error(
        self, cache_manager, mock_redis
    ):
        """Should return 0 when delete_pattern operation fails."""

        async def mock_scan_iter_error(*args, **kwargs):
            msg = "Scan error"
            raise RuntimeError(msg)
            yield  # Never reached

        mock_redis.scan_iter = mock_scan_iter_error

        with patch("app.cache.decorators.get_cache_client", return_value=mock_redis):
            result = await cache_manager.delete_pattern("user:*")

        assert result == 0

    async def test_exists_returns_false_on_redis_error(self, cache_manager, mock_redis):
        """Should return False when exists operation fails."""
        mock_redis.exists = AsyncMock(side_effect=Exception("Exists error"))

        with patch("app.cache.decorators.get_cache_client", return_value=mock_redis):
            result = await cache_manager.exists("mykey")

        assert result is False

    async def test_ttl_returns_negative_two_on_redis_error(
        self, cache_manager, mock_redis
    ):
        """Should return -2 when ttl operation fails."""
        mock_redis.ttl = AsyncMock(side_effect=Exception("TTL error"))

        with patch("app.cache.decorators.get_cache_client", return_value=mock_redis):
            result = await cache_manager.ttl("mykey")

        assert result == -2
