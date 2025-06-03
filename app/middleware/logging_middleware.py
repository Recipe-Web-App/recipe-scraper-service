"""Logging middleware.

Implements middleware to log incoming requests and responses, helping with debugging and
monitoring. Also intercepts Uvicorn logs to ensure they are handled by the application's
logging system.
"""

import logging
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

uvicorn_logger = get_logger("uvicorn")
request_logger = get_logger("requests")


class InterceptHandler(logging.Handler):
    """Intercept standard logging and route to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to Loguru.

        Args:
            record (logging.LogRecord): The log record to emit.
        """
        try:
            level = uvicorn_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        uvicorn_logger.log(level, record.getMessage())


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log incoming requests and responses.

    Logs the HTTP method and URL for each incoming request and the status code for each
    response.

    Attributes:
        app (ASGIApp): The ASGI application instance.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process the incoming request and log request/response details.

        Args:
            request (Request): The incoming HTTP request.
            call_next (Callable[[Request], Awaitable[Response]]): The next middleware or
              route handler.

        Returns:
            Response: The HTTP response after processing.
        """
        request_logger.info("Request: %s %s", request.method, request.url)
        response: Response = await call_next(request)
        request_logger.info(
            "Response status: %s for %s %s",
            response.status_code,
            request.method,
            request.url,
        )
        return response
