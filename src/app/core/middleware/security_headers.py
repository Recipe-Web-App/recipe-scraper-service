"""Security headers middleware.

This middleware adds security headers to all responses following
OWASP security best practices.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        content_security_policy: str | None = None,
        permissions_policy: str | None = None,
    ) -> None:
        super().__init__(app)
        self.content_security_policy = content_security_policy or self._default_csp()
        self.permissions_policy = permissions_policy or self._default_permissions()

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # XSS protection (legacy, but still useful for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Enforce HTTPS
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = self.content_security_policy

        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = self.permissions_policy

        # Prevent caching of sensitive responses
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, private"
            )
            response.headers["Pragma"] = "no-cache"

        return response

    def _default_csp(self) -> str:
        """Return default Content Security Policy."""
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "  # Allow inline scripts for Swagger UI
            "style-src 'self' 'unsafe-inline'; "  # Allow inline styles for Swagger UI
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

    def _default_permissions(self) -> str:
        """Return default Permissions Policy."""
        return (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )
