"""Caching decorators for function-level caching.

This module provides decorators for caching function results in Redis
with support for:
- TTL-based expiration
- Key generation from function arguments
- Cache invalidation
- Async function support
"""

from __future__ import annotations

import functools
import hashlib
import json
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar, cast

from app.cache.redis import get_cache_client
from app.observability.logging import get_logger


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from redis.asyncio import Redis

logger = get_logger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def _generate_cache_key(
    prefix: str,
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> str:
    """Generate a cache key from function and arguments.

    Args:
        prefix: Cache key prefix.
        func: The function being cached.
        args: Positional arguments.
        kwargs: Keyword arguments.

    Returns:
        A unique cache key string.
    """
    key_parts = [prefix, func.__module__, func.__name__]

    # Add args (skip 'self' for methods)
    for arg in args:
        try:
            key_parts.append(str(arg))
        except Exception:
            key_parts.append(str(id(arg)))

    # Add sorted kwargs
    for k, v in sorted(kwargs.items()):
        try:
            key_parts.append(f"{k}={v}")
        except Exception:
            key_parts.append(f"{k}={id(v)}")

    # Create a hash of the key parts for consistent length
    key_string = ":".join(key_parts)
    key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]

    return f"{prefix}:{func.__name__}:{key_hash}"


def cached(
    ttl: int = 300,
    prefix: str = "cache",
    key_builder: Callable[..., str] | None = None,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorator for caching async function results in Redis.

    Args:
        ttl: Time to live in seconds (default: 5 minutes).
        prefix: Cache key prefix for namespacing.
        key_builder: Optional custom key builder function.

    Returns:
        Decorated function with caching.

    Example:
        @cached(ttl=60, prefix="recipes")
        async def get_recipe(recipe_id: str) -> dict:
            ...
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Generate cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = _generate_cache_key(prefix, func, args, kwargs)

            try:
                client = get_cache_client()

                # Try to get from cache
                cached_value = await client.get(cache_key)
                if cached_value is not None:
                    logger.debug("Cache hit", key=cache_key)
                    return cast("R", json.loads(cached_value))

                logger.debug("Cache miss", key=cache_key)

            except RuntimeError:
                # Redis not initialized, skip caching
                logger.warning("Redis not available, skipping cache")
                return await func(*args, **kwargs)
            except Exception:
                # Log error but don't fail the request
                logger.exception("Cache read error", key=cache_key)
                return await func(*args, **kwargs)

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            try:
                await client.setex(cache_key, ttl, json.dumps(result))
                logger.debug("Cached result", key=cache_key, ttl=ttl)
            except Exception:
                logger.exception("Cache write error", key=cache_key)

            return result

        async def invalidate(*args: P.args, **kwargs: P.kwargs) -> bool:
            """Invalidate cached value for given arguments."""
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = _generate_cache_key(prefix, func, args, kwargs)

            try:
                client = get_cache_client()
                deleted = await client.delete(cache_key)
                logger.debug("Cache invalidated", key=cache_key, deleted=deleted)
            except Exception:
                logger.exception("Cache invalidation error")
                return False
            else:
                return deleted > 0

        wrapper.invalidate = invalidate  # type: ignore[attr-defined]

        return wrapper

    return decorator


def cache_key(*key_parts: str) -> str:
    """Build a cache key from parts.

    Args:
        key_parts: Parts to join with colons.

    Returns:
        Joined cache key string.

    Example:
        key = cache_key("recipes", recipe_id, "details")
        # Returns: "recipes:abc123:details"
    """
    return ":".join(str(part) for part in key_parts)


class CacheManager:
    """Manager class for cache operations.

    Provides methods for direct cache manipulation beyond decorators.
    """

    def __init__(self, prefix: str = "app") -> None:
        """Initialize cache manager.

        Args:
            prefix: Default prefix for cache keys.
        """
        self.prefix = prefix

    def _make_key(self, key: str) -> str:
        """Make a full cache key with prefix."""
        return f"{self.prefix}:{key}"

    def _get_client(self) -> Redis[Any]:
        """Get Redis client, raising if not available."""
        return get_cache_client()

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value from cache.

        Args:
            key: Cache key (without prefix).
            default: Default value if not found.

        Returns:
            Cached value or default.
        """
        try:
            client = self._get_client()
            value = await client.get(self._make_key(key))
            if value is None:
                return default
            return json.loads(value)
        except Exception:
            logger.exception("Cache get error", key=key)
            return default

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 300,
    ) -> bool:
        """Set a value in cache.

        Args:
            key: Cache key (without prefix).
            value: Value to cache (must be JSON serializable).
            ttl: Time to live in seconds.

        Returns:
            True if successful, False otherwise.
        """
        try:
            client = self._get_client()
            await client.setex(self._make_key(key), ttl, json.dumps(value))
        except Exception:
            logger.exception("Cache set error", key=key)
            return False
        else:
            return True

    async def delete(self, key: str) -> bool:
        """Delete a value from cache.

        Args:
            key: Cache key (without prefix).

        Returns:
            True if deleted, False otherwise.
        """
        try:
            client = self._get_client()
            deleted = await client.delete(self._make_key(key))
        except Exception:
            logger.exception("Cache delete error", key=key)
            return False
        else:
            return deleted > 0

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern.

        Args:
            pattern: Key pattern with wildcards (e.g., "user:*:profile").

        Returns:
            Number of keys deleted.
        """
        try:
            client = self._get_client()
            full_pattern = self._make_key(pattern)

            # Use SCAN to find matching keys
            keys = [
                key async for key in client.scan_iter(match=full_pattern, count=100)
            ]

            if keys:
                deleted = await client.delete(*keys)
                logger.debug("Deleted keys by pattern", pattern=pattern, count=deleted)
                return int(deleted)
        except Exception:
            logger.exception("Cache delete pattern error", pattern=pattern)
        return 0

    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache.

        Args:
            key: Cache key (without prefix).

        Returns:
            True if exists, False otherwise.
        """
        try:
            client = self._get_client()
            return await client.exists(self._make_key(key)) > 0
        except Exception:
            logger.exception("Cache exists error", key=key)
            return False

    async def ttl(self, key: str) -> int:
        """Get remaining TTL for a key.

        Args:
            key: Cache key (without prefix).

        Returns:
            TTL in seconds, -1 if no TTL, -2 if not found.
        """
        try:
            client = self._get_client()
            return await client.ttl(self._make_key(key))
        except Exception:
            logger.exception("Cache ttl error", key=key)
            return -2


# Default cache manager instance
cache = CacheManager()
