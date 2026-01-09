"""Unit tests for custom exceptions.

Tests cover:
- Exception classes
- Error response models
- Exception properties
"""

from __future__ import annotations

import pytest
from fastapi import status

from app.core.exceptions import (
    AppError,
    BadRequestError,
    ConflictError,
    ErrorDetail,
    ErrorResponse,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    UnauthorizedError,
)


pytestmark = pytest.mark.unit


# =============================================================================
# Error Models Tests
# =============================================================================


class TestErrorDetail:
    """Tests for ErrorDetail model."""

    def test_creates_with_required_fields(self):
        """Should create with required fields."""
        detail = ErrorDetail(code="VALIDATION_ERROR", message="Field is required")

        assert detail.code == "VALIDATION_ERROR"
        assert detail.message == "Field is required"
        assert detail.field is None

    def test_creates_with_all_fields(self):
        """Should create with all fields."""
        detail = ErrorDetail(
            code="VALIDATION_ERROR",
            message="Field is required",
            field="email",
        )

        assert detail.field == "email"


class TestErrorResponse:
    """Tests for ErrorResponse model."""

    def test_creates_with_required_fields(self):
        """Should create with required fields."""
        response = ErrorResponse(error="NOT_FOUND", message="Resource not found")

        assert response.error == "NOT_FOUND"
        assert response.message == "Resource not found"
        assert response.details is None
        assert response.request_id is None

    def test_creates_with_all_fields(self):
        """Should create with all fields."""
        details = [ErrorDetail(code="VALIDATION_ERROR", message="Invalid")]
        response = ErrorResponse(
            error="VALIDATION_ERROR",
            message="Validation failed",
            details=details,
            request_id="req-123",
        )

        assert response.details == details
        assert response.request_id == "req-123"


# =============================================================================
# AppError Tests
# =============================================================================


class TestAppError:
    """Tests for base AppError exception."""

    def test_creates_with_all_properties(self):
        """Should create with all properties."""
        error = AppError(
            status_code=400,
            error="BAD_REQUEST",
            message="Something went wrong",
        )

        assert error.status_code == 400
        assert error.error == "BAD_REQUEST"
        assert error.message == "Something went wrong"
        assert error.details is None

    def test_creates_with_details(self):
        """Should create with error details."""
        details = [ErrorDetail(code="FIELD_ERROR", message="Invalid field")]
        error = AppError(
            status_code=422,
            error="VALIDATION_ERROR",
            message="Validation failed",
            details=details,
        )

        assert error.details == details

    def test_is_exception(self):
        """Should be a valid exception."""
        error = AppError(
            status_code=500,
            error="INTERNAL_ERROR",
            message="Test error",
        )

        assert isinstance(error, Exception)
        assert str(error) == "Test error"


# =============================================================================
# Specific Exception Tests
# =============================================================================


class TestNotFoundError:
    """Tests for NotFoundError exception."""

    def test_has_correct_status_code(self):
        """Should have 404 status code."""
        error = NotFoundError(resource="Recipe", identifier="123")

        assert error.status_code == status.HTTP_404_NOT_FOUND

    def test_has_correct_error_type(self):
        """Should have NOT_FOUND error type."""
        error = NotFoundError(resource="Recipe", identifier="123")

        assert error.error == "NOT_FOUND"

    def test_message_includes_resource_and_identifier(self):
        """Should include resource and identifier in message."""
        error = NotFoundError(resource="Recipe", identifier="abc-123")

        assert "Recipe" in error.message
        assert "abc-123" in error.message


class TestUnauthorizedError:
    """Tests for UnauthorizedError exception."""

    def test_has_correct_status_code(self):
        """Should have 401 status code."""
        error = UnauthorizedError()

        assert error.status_code == status.HTTP_401_UNAUTHORIZED

    def test_has_correct_error_type(self):
        """Should have UNAUTHORIZED error type."""
        error = UnauthorizedError()

        assert error.error == "UNAUTHORIZED"

    def test_has_default_message(self):
        """Should have default message."""
        error = UnauthorizedError()

        assert error.message == "Could not validate credentials"

    def test_accepts_custom_message(self):
        """Should accept custom message."""
        error = UnauthorizedError(message="Token expired")

        assert error.message == "Token expired"


class TestForbiddenError:
    """Tests for ForbiddenError exception."""

    def test_has_correct_status_code(self):
        """Should have 403 status code."""
        error = ForbiddenError()

        assert error.status_code == status.HTTP_403_FORBIDDEN

    def test_has_correct_error_type(self):
        """Should have FORBIDDEN error type."""
        error = ForbiddenError()

        assert error.error == "FORBIDDEN"

    def test_has_default_message(self):
        """Should have default message."""
        error = ForbiddenError()

        assert error.message == "Insufficient permissions"


class TestConflictError:
    """Tests for ConflictError exception."""

    def test_has_correct_status_code(self):
        """Should have 409 status code."""
        error = ConflictError(message="Resource already exists")

        assert error.status_code == status.HTTP_409_CONFLICT

    def test_has_correct_error_type(self):
        """Should have CONFLICT error type."""
        error = ConflictError(message="Resource already exists")

        assert error.error == "CONFLICT"


class TestBadRequestError:
    """Tests for BadRequestError exception."""

    def test_has_correct_status_code(self):
        """Should have 400 status code."""
        error = BadRequestError(message="Invalid input")

        assert error.status_code == status.HTTP_400_BAD_REQUEST

    def test_has_correct_error_type(self):
        """Should have BAD_REQUEST error type."""
        error = BadRequestError(message="Invalid input")

        assert error.error == "BAD_REQUEST"


class TestRateLimitError:
    """Tests for RateLimitError exception."""

    def test_has_correct_status_code(self):
        """Should have 429 status code."""
        error = RateLimitError()

        assert error.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_has_correct_error_type(self):
        """Should have RATE_LIMIT_EXCEEDED error type."""
        error = RateLimitError()

        assert error.error == "RATE_LIMIT_EXCEEDED"

    def test_has_default_message(self):
        """Should have default message."""
        error = RateLimitError()

        assert error.message == "Rate limit exceeded"


class TestServiceUnavailableError:
    """Tests for ServiceUnavailableError exception."""

    def test_has_correct_status_code(self):
        """Should have 503 status code."""
        error = ServiceUnavailableError()

        assert error.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    def test_has_correct_error_type(self):
        """Should have SERVICE_UNAVAILABLE error type."""
        error = ServiceUnavailableError()

        assert error.error == "SERVICE_UNAVAILABLE"

    def test_has_default_message(self):
        """Should have default message."""
        error = ServiceUnavailableError()

        assert error.message == "Service temporarily unavailable"

    def test_accepts_custom_message(self):
        """Should accept custom message."""
        error = ServiceUnavailableError(message="Database connection failed")

        assert error.message == "Database connection failed"
