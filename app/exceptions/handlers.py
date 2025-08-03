"""Exception handlers.

Contains FastAPI exception handler functions to map exceptions to HTTP responses.
"""

from fastapi import Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse, Response

from app.core.logging import get_logger

_log = get_logger(__name__)


async def unhandled_exception_handler(_request: Request, exc: Exception) -> Response:
    """Handle unhandled exceptions in the FastAPI application.

    Args:     request (Request): The incoming request that caused the exception.     exc
    (Exception): The exception that was raised.

    Raises:     exc: _description_

    Returns:     _type_: _description_
    """
    if isinstance(exc, HTTPException):
        raise exc
    _log.exception("Unhandled exception occurred", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred."},
    )
