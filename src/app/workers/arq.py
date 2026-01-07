"""ARQ worker configuration.

This module provides:
- Worker settings and configuration
- Redis connection pool for workers
- Startup/shutdown handlers
- Cron job scheduling
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any, ClassVar

from arq import cron
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.observability.logging import get_logger, setup_logging
from app.workers.tasks.example import (
    cleanup_expired_cache,
    process_recipe_scrape,
    send_notification,
)


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
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
        is_development=settings.is_development,
    )

    logger.info(
        "ARQ worker starting",
        environment=settings.ENVIRONMENT,
    )

    # Store settings in context for tasks
    ctx["settings"] = settings


async def shutdown(_ctx: dict[str, Any]) -> None:
    """Worker shutdown handler.

    Called when the worker stops. Use for cleanup.

    Args:
        _ctx: Worker context dictionary (unused).
    """
    logger.info("ARQ worker shutting down")


def get_redis_settings() -> RedisSettings:
    """Get Redis settings for ARQ.

    Returns:
        RedisSettings configured for the job queue.
    """
    settings = get_settings()

    return RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD or None,
        database=settings.REDIS_QUEUE_DB,
    )


class WorkerSettings:
    """ARQ worker settings class.

    This class is used by the arq CLI to configure the worker.
    Run with: arq app.workers.arq.WorkerSettings
    """

    # Redis connection settings
    redis_settings = get_redis_settings()

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
    ]

    # Cron jobs (scheduled tasks)
    cron_jobs: ClassVar[list[cron]] = [
        # Run cache cleanup every hour at minute 0
        cron(cleanup_expired_cache, hour=None, minute=0),
    ]
