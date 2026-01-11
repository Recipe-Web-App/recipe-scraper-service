"""Rate limiting using SlowAPI with Redis backend.

This module provides:
- Rate limiting middleware configuration
- Custom rate limit key functions
- Rate limit exception handlers
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from app.core.config import get_settings
from app.observability.logging import get_logger


if TYPE_CHECKING:
    from fastapi import FastAPI
    from starlette.requests import Request

logger = get_logger(__name__)


def _get_rate_limit_key(request: Request) -> str:
    """Get rate limit key from request.

    Uses authenticated user ID if available, otherwise falls back to IP address.

    Args:
        request: The incoming request.

    Returns:
        A string key for rate limiting.
    """
    # Check for authenticated user
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"

    # Fall back to IP address
    return str(get_remote_address(request))


def _get_auth_rate_limit_key(request: Request) -> str:
    """Get rate limit key for auth endpoints.

    Always uses IP address to prevent brute force attacks.

    Args:
        request: The incoming request.

    Returns:
        IP address as rate limit key.
    """
    return f"auth:{get_remote_address(request)}"


def create_limiter() -> Limiter:
    """Create and configure the rate limiter.

    Returns:
        Configured Limiter instance.
    """
    settings = get_settings()

    return Limiter(
        key_func=_get_rate_limit_key,
        default_limits=[settings.RATE_LIMIT_DEFAULT],
        storage_uri=settings.REDIS_RATE_LIMIT_URL,
        strategy="fixed-window",
        headers_enabled=True,
    )


# Global limiter instance
limiter = create_limiter()


async def rate_limit_exceeded_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle rate limit exceeded exceptions.

    Args:
        request: The incoming request.
        exc: The rate limit exception.

    Returns:
        JSON response with rate limit error details.
    """
    assert isinstance(exc, RateLimitExceeded)
    logger.warning(
        "Rate limit exceeded",
        path=request.url.path,
        method=request.method,
        client_ip=get_remote_address(request),
        limit=str(exc.detail),
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": exc.detail,
        },
        headers={
            "Retry-After": str(exc.detail),
            "X-RateLimit-Limit": request.headers.get("X-RateLimit-Limit", ""),
            "X-RateLimit-Remaining": "0",
        },
    )


def setup_rate_limiting(app: FastAPI) -> None:
    """Configure rate limiting for the FastAPI application.

    Args:
        app: The FastAPI application instance.
    """
    # Store limiter in app state for access in routes
    app.state.limiter = limiter

    # Register exception handler
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    logger.info("Rate limiting configured")


def rate_limit(limit: str) -> Any:
    """Apply a custom rate limit to an endpoint.

    Args:
        limit: Rate limit string (e.g., "10/minute", "100/hour").

    Returns:
        Rate limit decorator (slowapi Limiter.limit return type).

    Example:
        @router.get("/resource")
        @rate_limit("5/minute")
        async def get_resource():
            ...
    """
    return limiter.limit(limit)


def rate_limit_auth() -> Any:
    """Apply auth-specific rate limit (stricter, IP-based).

    Returns:
        Rate limit decorator for auth endpoints (slowapi Limiter.limit return type).

    Example:
        @router.post("/login")
        @rate_limit_auth()
        async def login():
            ...
    """
    settings = get_settings()
    return limiter.limit(settings.RATE_LIMIT_AUTH, key_func=_get_auth_rate_limit_key)
