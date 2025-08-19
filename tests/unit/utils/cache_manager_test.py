"""Unit tests for the enhanced cache manager."""

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from app.utils.cache_manager import EnhancedCacheManager, get_cache_manager


class TestEnhancedCacheManager:
    """Unit tests for the EnhancedCacheManager class."""

    @pytest.mark.unit
    def test_enhanced_cache_manager_initialization_default(self) -> None:
        """Test cache manager initialization with default settings."""
        # Act
        cache_manager = EnhancedCacheManager()

        # Assert
        assert cache_manager.cache_dir.exists()
        assert cache_manager._memory_cache_size_limit == 1000
        assert cache_manager.redis_enabled is True
        assert cache_manager.cache_type == "resource"
        assert cache_manager._redis_client is None
        assert len(cache_manager._memory_cache) == 0

    @pytest.mark.unit
    def test_enhanced_cache_manager_initialization_custom_dir(self) -> None:
        """Test cache manager initialization with custom directory."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_cache_dir = str(Path(temp_dir) / "custom_cache")

            # Act
            cache_manager = EnhancedCacheManager(cache_dir=custom_cache_dir)

            # Assert
            assert cache_manager.cache_dir == Path(custom_cache_dir)
            assert cache_manager.cache_dir.exists()

    @pytest.mark.unit
    def test_enhanced_cache_manager_initialization_redis_disabled(self) -> None:
        """Test cache manager initialization with Redis disabled."""
        # Act
        cache_manager = EnhancedCacheManager(enable_redis=False)

        # Assert
        assert cache_manager.redis_enabled is False

    @pytest.mark.unit
    def test_get_session_db_cache_key(self) -> None:
        """Test session-database cache key formatting."""
        # Arrange
        cache_manager = EnhancedCacheManager()
        cache_key = "test_key_123"

        # Act
        result = cache_manager._get_session_db_cache_key(cache_key)

        # Assert
        assert result == "cache:resource:test_key_123"

    @pytest.mark.unit
    def test_get_key_prefix_with_colon(self) -> None:
        """Test key prefix extraction with colon separator."""
        # Arrange
        cache_manager = EnhancedCacheManager()
        cache_key = "recipes:italian:pasta"

        # Act
        result = cache_manager._get_key_prefix(cache_key)

        # Assert
        assert result == "recipes"

    @pytest.mark.unit
    def test_get_key_prefix_without_colon(self) -> None:
        """Test key prefix extraction without colon separator."""
        # Arrange
        cache_manager = EnhancedCacheManager()
        cache_key = "simple_key"

        # Act
        result = cache_manager._get_key_prefix(cache_key)

        # Assert
        assert result == "default"

    @pytest.mark.unit
    def test_get_cache_file_path(self) -> None:
        """Test cache file path generation."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = EnhancedCacheManager(cache_dir=temp_dir)
            cache_key = "test_data"

            # Act
            result = cache_manager._get_cache_file_path(cache_key)

            # Assert
            expected_path = Path(temp_dir) / "test_data.json"
            assert result == expected_path

    @pytest.mark.unit
    def test_evict_memory_cache_under_limit(self) -> None:
        """Test memory cache eviction when under size limit."""
        # Arrange
        cache_manager = EnhancedCacheManager()
        cache_manager._memory_cache_size_limit = 10
        # Add some items (under limit)
        for i in range(5):
            cache_manager._memory_cache[f"key_{i}"] = {"data": f"value_{i}"}

        # Act
        cache_manager._evict_memory_cache()

        # Assert
        # Should not evict anything since under limit
        assert len(cache_manager._memory_cache) == 5

    @pytest.mark.unit
    def test_evict_memory_cache_over_limit(self) -> None:
        """Test memory cache eviction when over size limit."""
        # Arrange
        cache_manager = EnhancedCacheManager()
        cache_manager._memory_cache_size_limit = 10
        # Add items to exceed limit
        for i in range(15):
            cache_manager._memory_cache[f"key_{i}"] = {"data": f"value_{i}"}

        # Act
        cache_manager._evict_memory_cache()

        # Assert
        # Should evict at least 1 item (10% of 15 = 1.5, rounded up to 2)
        assert len(cache_manager._memory_cache) < 15

    @pytest.mark.unit
    def test_is_cache_valid_not_expired(self) -> None:
        """Test cache validity check for non-expired data."""
        # Arrange
        cache_manager = EnhancedCacheManager()
        future_time = datetime.now(tz=UTC) + timedelta(hours=1)
        cache_data = {"expires_at": future_time.isoformat()}

        # Act
        result = cache_manager._is_cache_valid(cache_data)

        # Assert
        assert result is True

    @pytest.mark.unit
    def test_is_cache_valid_expired(self) -> None:
        """Test cache validity check for expired data."""
        # Arrange
        cache_manager = EnhancedCacheManager()
        past_time = datetime.now(tz=UTC) - timedelta(hours=1)
        cache_data = {"expires_at": past_time.isoformat()}

        # Act
        result = cache_manager._is_cache_valid(cache_data)

        # Assert
        assert result is False

    @pytest.mark.unit
    def test_is_cache_valid_invalid_format(self) -> None:
        """Test cache validity check with invalid data format."""
        # Arrange
        cache_manager = EnhancedCacheManager()
        cache_data = {"invalid": "data"}

        # Act
        result = cache_manager._is_cache_valid(cache_data)

        # Assert
        assert result is False

    @pytest.mark.unit
    def test_get_remaining_ttl_valid(self) -> None:
        """Test remaining TTL calculation for valid cache."""
        # Arrange
        cache_manager = EnhancedCacheManager()
        future_time = datetime.now(tz=UTC) + timedelta(hours=2)
        cache_data = {"expires_at": future_time.isoformat()}

        # Act
        result = cache_manager._get_remaining_ttl(cache_data)

        # Assert
        # Should be approximately 2 hours (7200 seconds), allow some tolerance
        assert 7190 <= result <= 7200

    @pytest.mark.unit
    def test_get_remaining_ttl_expired(self) -> None:
        """Test remaining TTL calculation for expired cache."""
        # Arrange
        cache_manager = EnhancedCacheManager()
        past_time = datetime.now(tz=UTC) - timedelta(hours=1)
        cache_data = {"expires_at": past_time.isoformat()}

        # Act
        result = cache_manager._get_remaining_ttl(cache_data)

        # Assert
        assert result == 0

    @pytest.mark.unit
    def test_store_file_cache_success(self) -> None:
        """Test successful file cache storage."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = EnhancedCacheManager(cache_dir=temp_dir)
            cache_key = "test_key"
            cache_data = {
                "data": {"test": "value"},
                "cached_at": datetime.now(tz=UTC).isoformat(),
                "expires_at": (datetime.now(tz=UTC) + timedelta(hours=1)).isoformat(),
            }

            # Act
            cache_manager._store_file_cache(cache_key, cache_data)

            # Assert
            cache_file = cache_manager._get_cache_file_path(cache_key)
            assert cache_file.exists()

            with cache_file.open(encoding="utf-8") as f:
                stored_data = json.load(f)
            assert stored_data == cache_data

    @pytest.mark.unit
    def test_load_file_cache_exists_valid(self) -> None:
        """Test loading valid file cache data."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = EnhancedCacheManager(cache_dir=temp_dir)
            cache_key = "test_key"
            cache_data = {
                "data": {"test": "value"},
                "cached_at": datetime.now(tz=UTC).isoformat(),
                "expires_at": (datetime.now(tz=UTC) + timedelta(hours=1)).isoformat(),
            }

            # Store data first
            cache_file = cache_manager._get_cache_file_path(cache_key)
            with cache_file.open("w", encoding="utf-8") as f:
                json.dump(cache_data, f)

            # Act
            result = cache_manager._load_file_cache(cache_key)

            # Assert
            assert result == cache_data

    @pytest.mark.unit
    def test_load_file_cache_not_exists(self) -> None:
        """Test loading file cache when file doesn't exist."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = EnhancedCacheManager(cache_dir=temp_dir)
            cache_key = "nonexistent_key"

            # Act
            result = cache_manager._load_file_cache(cache_key)

            # Assert
            assert result is None

    @pytest.mark.unit
    def test_load_file_cache_legacy_format(self) -> None:
        """Test loading file cache with legacy format (no metadata wrapper)."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = EnhancedCacheManager(cache_dir=temp_dir)
            cache_key = "legacy_key"
            legacy_data = {"test": "value"}  # Raw data without metadata

            # Store legacy format data
            cache_file = cache_manager._get_cache_file_path(cache_key)
            with cache_file.open("w", encoding="utf-8") as f:
                json.dump(legacy_data, f)

            # Act
            result = cache_manager._load_file_cache(cache_key)

            # Assert
            assert result is not None
            assert result["data"] == legacy_data
            assert "cached_at" in result
            assert "expires_at" in result
            assert result["cache_key"] == cache_key

    @pytest.mark.unit
    def test_delete_file_cache_exists(self) -> None:
        """Test deleting existing file cache."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = EnhancedCacheManager(cache_dir=temp_dir)
            cache_key = "test_key"
            cache_file = cache_manager._get_cache_file_path(cache_key)

            # Create file first
            cache_file.write_text('{"test": "data"}')
            assert cache_file.exists()

            # Act
            cache_manager._delete_file_cache(cache_key)

            # Assert
            assert not cache_file.exists()

    @pytest.mark.unit
    def test_delete_file_cache_not_exists(self) -> None:
        """Test deleting non-existent file cache."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = EnhancedCacheManager(cache_dir=temp_dir)
            cache_key = "nonexistent_key"

            # Act & Assert - Should not raise exception
            cache_manager._delete_file_cache(cache_key)

    @pytest.mark.unit
    def test_clear_file_cache(self) -> None:
        """Test clearing all file cache."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = EnhancedCacheManager(cache_dir=temp_dir)

            # Create some cache files
            for i in range(3):
                cache_file = cache_manager.cache_dir / f"test_{i}.json"
                cache_file.write_text('{"test": "data"}')

            assert len(list(cache_manager.cache_dir.glob("*.json"))) == 3

            # Act
            cache_manager._clear_file_cache()

            # Assert
            assert len(list(cache_manager.cache_dir.glob("*.json"))) == 0

    @pytest.mark.unit
    def test_cleanup_expired_files(self) -> None:
        """Test cleanup of expired file cache entries."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = EnhancedCacheManager(cache_dir=temp_dir)

            # Create expired cache file
            expired_data = {
                "data": {"test": "expired"},
                "expires_at": (datetime.now(tz=UTC) - timedelta(hours=1)).isoformat(),
            }
            expired_file = cache_manager.cache_dir / "expired.json"
            with expired_file.open("w", encoding="utf-8") as f:
                json.dump(expired_data, f)

            # Create valid cache file
            valid_data = {
                "data": {"test": "valid"},
                "expires_at": (datetime.now(tz=UTC) + timedelta(hours=1)).isoformat(),
            }
            valid_file = cache_manager.cache_dir / "valid.json"
            with valid_file.open("w", encoding="utf-8") as f:
                json.dump(valid_data, f)

            # Act
            result = cache_manager._cleanup_expired_files()

            # Assert
            assert result == 1  # One expired file cleaned
            assert not expired_file.exists()
            assert valid_file.exists()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_redis_client_disabled(self) -> None:
        """Test Redis client when Redis is disabled."""
        # Arrange
        cache_manager = EnhancedCacheManager(enable_redis=False)

        # Act
        result = await cache_manager._get_redis_client()

        # Assert
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_redis_client_connection_success(self) -> None:
        """Test successful Redis client connection."""
        # Arrange
        cache_manager = EnhancedCacheManager(enable_redis=True)
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        # Act
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            result = await cache_manager._get_redis_client()

        # Assert
        assert result == mock_redis
        assert cache_manager._redis_client == mock_redis
        mock_redis.ping.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_redis_client_connection_failure(self) -> None:
        """Test Redis client connection failure."""
        # Arrange
        cache_manager = EnhancedCacheManager(enable_redis=True)

        # Act
        with patch(
            "redis.asyncio.from_url",
            side_effect=RedisConnectionError("Connection failed"),
        ):
            result = await cache_manager._get_redis_client()

        # Assert
        assert result is None
        assert cache_manager.redis_enabled is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_set_memory_only(self) -> None:
        """Test setting data with Redis disabled (memory + file only)."""
        # Arrange
        cache_manager = EnhancedCacheManager(enable_redis=False)
        cache_key = "test_key"
        test_data = {"message": "hello"}

        # Act
        await cache_manager.set(cache_key, test_data, expiry_hours=1)

        # Assert
        # Check memory cache
        assert cache_key in cache_manager._memory_cache
        cached_data = cache_manager._memory_cache[cache_key]
        assert cached_data["data"] == test_data
        assert "expires_at" in cached_data

        # Check file cache
        cache_file = cache_manager._get_cache_file_path(cache_key)
        assert cache_file.exists()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_set_with_redis_success(self) -> None:
        """Test setting data with Redis enabled and working."""
        # Arrange
        cache_manager = EnhancedCacheManager(enable_redis=True)
        cache_key = "test_key"
        test_data = {"message": "hello"}

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.setex = AsyncMock()

        # Act
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            await cache_manager.set(cache_key, test_data, expiry_hours=2)

        # Assert
        # Check Redis was called
        session_db_key = f"cache:resource:{cache_key}"
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == session_db_key  # Key
        assert call_args[0][1] == 7200  # TTL (2 hours in seconds)
        # call_args[0][2] is the serialized data

        # Check memory cache
        assert cache_key in cache_manager._memory_cache

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_memory_cache_hit(self) -> None:
        """Test getting data from memory cache."""
        # Arrange
        cache_manager = EnhancedCacheManager(enable_redis=False)
        cache_key = "test_key"
        test_data = {"message": "hello"}

        # Set up memory cache directly with valid data
        cache_data = {
            "data": test_data,
            "expires_at": (datetime.now(tz=UTC) + timedelta(hours=1)).isoformat(),
        }
        cache_manager._memory_cache[cache_key] = cache_data

        # Act
        result = await cache_manager.get(cache_key)

        # Assert
        assert result == test_data

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_memory_cache_expired(self) -> None:
        """Test getting expired data from memory cache."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = EnhancedCacheManager(cache_dir=temp_dir, enable_redis=False)
            cache_key = "test_key"
            test_data = {"message": "hello"}

            # Set up memory cache with expired data
            cache_data = {
                "data": test_data,
                "expires_at": (datetime.now(tz=UTC) - timedelta(hours=1)).isoformat(),
            }
            cache_manager._memory_cache[cache_key] = cache_data

            # Act
            result = await cache_manager.get(cache_key)

            # Assert
            assert result is None
            # Expired data should be removed from memory cache
            assert cache_key not in cache_manager._memory_cache

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_redis_cache_hit(self) -> None:
        """Test getting data from Redis cache when memory cache misses."""
        # Arrange
        cache_manager = EnhancedCacheManager(enable_redis=True)
        cache_key = "test_key"
        test_data = {"message": "hello"}

        # Set up Redis mock
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        redis_cache_data = {
            "data": test_data,
            "expires_at": (datetime.now(tz=UTC) + timedelta(hours=1)).isoformat(),
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(redis_cache_data))

        # Act
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            result = await cache_manager.get(cache_key)

        # Assert
        assert result == test_data
        # Should also populate memory cache
        assert cache_key in cache_manager._memory_cache

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_redis_connection_failure(self) -> None:
        """Test getting data when Redis connection fails."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = EnhancedCacheManager(cache_dir=temp_dir, enable_redis=True)
            cache_key = "test_key"

            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock()
            mock_redis.get = AsyncMock(
                side_effect=RedisConnectionError("Connection failed")
            )

            # Act
            with patch("redis.asyncio.from_url", return_value=mock_redis):
                result = await cache_manager.get(cache_key)

            # Assert
            assert result is None
            # Redis should be disabled after failure
            assert cache_manager.redis_enabled is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_file_cache_hit(self) -> None:
        """Test getting data from file cache when higher tiers miss."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = EnhancedCacheManager(cache_dir=temp_dir, enable_redis=False)
            cache_key = "test_key"
            test_data = {"message": "hello"}

            # Set up file cache
            cache_data = {
                "data": test_data,
                "expires_at": (datetime.now(tz=UTC) + timedelta(hours=1)).isoformat(),
            }
            cache_file = cache_manager._get_cache_file_path(cache_key)
            with cache_file.open("w", encoding="utf-8") as f:
                json.dump(cache_data, f)

            # Act
            result = await cache_manager.get(cache_key)

            # Assert
            assert result == test_data
            # Should populate memory cache
            assert cache_key in cache_manager._memory_cache

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_cache_miss(self) -> None:
        """Test getting data when no cache exists."""
        # Arrange
        cache_manager = EnhancedCacheManager(enable_redis=False)
        cache_key = "nonexistent_key"

        # Act
        result = await cache_manager.get(cache_key)

        # Assert
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_all_tiers(self) -> None:
        """Test deleting data from all cache tiers."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = EnhancedCacheManager(cache_dir=temp_dir, enable_redis=True)
            cache_key = "test_key"
            test_data = {"message": "hello"}

            # Set up data in memory cache
            cache_manager._memory_cache[cache_key] = {"data": test_data}

            # Set up file cache
            cache_file = cache_manager._get_cache_file_path(cache_key)
            cache_file.write_text('{"data": "test"}')

            # Set up Redis mock
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock()
            mock_redis.delete = AsyncMock()

            # Act
            with patch("redis.asyncio.from_url", return_value=mock_redis):
                await cache_manager.delete(cache_key)

            # Assert
            # Check memory cache cleared
            assert cache_key not in cache_manager._memory_cache

            # Check Redis delete called
            session_db_key = f"cache:resource:{cache_key}"
            mock_redis.delete.assert_called_once_with(session_db_key)

            # Check file cache cleared
            assert not cache_file.exists()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_is_valid_exists_and_valid(self) -> None:
        """Test is_valid when cache exists and is valid."""
        # Arrange
        cache_manager = EnhancedCacheManager(enable_redis=False)
        cache_key = "test_key"
        test_data = {"message": "hello"}

        # Set up valid cache
        cache_data = {
            "data": test_data,
            "expires_at": (datetime.now(tz=UTC) + timedelta(hours=1)).isoformat(),
        }
        cache_manager._memory_cache[cache_key] = cache_data

        # Act
        result = await cache_manager.is_valid(cache_key)

        # Assert
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_is_valid_not_exists(self) -> None:
        """Test is_valid when cache doesn't exist."""
        # Arrange
        cache_manager = EnhancedCacheManager(enable_redis=False)
        cache_key = "nonexistent_key"

        # Act
        result = await cache_manager.is_valid(cache_key)

        # Assert
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_clear_all_tiers(self) -> None:
        """Test clearing all cache tiers."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = EnhancedCacheManager(cache_dir=temp_dir, enable_redis=True)

            # Set up memory cache
            cache_manager._memory_cache["key1"] = {"data": "value1"}
            cache_manager._memory_cache["key2"] = {"data": "value2"}

            # Set up file cache
            for i in range(3):
                cache_file = cache_manager.cache_dir / f"test_{i}.json"
                cache_file.write_text('{"test": "data"}')

            # Set up Redis mock
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock()
            mock_redis.keys = AsyncMock(
                return_value=["cache:resource:key1", "cache:resource:key2"]
            )
            mock_redis.delete = AsyncMock()

            # Act
            with patch("redis.asyncio.from_url", return_value=mock_redis):
                await cache_manager.clear_all()

            # Assert
            # Check memory cache cleared
            assert len(cache_manager._memory_cache) == 0

            # Check Redis cleared
            mock_redis.delete.assert_called_once_with(
                "cache:resource:key1", "cache:resource:key2"
            )

            # Check file cache cleared
            assert len(list(cache_manager.cache_dir.glob("*.json"))) == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_cache_stats_redis_enabled(self) -> None:
        """Test getting cache statistics with Redis enabled."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = EnhancedCacheManager(cache_dir=temp_dir, enable_redis=True)

            # Set up some data
            cache_manager._memory_cache["key1"] = {"data": "value1"}
            cache_manager._memory_cache["key2"] = {"data": "value2"}

            # Create file cache
            for i in range(2):
                cache_file = cache_manager.cache_dir / f"test_{i}.json"
                cache_file.write_text('{"test": "data"}')

            # Set up Redis mock
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock()
            mock_redis.keys = AsyncMock(
                return_value=["cache:resource:key1", "cache:resource:key2"]
            )

            # Act
            with patch("redis.asyncio.from_url", return_value=mock_redis):
                result = await cache_manager.get_cache_stats()

            # Assert
            assert result["memory_cache"]["items"] == 2
            assert result["memory_cache"]["size_limit"] == 1000
            assert result["file_cache"]["files"] == 2
            assert result["redis_cache"]["enabled"] is True
            assert result["redis_cache"]["connected"] is True
            assert result["redis_cache"]["items"] == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_cache_stats_redis_disabled(self) -> None:
        """Test getting cache statistics with Redis disabled."""
        # Arrange
        cache_manager = EnhancedCacheManager(enable_redis=False)

        # Act
        result = await cache_manager.get_cache_stats()

        # Assert
        assert result["memory_cache"]["items"] == 0
        assert result["redis_cache"]["enabled"] is False
        assert result["redis_cache"]["connected"] is False
        assert result["redis_cache"]["items"] == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cleanup_expired_memory_and_file(self) -> None:
        """Test cleanup of expired entries from memory and file cache."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = EnhancedCacheManager(cache_dir=temp_dir, enable_redis=False)

            # Set up expired memory cache
            expired_data = {
                "data": {"test": "expired"},
                "expires_at": (datetime.now(tz=UTC) - timedelta(hours=1)).isoformat(),
            }
            cache_manager._memory_cache["expired_key"] = expired_data

            # Set up valid memory cache
            valid_data = {
                "data": {"test": "valid"},
                "expires_at": (datetime.now(tz=UTC) + timedelta(hours=1)).isoformat(),
            }
            cache_manager._memory_cache["valid_key"] = valid_data

            # Set up expired file cache
            expired_file = cache_manager.cache_dir / "expired.json"
            with expired_file.open("w", encoding="utf-8") as f:
                json.dump(expired_data, f)

            # Act
            result = await cache_manager.cleanup_expired()

            # Assert
            assert result == 2  # 1 memory + 1 file
            assert "expired_key" not in cache_manager._memory_cache
            assert "valid_key" in cache_manager._memory_cache
            assert not expired_file.exists()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """Test closing cache manager and cleanup."""
        # Arrange
        cache_manager = EnhancedCacheManager(enable_redis=True)
        cache_manager._memory_cache["key1"] = {"data": "value1"}

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.close = AsyncMock()
        cache_manager._redis_client = mock_redis

        # Act
        await cache_manager.close()

        # Assert
        mock_redis.close.assert_called_once()
        assert len(cache_manager._memory_cache) == 0


class TestCacheManagerGlobalInstance:
    """Unit tests for the global cache manager instance."""

    @pytest.mark.unit
    def test_get_cache_manager_singleton(self) -> None:
        """Test that get_cache_manager returns the same instance."""
        # Act
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()

        # Assert
        assert manager1 is manager2
        assert isinstance(manager1, EnhancedCacheManager)

    @pytest.mark.unit
    def test_get_cache_manager_creates_instance(self) -> None:
        """Test that get_cache_manager creates an instance on first call."""
        # Arrange
        # Reset global instance
        import app.utils.cache_manager

        app.utils.cache_manager._enhanced_cache_manager = None

        # Act
        manager = get_cache_manager()

        # Assert
        assert isinstance(manager, EnhancedCacheManager)
        assert app.utils.cache_manager._enhanced_cache_manager is manager
