"""Application lifespan event handlers.

This module defines the lifespan context manager that handles:
- Application startup: Initialize connections, warm caches, etc.
- Application shutdown: Close connections, flush buffers, etc.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from app.core.config import get_settings
from app.observability.logging import get_logger, setup_logging

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events.

    This context manager handles startup and shutdown events for the application.
    Resources initialized here are available throughout the application's lifetime.

    Args:
        app: The FastAPI application instance.

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

    # Initialize Redis connections (will be implemented in Phase 4)
    # await init_redis_pools(settings)

    # Initialize background job worker connection (will be implemented in Phase 5)
    # await init_arq_pool(settings)

    logger.info("Application startup complete")

    yield

    # === SHUTDOWN ===
    logger.info("Shutting down application")

    # Close Redis connections (will be implemented in Phase 4)
    # await close_redis_pools()

    # Close background job worker connection (will be implemented in Phase 5)
    # await close_arq_pool()

    logger.info("Application shutdown complete")
