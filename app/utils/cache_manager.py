"""Enhanced cache manager with Redis support and metrics.

This module provides a multi-tier caching system supporting both file-based and Redis
caching with comprehensive monitoring and metrics collection.
"""

import asyncio
import json
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TypeVar

import redis.asyncio as aioredis
from prometheus_client import Counter, Gauge, Histogram

from app.core.config.config import get_settings
from app.core.logging import get_logger

_log = get_logger(__name__)
settings = get_settings()

T = TypeVar("T")

# Prometheus metrics
cache_hits = Counter(
    "cache_hits_total", "Total number of cache hits", ["cache_type", "key_prefix"]
)

cache_misses = Counter(
    "cache_misses_total", "Total number of cache misses", ["cache_type", "key_prefix"]
)

cache_operations = Histogram(
    "cache_operation_duration_seconds",
    "Time spent on cache operations",
    ["operation", "cache_type"],
)

cache_size = Gauge("cache_size_bytes", "Current cache size in bytes", ["cache_type"])

cache_keys_count = Gauge(
    "cache_keys_total", "Total number of cached keys", ["cache_type"]
)


class EnhancedCacheManager:
    """Enhanced multi-tier cache manager with Redis support and monitoring.

    This class provides a sophisticated caching system with:
    - File-based caching (L3 cache)
    - Redis caching (L2 cache) - optional
    - In-memory caching (L1 cache)
    - Comprehensive metrics and monitoring
    - Async operations for better performance

    Example:
        cache = EnhancedCacheManager()
        await cache.set("my_data", {"key": "value"}, expiry_hours=24)
        data = await cache.get("my_data")  # Returns data if not expired
    """

    def __init__(self, cache_dir: str | None = None, enable_redis: bool = True) -> None:
        """Initialize enhanced cache manager.

        Args:     cache_dir: Directory to store cache files. If None, uses default.
        enable_redis: Whether to enable Redis caching layer.
        """
        # File cache setup
        if cache_dir is None:
            default_cache_dir = Path(tempfile.gettempdir()) / "recipe_cache_enhanced"
            self.cache_dir = default_cache_dir
        else:
            self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache (L1)
        self._memory_cache: dict[str, dict[str, Any]] = {}
        self._memory_cache_size_limit = 1000  # Max number of items

        # Redis setup (L2)
        self.redis_enabled = enable_redis
        self._redis_client: aioredis.Redis | None = None

        _log.info(
            "Initialized Enhanced CacheManager - File: {}, Redis: {}, Memory: enabled",
            self.cache_dir,
            "enabled" if self.redis_enabled else "disabled",
        )

    async def _get_redis_client(self) -> aioredis.Redis | None:
        """Get Redis client, creating connection if needed.

        Returns:     Redis client or None if Redis is not available
        """
        if not self.redis_enabled:
            return None

        if self._redis_client is None:
            self._redis_client = aioredis.from_url(
                settings.redis_url, encoding="utf-8", decode_responses=True
            )
            # Test connection
            await self._redis_client.ping()
            _log.info("Redis connection established")

        return self._redis_client

    def _get_key_prefix(self, cache_key: str) -> str:
        """Extract key prefix for metrics.

        Args:     cache_key: Full cache key

        Returns:     Key prefix for metrics grouping
        """
        return cache_key.split(":")[0] if ":" in cache_key else "default"

    def _evict_memory_cache(self) -> None:
        """Evict oldest items from memory cache if over limit."""
        if len(self._memory_cache) >= self._memory_cache_size_limit:
            # Remove 10% of oldest items (simple LRU approximation)
            items_to_remove = max(1, len(self._memory_cache) // 10)
            keys_to_remove = list(self._memory_cache.keys())[:items_to_remove]
            for key in keys_to_remove:
                del self._memory_cache[key]

    def _get_cache_file_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key.

        Args:     cache_key: The cache key

        Returns:     Path to the cache data file
        """
        return self.cache_dir / f"{cache_key}.json"

    async def set(
        self,
        cache_key: str,
        data: list[dict[str, Any]] | dict[str, Any] | str | float | bool,
        expiry_hours: int = 24,
    ) -> None:
        """Store data in multi-tier cache with expiration time.

        Args:     cache_key: Unique key for the cached data     data: Data to cache
        (must be JSON serializable)     expiry_hours: Hours until cache expires
        (default: 24)

        Raises:     OSError: If data cannot be written to cache files     ValueError: If
        data cannot be JSON serialized
        """
        start_time = time.time()

        try:
            now = datetime.now(tz=UTC)
            expiry_time = now + timedelta(hours=expiry_hours)

            cache_data = {
                "data": data,
                "cached_at": now.isoformat(),
                "expires_at": expiry_time.isoformat(),
                "expiry_hours": expiry_hours,
                "cache_key": cache_key,
            }

            # Store in memory cache (L1)
            self._evict_memory_cache()
            self._memory_cache[cache_key] = cache_data

            # Store in Redis cache (L2) if available
            redis_client = await self._get_redis_client()
            if redis_client:
                serialized_data = json.dumps(
                    cache_data, default=str, ensure_ascii=False
                )
                expiry_seconds = int(expiry_hours * 3600)
                await redis_client.setex(
                    f"cache:{cache_key}", expiry_seconds, serialized_data
                )
                _log.debug("Stored in Redis cache: {}", cache_key)

            # Store in file cache (L3)
            await asyncio.get_event_loop().run_in_executor(
                None, self._store_file_cache, cache_key, cache_data
            )

            # Update metrics
            cache_operations.labels(operation="set", cache_type="multi").observe(
                time.time() - start_time
            )

            _log.info(
                "Cached data for key '{}' with expiry at {} (multi-tier)",
                cache_key,
                expiry_time,
            )

        except Exception as e:
            _log.error("Failed to cache data for key '{}': {}", cache_key, e)
            raise

    def _store_file_cache(self, cache_key: str, cache_data: dict[str, Any]) -> None:
        """Store data in file cache (synchronous helper).

        Args:     cache_key: Cache key     cache_data: Data with metadata to store
        """
        try:
            cache_file = self._get_cache_file_path(cache_key)

            with cache_file.open("w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, default=str, ensure_ascii=False)

        except (OSError, ValueError) as e:
            _log.error("Failed to write file cache for key '{}': {}", cache_key, e)

    async def get(
        self, cache_key: str
    ) -> list[dict[str, Any]] | dict[str, Any] | str | int | float | bool | None:
        """Retrieve data from multi-tier cache if not expired.

        Args:     cache_key: Unique key for the cached data

        Returns:     Cached data if valid and not expired, None otherwise
        """
        start_time = time.time()
        key_prefix = self._get_key_prefix(cache_key)

        # Check memory cache first (L1)
        if cache_key in self._memory_cache:
            cache_data = self._memory_cache[cache_key]
            if self._is_cache_valid(cache_data):
                cache_hits.labels(cache_type="memory", key_prefix=key_prefix).inc()
                cache_operations.labels(operation="get", cache_type="memory").observe(
                    time.time() - start_time
                )
                _log.debug("Memory cache hit for key '{}'", cache_key)
                return cache_data["data"]
            # Remove expired data from memory
            del self._memory_cache[cache_key]

        # Check Redis cache (L2)
        redis_client = await self._get_redis_client()
        if redis_client:
            redis_data = await redis_client.get(f"cache:{cache_key}")
            if redis_data:
                cache_data = json.loads(redis_data)
                if self._is_cache_valid(cache_data):
                    # Store back in memory cache
                    self._memory_cache[cache_key] = cache_data
                    cache_hits.labels(cache_type="redis", key_prefix=key_prefix).inc()
                    cache_operations.labels(
                        operation="get", cache_type="redis"
                    ).observe(time.time() - start_time)
                    _log.debug("Redis cache hit for key '{}'", cache_key)
                    return cache_data["data"]

        # Check file cache (L3)
        file_data = await asyncio.get_event_loop().run_in_executor(
            None, self._load_file_cache, cache_key
        )

        if file_data and self._is_cache_valid(file_data):
            # Store back in higher-tier caches
            self._memory_cache[cache_key] = file_data

            if redis_client:
                expiry_seconds = self._get_remaining_ttl(file_data)
                if expiry_seconds > 0:
                    serialized_data = json.dumps(file_data, default=str)
                    await redis_client.setex(
                        f"cache:{cache_key}", expiry_seconds, serialized_data
                    )

            cache_hits.labels(cache_type="file", key_prefix=key_prefix).inc()
            cache_operations.labels(operation="get", cache_type="file").observe(
                time.time() - start_time
            )
            _log.debug("File cache hit for key '{}'", cache_key)
            return file_data["data"]

        # Cache miss
        cache_misses.labels(cache_type="multi", key_prefix=key_prefix).inc()
        cache_operations.labels(operation="get", cache_type="multi").observe(
            time.time() - start_time
        )
        _log.debug("Cache miss for key '{}'", cache_key)
        return None

    def _is_cache_valid(self, cache_data: dict[str, Any]) -> bool:
        """Check if cache data is still valid.

        Args:     cache_data: Cache data with metadata

        Returns:     True if cache is valid, False if expired
        """
        try:
            expires_at = datetime.fromisoformat(cache_data["expires_at"])
            return datetime.now(tz=UTC) <= expires_at
        except (KeyError, ValueError):
            return False

    def _get_remaining_ttl(self, cache_data: dict[str, Any]) -> int:
        """Get remaining TTL in seconds.

        Args:     cache_data: Cache data with metadata

        Returns:     Remaining TTL in seconds
        """
        try:
            expires_at = datetime.fromisoformat(cache_data["expires_at"])
            remaining = expires_at - datetime.now(tz=UTC)
            return max(0, int(remaining.total_seconds()))
        except (KeyError, ValueError):
            return 0

    def _load_file_cache(self, cache_key: str) -> dict[str, Any] | None:
        """Load data from file cache (synchronous helper).

        Args:     cache_key: Cache key

        Returns:     Cache data or None if not found/expired
        """
        try:
            cache_file = self._get_cache_file_path(cache_key)

            if not cache_file.exists():
                return None

            with cache_file.open(encoding="utf-8") as f:
                cache_data = json.load(f)

            # Handle legacy format (without metadata wrapper)
            if "data" not in cache_data:
                # Legacy format - wrap in new format
                return {
                    "data": cache_data,
                    "cached_at": datetime.now(tz=UTC).isoformat(),
                    "expires_at": (
                        datetime.now(tz=UTC) + timedelta(hours=24)
                    ).isoformat(),
                    "cache_key": cache_key,
                }
        except (OSError, ValueError, KeyError) as e:
            _log.debug("Failed to load file cache for key '{}': {}", cache_key, e)
            return None
        else:
            return cache_data

    async def delete(self, cache_key: str) -> None:
        """Delete cached data from all cache tiers.

        Args:     cache_key: Unique key for the cached data
        """
        # Delete from memory cache
        if cache_key in self._memory_cache:
            del self._memory_cache[cache_key]
            _log.debug("Deleted from memory cache: {}", cache_key)

        # Delete from Redis cache
        redis_client = await self._get_redis_client()
        if redis_client:
            await redis_client.delete(f"cache:{cache_key}")
            _log.debug("Deleted from Redis cache: {}", cache_key)

        # Delete from file cache
        await asyncio.get_event_loop().run_in_executor(
            None, self._delete_file_cache, cache_key
        )

    def _delete_file_cache(self, cache_key: str) -> None:
        """Delete file cache (synchronous helper).

        Args:     cache_key: Cache key
        """
        try:
            cache_file = self._get_cache_file_path(cache_key)

            if cache_file.exists():
                cache_file.unlink()
                _log.debug("Deleted file cache for key '{}'", cache_key)

        except OSError as e:
            _log.error("Failed to delete file cache for key '{}': {}", cache_key, e)

    async def is_valid(self, cache_key: str) -> bool:
        """Check if cache exists and is not expired.

        Args:     cache_key: Unique key for the cached data

        Returns:     True if cache is valid and not expired, False otherwise
        """
        result = await self.get(cache_key)
        return result is not None

    async def clear_all(self) -> None:
        """Clear all cached data from all tiers."""
        # Clear memory cache
        memory_count = len(self._memory_cache)
        self._memory_cache.clear()
        _log.info("Cleared {} items from memory cache", memory_count)

        # Clear Redis cache
        redis_client = await self._get_redis_client()
        if redis_client:
            keys = await redis_client.keys("cache:*")
            if keys:
                await redis_client.delete(*keys)
                _log.info("Cleared {} items from Redis cache", len(keys))

        # Clear file cache
        await asyncio.get_event_loop().run_in_executor(None, self._clear_file_cache)

    def _clear_file_cache(self) -> None:
        """Clear file cache (synchronous helper)."""
        try:
            files_deleted = 0
            for file in self.cache_dir.glob("*.json"):
                file.unlink()
                files_deleted += 1
            _log.info("Cleared {} files from file cache", files_deleted)
        except OSError as e:
            _log.error("Failed to clear file cache: {}", e)

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics.

        Returns:     Dictionary with cache statistics
        """
        stats = {
            "memory_cache": {
                "items": len(self._memory_cache),
                "size_limit": self._memory_cache_size_limit,
            },
            "file_cache": {
                "directory": str(self.cache_dir),
                "files": len(list(self.cache_dir.glob("*.json"))),
            },
            "redis_cache": {
                "enabled": self.redis_enabled,
                "connected": False,
                "items": 0,
            },
        }

        # Get Redis stats if available
        redis_client = await self._get_redis_client()
        if redis_client:
            keys = await redis_client.keys("cache:*")
            stats["redis_cache"]["connected"] = True
            stats["redis_cache"]["items"] = len(keys)

        return stats

    async def cleanup_expired(self) -> int:
        """Clean up expired cache entries from all tiers.

        Returns:     Number of expired entries removed
        """
        cleaned = 0

        # Clean memory cache
        expired_keys = [
            key
            for key, data in self._memory_cache.items()
            if not self._is_cache_valid(data)
        ]
        for key in expired_keys:
            del self._memory_cache[key]
            cleaned += 1

        # Clean file cache
        file_cleaned = await asyncio.get_event_loop().run_in_executor(
            None, self._cleanup_expired_files
        )
        cleaned += file_cleaned

        _log.info("Cleaned up {} expired cache entries", cleaned)
        return cleaned

    def _cleanup_expired_files(self) -> int:
        """Clean up expired file cache entries (synchronous helper).

        Returns:     Number of files cleaned up
        """
        cleaned = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with cache_file.open(encoding="utf-8") as f:
                    cache_data = json.load(f)

                if not self._is_cache_valid(cache_data):
                    cache_file.unlink()
                    cleaned += 1

            except (OSError, ValueError, KeyError):
                # Remove corrupted files
                cache_file.unlink()
                cleaned += 1

        return cleaned

    async def close(self) -> None:
        """Close cache manager and cleanup resources."""
        if self._redis_client:
            await self._redis_client.close()
            _log.info("Redis connection closed")

        self._memory_cache.clear()
        _log.info("Enhanced cache manager closed")


# Global enhanced cache manager instance
_enhanced_cache_manager: EnhancedCacheManager | None = None


def get_cache_manager() -> EnhancedCacheManager:
    """Get global cache manager instance.

    Returns:     EnhancedCacheManager instance
    """
    global _enhanced_cache_manager  # noqa: PLW0603
    if _enhanced_cache_manager is None:
        _enhanced_cache_manager = EnhancedCacheManager()
    return _enhanced_cache_manager
