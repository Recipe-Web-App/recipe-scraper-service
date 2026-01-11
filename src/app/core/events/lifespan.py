"""Application lifespan event handlers.

This module defines the lifespan context manager that handles:
- Application startup: Initialize connections, warm caches, etc.
- Application shutdown: Close connections, flush buffers, etc.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from app.auth.providers import initialize_auth_provider, shutdown_auth_provider
from app.cache.redis import close_redis_pools, get_cache_client, init_redis_pools
from app.core.config import AuthMode, get_settings
from app.observability.logging import get_logger, setup_logging
from app.observability.tracing import shutdown_tracing
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
        app_name=settings.app.name,
        environment=settings.APP_ENV,
        debug=settings.app.debug,
    )

    # Initialize logging
    setup_logging(
        log_level=settings.logging.level,
        log_format=settings.logging.format,
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

    # Initialize auth provider
    try:
        # Pass Redis client to auth provider for introspection caching
        cache_client = None
        if settings.auth_mode_enum == AuthMode.INTROSPECTION:
            try:
                cache_client = await get_cache_client()
            except Exception:
                logger.warning(
                    "Redis not available for auth introspection caching - "
                    "continuing without cache"
                )

        await initialize_auth_provider(cache_client=cache_client)
        logger.info("Auth provider initialized", mode=settings.auth.mode)
    except Exception:
        logger.exception("Failed to initialize auth provider")
        raise  # Auth is critical - don't continue without it

    logger.info("Application startup complete")

    yield

    # === SHUTDOWN ===
    logger.info("Shutting down application")

    # Shutdown auth provider (close HTTP connections, etc.)
    await shutdown_auth_provider()

    # Shutdown tracing (flush pending spans)
    shutdown_tracing()

    # Close ARQ connection pool
    await close_arq_pool()

    # Close Redis connection pools
    await close_redis_pools()

    logger.info("Application shutdown complete")
