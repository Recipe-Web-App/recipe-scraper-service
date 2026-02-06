"""ARQ worker configuration.

This module provides:
- Worker settings and configuration
- Redis connection pool for workers
- Startup/shutdown handlers
- Cron job scheduling
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any, ClassVar

from arq import cron
from arq.connections import RedisSettings
from redis.asyncio import Redis

from app.core.config import get_settings
from app.llm.client.fallback import FallbackLLMClient
from app.llm.client.groq import GroqClient
from app.llm.client.ollama import OllamaClient
from app.observability.logging import get_logger, setup_logging
from app.workers.tasks.example import (
    cleanup_expired_cache,
    process_recipe_scrape,
    send_notification,
)
from app.workers.tasks.popular_recipes import (
    check_and_refresh_popular_recipes,
    refresh_popular_recipes,
)


if TYPE_CHECKING:
    from arq.cron import CronJob

    from app.llm.client.protocol import LLMClientProtocol


logger = get_logger(__name__)

# Type alias for ARQ worker functions
WorkerFunction = Callable[..., Coroutine[Any, Any, Any]]


async def startup(ctx: dict[str, Any]) -> None:
    """Worker startup handler.

    Called when the worker starts. Use for initialization.

    Args:
        ctx: Worker context dictionary for storing shared state.
    """
    settings = get_settings()

    # Setup logging
    setup_logging(
        log_level=settings.logging.level,
        log_format=settings.logging.format,
        is_development=settings.is_development,
    )

    logger.info(
        "ARQ worker starting",
        environment=settings.APP_ENV,
    )

    # Store settings in context for tasks
    ctx["settings"] = settings

    # Initialize Redis cache client (uses cache DB, not queue DB)
    ctx["cache_client"] = Redis.from_url(
        settings.redis_cache_url,
        decode_responses=False,  # Keep bytes for orjson
    )
    logger.debug("Initialized cache client for worker")

    # Initialize LLM client for recipe extraction
    if settings.llm.enabled:
        # Create primary client based on provider setting
        primary: LLMClientProtocol
        if settings.llm.provider == "groq":
            if not settings.GROQ_API_KEY:
                logger.warning(
                    "Groq selected as primary but GROQ_API_KEY not set - LLM disabled"
                )
                ctx["llm_client"] = None
                return
            primary = GroqClient(
                api_key=settings.GROQ_API_KEY,
                model=settings.llm.groq.model,
                timeout=settings.llm.groq.timeout,
                max_retries=settings.llm.groq.max_retries,
                requests_per_minute=settings.llm.groq.requests_per_minute,
            )
        else:
            # Default to Ollama
            primary = OllamaClient(
                base_url=settings.llm.ollama.url,
                model=settings.llm.ollama.model,
                timeout=settings.llm.ollama.timeout,
                max_retries=settings.llm.ollama.max_retries,
            )
        await primary.initialize()

        # Create secondary client (Groq) if fallback enabled and API key present
        secondary: LLMClientProtocol | None = None
        if (
            settings.llm.fallback.enabled
            and settings.llm.fallback.secondary_provider == "groq"
            and settings.GROQ_API_KEY
            and settings.llm.provider != "groq"  # Don't use same provider for fallback
        ):
            secondary = GroqClient(
                api_key=settings.GROQ_API_KEY,
                model=settings.llm.groq.model,
                timeout=settings.llm.groq.timeout,
                max_retries=settings.llm.groq.max_retries,
                requests_per_minute=settings.llm.groq.requests_per_minute,
            )
            await secondary.initialize()
            logger.debug(
                "Initialized Groq fallback client for worker",
                model=settings.llm.groq.model,
            )

        ctx["llm_client"] = FallbackLLMClient(
            primary=primary,
            secondary=secondary,
            fallback_enabled=settings.llm.fallback.enabled,
        )
        primary_model = (
            settings.llm.groq.model
            if settings.llm.provider == "groq"
            else settings.llm.ollama.model
        )
        logger.info(
            "Initialized LLM client for worker",
            primary_provider=settings.llm.provider,
            primary_model=primary_model,
            fallback_enabled=settings.llm.fallback.enabled,
            has_fallback=secondary is not None,
        )
    else:
        ctx["llm_client"] = None
        logger.debug("LLM client disabled")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Worker shutdown handler.

    Called when the worker stops. Use for cleanup.

    Args:
        ctx: Worker context dictionary containing initialized resources.
    """
    logger.info("ARQ worker shutting down")

    # Close cache client
    if ctx.get("cache_client"):
        await ctx["cache_client"].close()
        logger.debug("Closed cache client")

    # Close LLM client
    if ctx.get("llm_client"):
        await ctx["llm_client"].shutdown()
        logger.debug("Closed LLM client")


# Redis key names - must match Redis ACL pattern (scraper:*)
ARQ_QUEUE_NAME = "scraper:queue:jobs"
ARQ_HEALTH_CHECK_KEY = "scraper:queue:health-check"


def get_redis_settings() -> RedisSettings:
    """Get Redis settings for ARQ.

    Returns:
        RedisSettings configured for the job queue.
    """
    settings = get_settings()

    return RedisSettings(
        host=settings.redis.host,
        port=settings.redis.port,
        username=settings.redis.user,
        password=settings.REDIS_PASSWORD or None,
        database=settings.redis.queue_db,
    )


class WorkerSettings:
    """ARQ worker settings class.

    This class is used by the arq CLI to configure the worker.
    Run with: arq app.workers.arq.WorkerSettings
    """

    # Redis connection settings
    redis_settings = get_redis_settings()

    # Queue name - must match Redis ACL key pattern (scraper:*)
    queue_name = ARQ_QUEUE_NAME

    # Health check key - must match Redis ACL key pattern (scraper:*)
    health_check_key = ARQ_HEALTH_CHECK_KEY

    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown

    # Job timeout (default: 5 minutes)
    job_timeout = 300

    # Maximum number of concurrent jobs
    max_jobs = 10

    # How long to keep job results (default: 1 hour)
    keep_result = 3600

    # Maximum retries for failed jobs
    max_tries = 3

    # Registered task functions
    functions: ClassVar[list[WorkerFunction]] = [
        send_notification,
        cleanup_expired_cache,
        process_recipe_scrape,
        refresh_popular_recipes,
        check_and_refresh_popular_recipes,
    ]

    # Cron jobs (scheduled tasks)
    cron_jobs: ClassVar[list[CronJob]] = [
        # Run cache cleanup every hour at minute 0
        cron(cleanup_expired_cache, hour=None, minute=0),  # type: ignore[arg-type]
        # Check popular recipes cache TTL every 30 minutes
        cron(check_and_refresh_popular_recipes, minute={0, 30}),
    ]
