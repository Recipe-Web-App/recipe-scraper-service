"""Request ID middleware.

Provides middleware to assign unique request IDs to each incoming HTTP request for
traceability.
"""

import uuid
from collections.abc import Awaitable, Callable

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_CONTEXT_KEY = "request_id"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to assign a unique request ID to each HTTP request.

    This middleware checks for an existing request ID in the incoming request headers.
    If not present, it generates a new UUID. The request ID is stored in
    `request.state.request_id` for use throughout the request lifecycle and is also
    added to the response headers for traceability.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the RequestIDMiddleware.

        Args:
            app (ASGIApp): The ASGI application instance.
        """
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Assign or propagate a request ID for the incoming HTTP request.

        Checks for an existing request ID in the request headers. If not found,
        generates a new UUID. Stores the request ID in `request.state.request_id`
        and adds it to the response headers.

        Args:
            request (Request): The incoming HTTP request.
            call_next (Callable): The next middleware or route handler.

        Returns:
            Response: The HTTP response with the request ID header included.
        """
        request_id = request.headers.get(REQUEST_ID_HEADER, str(uuid.uuid4()))
        request.state.request_id = request_id

        # Inject request_id into Loguru's context for this request
        with logger.contextualize(request_id=request_id):
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
