"""Unit tests for exception handlers."""

from unittest.mock import Mock, patch

import pytest
from fastapi import Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

from app.exceptions.handlers import unhandled_exception_handler


class TestUnhandledExceptionHandler:
    """Unit tests for the unhandled exception handler."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unhandled_exception_handler_with_http_exception(self) -> None:
        """Test that HTTPExceptions are re-raised without modification."""
        # Arrange
        request = Mock(spec=Request)
        http_exception = HTTPException(status_code=404, detail="Not found")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await unhandled_exception_handler(request, http_exception)

        assert exc_info.value == http_exception
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Not found"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unhandled_exception_handler_with_generic_exception(self) -> None:
        """Test that generic exceptions return a 500 error response."""
        # Arrange
        request = Mock(spec=Request)
        generic_exception = ValueError("Something went wrong")

        # Act
        with patch("app.exceptions.handlers._log") as mock_logger:
            response = await unhandled_exception_handler(request, generic_exception)

        # Assert
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

        # Check response content
        response_body = response.body
        response_content = (
            response_body.decode()
            if isinstance(response_body, bytes)
            else bytes(response_body).decode()
        )
        assert "An unexpected error occurred." in response_content

        # Verify logging
        mock_logger.exception.assert_called_once_with(
            "Unhandled exception occurred", exc_info=generic_exception
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unhandled_exception_handler_logs_exception_details(self) -> None:
        """Test that exception details are properly logged."""
        # Arrange
        request = Mock(spec=Request)
        exception = RuntimeError("Database connection failed")

        # Act
        with patch("app.exceptions.handlers._log") as mock_logger:
            await unhandled_exception_handler(request, exception)

        # Assert
        mock_logger.exception.assert_called_once_with(
            "Unhandled exception occurred", exc_info=exception
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unhandled_exception_handler_response_format(self) -> None:
        """Test that the error response has the correct format."""
        # Arrange
        request = Mock(spec=Request)
        exception = Exception("Test exception")

        # Act
        with patch("app.exceptions.handlers._log"):
            response = await unhandled_exception_handler(request, exception)

        # Assert
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        assert response.media_type == "application/json"

        # Check that response body contains expected structure
        response_body = response.body
        response_content = (
            response_body.decode()
            if isinstance(response_body, bytes)
            else bytes(response_body).decode()
        )
        # The actual response content: {"detail":"An unexpected error occurred."}
        assert '"detail":"An unexpected error occurred."' in response_content

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unhandled_exception_handler_with_various_exception_types(
        self,
    ) -> None:
        """Test handler with different types of exceptions."""
        # Arrange
        request = Mock(spec=Request)
        exceptions_to_test = [
            ValueError("Invalid value"),
            TypeError("Type error"),
            KeyError("Key not found"),
            AttributeError("Attribute error"),
            RuntimeError("Runtime error"),
        ]

        # Act & Assert
        for exception in exceptions_to_test:
            with patch("app.exceptions.handlers._log") as mock_logger:
                response = await unhandled_exception_handler(request, exception)

                # All should return 500 status
                assert response.status_code == 500
                assert isinstance(response, JSONResponse)

                # All should be logged
                mock_logger.exception.assert_called_once_with(
                    "Unhandled exception occurred", exc_info=exception
                )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unhandled_exception_handler_doesnt_modify_http_exceptions(
        self,
    ) -> None:
        """Test that various HTTP exceptions are passed through unchanged."""
        # Arrange
        request = Mock(spec=Request)
        http_exceptions = [
            HTTPException(status_code=400, detail="Bad request"),
            HTTPException(status_code=401, detail="Unauthorized"),
            HTTPException(status_code=403, detail="Forbidden"),
            HTTPException(status_code=404, detail="Not found"),
            HTTPException(status_code=422, detail="Validation error"),
        ]

        # Act & Assert
        for http_exc in http_exceptions:
            with pytest.raises(HTTPException) as exc_info:
                await unhandled_exception_handler(request, http_exc)

            # Should be the exact same exception
            assert exc_info.value is http_exc
            assert exc_info.value.status_code == http_exc.status_code
            assert exc_info.value.detail == http_exc.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unhandled_exception_handler_with_none_exception(self) -> None:
        """Test handler behavior with None as exception (edge case)."""
        # Arrange
        request = Mock(spec=Request)

        # Act
        with patch("app.exceptions.handlers._log") as mock_logger:
            response = await unhandled_exception_handler(request, None)  # type: ignore[arg-type]

        # Assert
        assert response.status_code == 500
        assert isinstance(response, JSONResponse)
        mock_logger.exception.assert_called_once_with(
            "Unhandled exception occurred", exc_info=None
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unhandled_exception_handler_preserves_request_object(self) -> None:
        """Test that the request object is properly handled but not modified."""
        # Arrange
        request = Mock(spec=Request)
        request.url = "http://localhost:8000/test"
        request.method = "GET"
        exception = Exception("Test exception")

        # Act
        with patch("app.exceptions.handlers._log"):
            response = await unhandled_exception_handler(request, exception)

        # Assert
        assert response.status_code == 500
        # Request object should remain unchanged
        assert request.url == "http://localhost:8000/test"
        assert request.method == "GET"
        assert request.method == "GET"
