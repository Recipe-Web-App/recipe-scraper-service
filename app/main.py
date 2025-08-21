"""Application entry point.

This module initializes and starts the FastAPI application, configures middleware,
routers, and other startup procedures.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.v1.routes import api_router
from app.core.config.config import get_settings
from app.core.logging import get_logger
from app.exceptions.handlers import unhandled_exception_handler
from app.middleware.process_time_middleware import ProcessTimeMiddleware
from app.middleware.request_id_middleware import RequestIDMiddleware
from app.middleware.security_headers_middleware import SecurityHeadersMiddleware

_log = get_logger(__name__)
settings = get_settings()

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)


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
