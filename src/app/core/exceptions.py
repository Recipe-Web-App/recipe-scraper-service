"""Custom exceptions and exception handlers.

This module provides structured exception handling with:
- Custom exception classes for common error scenarios
- FastAPI exception handlers for consistent error responses
- Structured error response models
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

if TYPE_CHECKING:
    from fastapi import Request


class ErrorDetail(BaseModel):
    """Structured error detail for validation errors."""

    code: str
    message: str
    field: str | None = None


class ErrorResponse(BaseModel):
    """Structured error response."""

    error: str
    message: str
    details: list[ErrorDetail] | None = None
    request_id: str | None = None


class AppException(Exception):
    """Base application exception.

    All custom exceptions should inherit from this class
    for consistent error handling.
    """

    def __init__(
        self,
        status_code: int,
        error: str,
        message: str,
        details: list[ErrorDetail] | None = None,
    ) -> None:
        self.status_code = status_code
        self.error = error
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundException(AppException):
    """Resource not found exception."""

    def __init__(self, resource: str, identifier: Any) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error="NOT_FOUND",
            message=f"{resource} with identifier '{identifier}' not found",
        )


class UnauthorizedException(AppException):
    """Unauthorized access exception."""

    def __init__(self, message: str = "Could not validate credentials") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="UNAUTHORIZED",
            message=message,
        )


class ForbiddenException(AppException):
    """Forbidden access exception."""

    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error="FORBIDDEN",
            message=message,
        )


class ConflictException(AppException):
    """Resource conflict exception."""

    def __init__(self, message: str) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error="CONFLICT",
            message=message,
        )


class BadRequestException(AppException):
    """Bad request exception."""

    def __init__(self, message: str) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error="BAD_REQUEST",
            message=message,
        )


class RateLimitException(AppException):
    """Rate limit exceeded exception."""

    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error="RATE_LIMIT_EXCEEDED",
            message=message,
        )


class ServiceUnavailableException(AppException):
    """Service unavailable exception."""

    def __init__(self, message: str = "Service temporarily unavailable") -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error="SERVICE_UNAVAILABLE",
            message=message,
        )


def _get_request_id(request: Request) -> str | None:
    """Extract request ID from request state."""
    return getattr(request.state, "request_id", None)


def setup_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers with the FastAPI application."""

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request,
        exc: AppException,
    ) -> ORJSONResponse:
        """Handle custom application exceptions."""
        return ORJSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.error,
                message=exc.message,
                details=exc.details,
                request_id=_get_request_id(request),
            ).model_dump(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> ORJSONResponse:
        """Handle Starlette HTTP exceptions."""
        return ORJSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error="HTTP_ERROR",
                message=str(exc.detail),
                request_id=_get_request_id(request),
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> ORJSONResponse:
        """Handle Pydantic validation errors."""
        details = [
            ErrorDetail(
                code="VALIDATION_ERROR",
                message=error["msg"],
                field=".".join(str(loc) for loc in error["loc"]),
            )
            for error in exc.errors()
        ]
        return ORJSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error="VALIDATION_ERROR",
                message="Request validation failed",
                details=details,
                request_id=_get_request_id(request),
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception,
    ) -> ORJSONResponse:
        """Handle unexpected exceptions."""
        from app.observability.logging import get_logger

        logger = get_logger(__name__)
        logger.exception("Unhandled exception", exc_info=exc)

        return ORJSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="INTERNAL_SERVER_ERROR",
                message="An unexpected error occurred",
                request_id=_get_request_id(request),
            ).model_dump(),
        )
