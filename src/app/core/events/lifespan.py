"""Application lifespan event handlers.

This module defines the lifespan context manager that handles:
- Application startup: Initialize connections, warm caches, etc.
- Application shutdown: Close connections, flush buffers, etc.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from app.core.config import get_settings
from app.observability.logging import get_logger, setup_logging


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

    # TODO(Phase 4): Initialize Redis connection pools
    # TODO(Phase 5): Initialize ARQ background job worker

    logger.info("Application startup complete")

    yield

    # === SHUTDOWN ===
    logger.info("Shutting down application")

    # TODO(Phase 4): Close Redis connection pools
    # TODO(Phase 5): Close ARQ background job worker

    logger.info("Application shutdown complete")
