"""Application factory for creating FastAPI instances.

This module provides the create_app factory function that:
- Configures the FastAPI application with appropriate settings
- Sets up middleware stack in the correct order
- Registers exception handlers
- Mounts API routers
- Configures OpenAPI documentation
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import Settings, get_settings
from app.core.events import lifespan
from app.core.exceptions import setup_exception_handlers
from app.core.middleware.logging import LoggingMiddleware
from app.core.middleware.request_id import RequestIDMiddleware
from app.core.middleware.security_headers import SecurityHeadersMiddleware
from app.core.middleware.timing import TimingMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure a FastAPI application instance.

    Args:
        settings: Optional settings override. If not provided, uses get_settings().

    Returns:
        Configured FastAPI application instance.
    """
    if settings is None:
        settings = get_settings()

    # Create FastAPI app with configuration
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Recipe Scraper Service - Enterprise-grade API for recipe management",
        lifespan=lifespan,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        # Disable default exception handlers - we use custom ones
        debug=settings.DEBUG,
    )

    # Store settings in app state for access in routes
    app.state.settings = settings

    # Setup exception handlers
    setup_exception_handlers(app)

    # Setup middleware (order matters - first added = last executed)
    _setup_middleware(app, settings)

    # Mount API routers
    _setup_routers(app, settings)

    return app


def _setup_middleware(app: FastAPI, settings: Settings) -> None:
    """Configure middleware stack.

    Middleware is executed in reverse order of addition:
    - Last added middleware runs first on request
    - First added middleware runs first on response

    Order from request perspective:
    1. SecurityHeadersMiddleware (adds security headers)
    2. RequestIDMiddleware (adds request ID for tracing)
    3. TimingMiddleware (measures request time)
    4. LoggingMiddleware (logs requests/responses)
    5. GZipMiddleware (compresses responses)
    6. CORSMiddleware (handles CORS)
    """
    # CORS - must be added first (runs last on request, first on response)
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID", "X-Process-Time"],
        )

    # GZip compression for responses
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Request/response logging
    app.add_middleware(
        LoggingMiddleware,
        exclude_paths={"/health", "/ready", "/metrics", "/favicon.ico"},
    )

    # Request timing
    app.add_middleware(TimingMiddleware)

    # Request ID for tracing
    app.add_middleware(RequestIDMiddleware)

    # Security headers (runs first on request)
    app.add_middleware(SecurityHeadersMiddleware)


def _setup_routers(app: FastAPI, settings: Settings) -> None:
    """Mount API routers.

    Args:
        app: FastAPI application instance.
        settings: Application settings.
    """
    # Mount v1 API router
    app.include_router(v1_router, prefix=settings.API_V1_PREFIX)

    # Root health check (no prefix, for load balancers)
    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        """Root endpoint returning basic service info."""
        return {
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs" if settings.is_development else "disabled",
        }
