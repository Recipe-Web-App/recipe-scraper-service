"""Request logging middleware.

This middleware:
- Logs incoming requests with method, path, and client info
- Logs outgoing responses with status codes
- Binds request context for structured logging
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.observability.logging import bind_context, get_logger

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request/response logging."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        log_request_body: bool = False,
        exclude_paths: set[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.log_request_body = log_request_body
        self.exclude_paths = exclude_paths or {"/health", "/metrics", "/favicon.ico"}

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Log request and response."""
        # Skip logging for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Bind request context
        bind_context(
            method=request.method,
            path=request.url.path,
            client_ip=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent", "unknown"),
        )

        # Log incoming request
        logger.info(
            "Request started",
            query_params=str(request.query_params) if request.query_params else None,
        )

        # Process request
        response = await call_next(request)

        # Log response
        logger.info(
            "Request completed",
            status_code=response.status_code,
        )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, considering proxies."""
        # Check X-Forwarded-For header (set by reverse proxies)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain (original client)
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct client
        if request.client:
            return request.client.host

        return "unknown"
