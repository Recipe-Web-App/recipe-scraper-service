"""Application entry point.

This module initializes and starts the FastAPI application, configures middleware,
routers, and other startup procedures.
"""

import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.routes import api_router
from app.core.config.config import get_settings
from app.core.logging import get_logger
from app.exceptions.handlers import unhandled_exception_handler
from app.middleware.request_id_middleware import RequestIDMiddleware

_log = get_logger(__name__)
settings = get_settings()

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Add security headers to response.

        Args:     request: The incoming request     call_next: The next
        middleware/handler in chain

        Returns:     Response with security headers added
        """
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'"
        )

        return response


class ProcessTimeMiddleware(BaseHTTPMiddleware):
    """Add process time header to responses."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Add process time to response headers.

        Args:     request: The incoming request     call_next: The next
        middleware/handler in chain

        Returns:     Response with process time header
        """
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management.

    Args:     app: FastAPI application instance

    Yields:     None during application lifecycle
    """
    _log.info("Starting Recipe Scraper Service")

    yield

    # Shutdown
    _log.info("Shutting down Recipe Scraper Service")


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
app.add_exception_handler(Exception, unhandled_exception_handler)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
