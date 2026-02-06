"""Redis caching layer.

This module provides:
- Redis connection management
- Caching decorators for functions
- Cache manager for direct operations
- Rate limiting with SlowAPI
"""

from app.cache.decorators import CacheManager, cache, cache_key, cached
from app.cache.rate_limit import (
    limiter,
    rate_limit,
    rate_limit_auth,
    setup_rate_limiting,
)
from app.cache.redis import (
    check_redis_health,
    close_redis_pools,
    get_cache_client,
    get_queue_client,
    get_rate_limit_client,
    init_redis_pools,
)


__all__ = [
    # Caching
    "CacheManager",
    "cache",
    "cache_key",
    "cached",
    # Connection management
    "check_redis_health",
    "close_redis_pools",
    "get_cache_client",
    "get_queue_client",
    "get_rate_limit_client",
    "init_redis_pools",
    # Rate limiting
    "limiter",
    "rate_limit",
    "rate_limit_auth",
    "setup_rate_limiting",
]
