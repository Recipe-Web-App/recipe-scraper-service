"""Request ID middleware for request tracing.

This middleware:
- Generates or propagates request IDs for each request
- Attaches request ID to request state for use in handlers
- Adds request ID to response headers
- Binds request ID to logging context for correlation
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.observability.logging import bind_context, clear_context

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID to all requests.

    Propagates existing X-Request-ID header or generates a new one.
    The request ID is stored in request.state and added to response headers.
    """

    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process request and add request ID."""
        # Clear logging context at start of request
        clear_context()

        # Get existing request ID or generate new one
        request_id = request.headers.get(self.header_name, str(uuid.uuid4()))

        # Store in request state for access in handlers
        request.state.request_id = request_id

        # Bind to logging context for correlation
        bind_context(request_id=request_id)

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers[self.header_name] = request_id

        return response
