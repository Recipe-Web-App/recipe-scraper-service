"""Application lifespan event handlers.

This module defines the lifespan context manager that handles:
- Application startup: Initialize connections, warm caches, etc.
- Application shutdown: Close connections, flush buffers, etc.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from app.cache.redis import close_redis_pools, init_redis_pools
from app.core.config import get_settings
from app.observability.logging import get_logger, setup_logging
from app.workers.jobs import close_arq_pool, get_arq_pool


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import FastAPI

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Manage application lifespan events.

    This context manager handles startup and shutdown events for the application.
    Resources initialized here are available throughout the application's lifetime.

    Args:
        _app: The FastAPI application instance (unused, for future extensions).

    Yields:
        None - control returns to the application to handle requests.
    """
    settings = get_settings()

    # === STARTUP ===
    logger.info(
        "Starting application",
        app_name=settings.APP_NAME,
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
    )

    # Initialize logging
    setup_logging(
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
        is_development=settings.is_development,
    )

    # Initialize Redis connection pools
    try:
        await init_redis_pools()
    except Exception:
        logger.exception("Failed to initialize Redis - continuing without cache")

    # Initialize ARQ connection pool for job enqueuing
    try:
        await get_arq_pool()
    except Exception:
        logger.exception("Failed to initialize ARQ pool - background jobs unavailable")

    logger.info("Application startup complete")

    yield

    # === SHUTDOWN ===
    logger.info("Shutting down application")

    # Close ARQ connection pool
    await close_arq_pool()

    # Close Redis connection pools
    await close_redis_pools()

    logger.info("Application shutdown complete")
