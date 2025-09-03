"""Exception handlers.

Contains FastAPI exception handler functions to map exceptions to HTTP responses.
"""

from fastapi import Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse, Response

from app.api.v1.schemas.response.auth_error_response import (
    AuthenticationRequiredResponse,
    ExpiredTokenResponse,
    InsufficientPermissionsResponse,
    IntrospectionFailedResponse,
    InvalidTokenResponse,
)
from app.core.logging import get_logger
from app.exceptions.custom_exceptions import (
    AuthenticationRequiredError,
    DatabaseUnavailableError,
    ExpiredTokenError,
    InsufficientPermissionsError,
    InvalidTokenError,
    OAuth2IntrospectionError,
)

_log = get_logger(__name__)


async def database_unavailable_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse | Response:
    """Handle database unavailable exceptions.

    This handler returns a 503 Service Unavailable response for all routes
    except health endpoints, which handle database unavailability gracefully.

    Args:
        request: The incoming request that caused the exception.
        exc: The database unavailable exception.

    Returns:
        JSONResponse with 503 status and error details.
    """
    # Cast to the expected type for proper error handling
    db_error = exc if isinstance(exc, DatabaseUnavailableError) else None

    # Log the database unavailability with context
    _log.warning(
        "Database unavailable for request to {}: {}",
        request.url.path,
        str(exc),
        exc_info=db_error.get_original_error() if db_error else None,
    )

    return JSONResponse(
        status_code=503,
        content={
            "detail": (
                "Service temporarily unavailable due to " "database connectivity issues"
            ),
            "type": "database_unavailable",
            "retry_after": 60,  # Suggest retry after 60 seconds
        },
    )


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


async def authentication_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle authentication-related exceptions.

    Args:
        request: The incoming request that caused the exception.
        exc: The authentication exception.

    Returns:
        JSONResponse with appropriate status and schema-based error details.
    """
    _log.warning(
        "Authentication error for request to {}: {}",
        request.url.path,
        str(exc),
    )

    # Determine response based on exception type
    if isinstance(exc, AuthenticationRequiredError):
        response_content = AuthenticationRequiredResponse().model_dump()
        status_code = 401
    elif isinstance(exc, InvalidTokenError):
        response_content = InvalidTokenResponse(detail=str(exc)).model_dump()
        status_code = 401
    elif isinstance(exc, ExpiredTokenError):
        response_content = ExpiredTokenResponse().model_dump()
        status_code = 401
    elif isinstance(exc, InsufficientPermissionsError):
        response_content = InsufficientPermissionsResponse(detail=str(exc)).model_dump()
        status_code = 403
    elif isinstance(exc, OAuth2IntrospectionError):
        response_content = IntrospectionFailedResponse(detail=str(exc)).model_dump()
        status_code = 401
    else:
        # Fallback for any other AuthenticationError
        response_content = InvalidTokenResponse(detail=str(exc)).model_dump()
        status_code = 401

    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None

    return JSONResponse(
        status_code=status_code,
        content=response_content,
        headers=headers,
    )
