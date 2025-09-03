"""Application entry point.

This module initializes and starts the FastAPI application, configures middleware,
routers, and other startup procedures.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.v1.routes import api_router
from app.core.config.config import get_settings
from app.core.logging import get_logger
from app.exceptions.custom_exceptions import (
    AuthenticationError,
    DatabaseUnavailableError,
)
from app.exceptions.handlers import (
    authentication_exception_handler,
    database_unavailable_exception_handler,
    unhandled_exception_handler,
)
from app.middleware.process_time_middleware import ProcessTimeMiddleware
from app.middleware.request_id_middleware import RequestIDMiddleware
from app.middleware.security_headers_middleware import SecurityHeadersMiddleware
from app.services.database_monitor import (
    start_database_monitoring,
    stop_database_monitoring,
)

_log = get_logger(__name__)
settings = get_settings()

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)


async def rate_limit_handler(request: Request, exc: Exception) -> Response:
    """Wrapper for slowapi rate limit handler with correct signature."""
    if isinstance(exc, RateLimitExceeded):
        # The slowapi handler returns Response, we need to return it properly
        response: Response = _rate_limit_exceeded_handler(request, exc)
        return response
    # Fallback for unexpected exception types
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests"},
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan management.

    Args:     app: FastAPI application instance

    Yields:     None during application lifecycle
    """
    _log.info("Starting Recipe Scraper Service")

    # Start background database monitoring
    try:
        await start_database_monitoring()
        _log.info("Database monitoring started successfully")
    except Exception as e:
        _log.warning(
            "Failed to start database monitoring: {} ({})", str(e), type(e).__name__
        )

    yield

    # Shutdown
    _log.info("Shutting down Recipe Scraper Service")

    # Stop background database monitoring
    try:
        await stop_database_monitoring()
        _log.info("Database monitoring stopped successfully")
    except Exception as e:
        _log.warning(
            "Error stopping database monitoring: {} ({})", str(e), type(e).__name__
        )


app = FastAPI(
    title="Recipe Scraper Service",
    version="2.0.0",
    description=(
        "A modern, secure API for scraping and managing recipe data "
        "with comprehensive monitoring."
    ),
    summary="High-performance recipe scraping microservice",
    contact={
        "name": "Recipe Scraper Team",
        "url": "https://github.com/jsamuelsen/recipe-scraper-service",
        "email": "jsamuelsen11@gmail.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_version="3.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Prometheus instrumentation (must be done before middleware setup)
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

# Exception handlers
app.add_exception_handler(
    DatabaseUnavailableError, database_unavailable_exception_handler
)
app.add_exception_handler(AuthenticationError, authentication_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Middleware stack (order matters!)
app.add_middleware(ProcessTimeMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestIDMiddleware)

# Rate limiting
app.state.limiter = limiter

# Routes
app.include_router(api_router, prefix="/api")


@app.get("/", tags=["Root"], summary="Root endpoint")
async def root() -> JSONResponse:
    """Root endpoint providing basic service information.

    Returns:     JSONResponse with service information
    """
    return JSONResponse(
        content={
            "service": "Recipe Scraper Service",
            "version": "2.0.0",
            "status": "operational",
            "docs": "/docs",
            "health": "/api/v1/health",
        }
    )
