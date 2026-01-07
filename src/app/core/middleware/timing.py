"""Request timing middleware.

This middleware:
- Measures request processing time
- Adds timing information to response headers
- Logs slow requests for performance monitoring
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.observability.logging import get_logger

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

logger = get_logger(__name__)

# Threshold for slow request warning (in seconds)
SLOW_REQUEST_THRESHOLD = 1.0


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to measure and log request processing time."""

    def __init__(
        self,
        app: ASGIApp,
        header_name: str = "X-Process-Time",
        slow_threshold: float = SLOW_REQUEST_THRESHOLD,
    ) -> None:
        super().__init__(app)
        self.header_name = header_name
        self.slow_threshold = slow_threshold

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process request and measure time."""
        start_time = time.perf_counter()

        response = await call_next(request)

        process_time = time.perf_counter() - start_time
        process_time_ms = round(process_time * 1000, 2)

        # Add timing to response headers
        response.headers[self.header_name] = f"{process_time_ms}ms"

        # Log slow requests
        if process_time > self.slow_threshold:
            logger.warning(
                "Slow request detected",
                method=request.method,
                path=request.url.path,
                process_time_ms=process_time_ms,
                threshold_ms=self.slow_threshold * 1000,
            )

        return response
