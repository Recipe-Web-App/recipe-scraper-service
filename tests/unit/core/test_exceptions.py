"""Unit tests for custom exceptions.

Tests cover:
- Exception classes
- Error response models
- Exception properties
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.testclient import TestClient

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
    _get_request_id,
    setup_exception_handlers,
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


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestGetRequestId:
    """Tests for _get_request_id helper function."""

    def test_returns_request_id_when_present(self):
        """Should return request_id from request state."""
        mock_request = MagicMock()
        mock_request.state.request_id = "req-abc-123"

        result = _get_request_id(mock_request)

        assert result == "req-abc-123"

    def test_returns_none_when_missing(self):
        """Should return None when request_id not in state."""
        mock_request = MagicMock(spec=[])
        mock_request.state = MagicMock(spec=[])

        result = _get_request_id(mock_request)

        assert result is None


# =============================================================================
# Exception Handler Tests
# =============================================================================


class TestSetupExceptionHandlers:
    """Tests for exception handlers."""

    @pytest.fixture
    def test_app(self):
        """Create a test FastAPI app with handlers registered."""
        app = FastAPI()
        setup_exception_handlers(app)
        return app

    @pytest.fixture
    def test_client(self, test_app):
        """Create a test client for the app."""
        return TestClient(test_app, raise_server_exceptions=False)

    def test_app_error_handler(self, test_app, test_client):
        """Should handle AppError and return structured response."""

        @test_app.get("/app-error")
        async def trigger_app_error():
            raise BadRequestError(message="Test bad request")

        response = test_client.get("/app-error")

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "BAD_REQUEST"
        assert data["message"] == "Test bad request"

    def test_http_exception_handler(self, test_app, test_client):
        """Should handle HTTP exceptions and return structured response."""

        @test_app.get("/http-error")
        async def trigger_http_error():
            raise HTTPException(status_code=404, detail="Resource not found")

        response = test_client.get("/http-error")

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "Resource not found" in data["message"]

    def test_validation_exception_handler(self, test_app, test_client):
        """Should handle validation errors and return structured response."""

        class RequestBody(BaseModel):
            name: str
            count: int

        @test_app.post("/validate")
        async def validate_endpoint(body: RequestBody):
            return {"ok": True}

        response = test_client.post("/validate", json={"name": 123})

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
        assert data["message"] == "Request validation failed"
        assert data["details"] is not None
        assert len(data["details"]) > 0

    def test_general_exception_handler(self, test_app, test_client):
        """Should handle unexpected exceptions and return 500."""

        @test_app.get("/unexpected-error")
        async def trigger_unexpected_error():
            msg = "Something unexpected happened"
            raise RuntimeError(msg)

        response = test_client.get("/unexpected-error")

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "INTERNAL_SERVER_ERROR"
        assert data["message"] == "An unexpected error occurred"

    def test_handler_includes_request_id(self, test_app, test_client):
        """Should include request_id from request state in response."""

        class AddRequestIdMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                request.state.request_id = "test-req-id-456"
                return await call_next(request)

        test_app.add_middleware(AddRequestIdMiddleware)

        @test_app.get("/with-request-id")
        async def trigger_error_with_id():
            raise BadRequestError(message="Error with ID")

        response = test_client.get("/with-request-id")

        data = response.json()
        assert data["request_id"] == "test-req-id-456"

    def test_app_error_handler_with_details(self, test_app, test_client):
        """Should include error details in response."""

        @test_app.get("/detailed-error")
        async def trigger_detailed_error():
            details = [
                ErrorDetail(code="FIELD_ERROR", message="Invalid value", field="name"),
                ErrorDetail(
                    code="FIELD_ERROR", message="Too long", field="description"
                ),
            ]
            raise AppError(
                status_code=422,
                error="VALIDATION_FAILED",
                message="Multiple validation errors",
                details=details,
            )

        response = test_client.get("/detailed-error")

        assert response.status_code == 422
        data = response.json()
        assert data["details"] is not None
        assert len(data["details"]) == 2
        assert data["details"][0]["field"] == "name"
        assert data["details"][1]["field"] == "description"
