"""Popular recipes background tasks.

This module provides ARQ tasks for:
- Refreshing the popular recipes cache
- Proactive cache refresh via cron job
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.config import get_settings
from app.observability.logging import get_logger
from app.services.popular.service import PopularRecipesService


if TYPE_CHECKING:
    from redis.asyncio import Redis

    from app.llm.client.protocol import LLMClientProtocol

logger = get_logger(__name__)


async def refresh_popular_recipes(ctx: dict[str, Any]) -> dict[str, Any]:
    """Fetch and cache popular recipes from all sources.

    This task performs the CPU-intensive work of:
    1. Fetching HTML from configured recipe sources
    2. Extracting recipe links (using LLM or regex)
    3. Fetching individual recipe pages for metrics
    4. Scoring and caching the results

    Called by:
    - Cron job (proactive refresh when TTL < threshold)
    - Endpoint (on cache miss via job enqueue)

    Args:
        ctx: ARQ worker context containing shared dependencies:
            - cache_client: Redis client for caching
            - llm_client: LLM client for extraction (optional)
            - settings: Application settings

    Returns:
        Result dict with status, recipe count, and sources processed.
    """
    cache_client: Redis[bytes] | None = ctx.get("cache_client")
    llm_client: LLMClientProtocol | None = ctx.get("llm_client")

    logger.info("Starting popular recipes refresh")

    # Create and initialize service
    service = PopularRecipesService(
        cache_client=cache_client,
        llm_client=llm_client,
    )
    await service.initialize()

    try:
        # Force refresh (fetch and cache)
        data = await service.refresh_cache()

        logger.info(
            "Popular recipes refresh completed",
            total_count=data.total_count,
            sources_fetched=data.sources_fetched,
            fetch_errors=list(data.fetch_errors.keys()) if data.fetch_errors else [],
        )

        return {
            "status": "completed",
            "recipe_count": data.total_count,
            "sources_fetched": data.sources_fetched,
            "sources_failed": list(data.fetch_errors.keys())
            if data.fetch_errors
            else [],
        }
    finally:
        await service.shutdown()


async def check_and_refresh_popular_recipes(ctx: dict[str, Any]) -> dict[str, Any]:
    """Cron job: Check cache TTL and refresh if expiring soon.

    Runs periodically (e.g., every 30 minutes). Refreshes the cache if:
    - Cache key doesn't exist
    - TTL is below the configured threshold (default: 1 hour)

    This ensures the cache is always warm and users rarely hit a cache miss.

    Args:
        ctx: ARQ worker context containing shared dependencies.

    Returns:
        Result dict with status and TTL information.
    """
    cache_client: Redis[bytes] | None = ctx.get("cache_client")
    settings = get_settings()
    config = settings.scraping.popular_recipes

    if not cache_client:
        logger.warning("Cache client not available, skipping TTL check")
        return {"status": "skipped", "reason": "no_cache_client"}

    cache_key = f"popular:{config.cache_key}"

    # Check TTL
    ttl = await cache_client.ttl(cache_key)

    # TTL returns:
    #  -2 if key doesn't exist
    #  -1 if key exists but has no expiry
    #  >= 0 for remaining TTL in seconds
    if ttl == -2:
        logger.info("Cache key missing, triggering refresh", cache_key=cache_key)
        return await refresh_popular_recipes(ctx)

    if ttl == -1:
        logger.warning(
            "Cache key has no expiry, triggering refresh", cache_key=cache_key
        )
        return await refresh_popular_recipes(ctx)

    if ttl < config.refresh_threshold:
        logger.info(
            "Cache expiring soon, triggering refresh",
            ttl_remaining=ttl,
            threshold=config.refresh_threshold,
        )
        return await refresh_popular_recipes(ctx)

    logger.debug(
        "Cache healthy, skipping refresh",
        ttl_remaining=ttl,
        threshold=config.refresh_threshold,
    )
    return {"status": "skipped", "ttl_remaining": ttl}
