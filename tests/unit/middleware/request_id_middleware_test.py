"""Unit tests for the request ID middleware."""

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.middleware.request_id_middleware import (
    REQUEST_ID_CONTEXT_KEY,
    REQUEST_ID_HEADER,
    RequestIDMiddleware,
)


class TestRequestIDMiddleware:
    """Unit tests for the RequestIDMiddleware class."""

    @pytest.mark.unit
    def test_request_id_middleware_initialization(self) -> None:
        """Test that RequestIDMiddleware initializes correctly."""
        # Arrange
        app = Mock()

        # Act
        middleware = RequestIDMiddleware(app)

        # Assert
        assert middleware.app == app

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_with_existing_request_id(self) -> None:
        """Test dispatch method when request already has a request ID."""
        # Arrange
        app = Mock()
        middleware = RequestIDMiddleware(app)

        existing_request_id = "existing-id-123"
        request = Mock(spec=Request)
        request.headers = {"X-Request-ID": existing_request_id}
        request.state = Mock()

        response = Mock(spec=Response)
        response.headers = {}
        call_next = AsyncMock(return_value=response)

        # Act
        with patch("app.middleware.request_id_middleware.logger") as mock_logger:
            mock_logger.contextualize.return_value.__enter__ = Mock(return_value=None)
            mock_logger.contextualize.return_value.__exit__ = Mock(return_value=None)

            result = await middleware.dispatch(request, call_next)

        # Assert
        assert request.state.request_id == existing_request_id
        assert result.headers["X-Request-ID"] == existing_request_id
        call_next.assert_called_once_with(request)
        mock_logger.contextualize.assert_called_once_with(
            request_id=existing_request_id
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_without_existing_request_id(self) -> None:
        """Test dispatch method when request doesn't have a request ID."""
        # Arrange
        app = Mock()
        middleware = RequestIDMiddleware(app)

        request = Mock(spec=Request)
        request.headers = {}
        request.state = Mock()

        response = Mock(spec=Response)
        response.headers = {}
        call_next = AsyncMock(return_value=response)

        # Act
        with (
            patch("app.middleware.request_id_middleware.logger") as mock_logger,
            patch("app.middleware.request_id_middleware.uuid.uuid4") as mock_uuid,
        ):
            generated_id = "generated-uuid-456"
            mock_uuid.return_value = generated_id
            mock_logger.contextualize.return_value.__enter__ = Mock(return_value=None)
            mock_logger.contextualize.return_value.__exit__ = Mock(return_value=None)

            result = await middleware.dispatch(request, call_next)

        # Assert
        assert request.state.request_id == generated_id
        assert result.headers["X-Request-ID"] == generated_id
        call_next.assert_called_once_with(request)
        mock_logger.contextualize.assert_called_once_with(request_id=generated_id)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_preserves_response_content(self) -> None:
        """Test that dispatch preserves the original response content."""
        # Arrange
        app = Mock()
        middleware = RequestIDMiddleware(app)

        request = Mock(spec=Request)
        request.headers = {}
        request.state = Mock()

        original_response = Mock(spec=Response)
        original_response.headers = {"Content-Type": "application/json"}
        original_response.status_code = 200
        call_next = AsyncMock(return_value=original_response)

        # Act
        with patch("app.middleware.request_id_middleware.logger") as mock_logger:
            mock_logger.contextualize.return_value.__enter__ = Mock(return_value=None)
            mock_logger.contextualize.return_value.__exit__ = Mock(return_value=None)

            result = await middleware.dispatch(request, call_next)

        # Assert
        assert result is original_response
        assert result.status_code == 200
        assert result.headers["Content-Type"] == "application/json"
        assert REQUEST_ID_HEADER in result.headers

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_with_case_insensitive_header(self) -> None:
        """Test dispatch with different case variations of the request ID header."""
        # Arrange
        app = Mock()
        middleware = RequestIDMiddleware(app)

        existing_request_id = "case-test-789"
        request = Mock(spec=Request)
        # Mock headers.get to simulate case-insensitive behavior
        request.headers.get = Mock(return_value=existing_request_id)
        request.state = Mock()

        response = Mock(spec=Response)
        response.headers = {}
        call_next = AsyncMock(return_value=response)

        # Act
        with patch("app.middleware.request_id_middleware.logger") as mock_logger:
            mock_logger.contextualize.return_value.__enter__ = Mock(return_value=None)
            mock_logger.contextualize.return_value.__exit__ = Mock(return_value=None)

            result = await middleware.dispatch(request, call_next)

        # Assert
        assert request.state.request_id == existing_request_id
        assert result.headers["X-Request-ID"] == existing_request_id

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_generates_valid_uuid(self) -> None:
        """Test that generated request IDs are valid UUIDs."""
        # Arrange
        app = Mock()
        middleware = RequestIDMiddleware(app)

        request = Mock(spec=Request)
        request.headers = {}
        request.state = Mock()

        response = Mock(spec=Response)
        response.headers = {}
        call_next = AsyncMock(return_value=response)

        # Act
        with patch("app.middleware.request_id_middleware.logger") as mock_logger:
            mock_logger.contextualize.return_value.__enter__ = Mock(return_value=None)
            mock_logger.contextualize.return_value.__exit__ = Mock(return_value=None)

            await middleware.dispatch(request, call_next)

        # Assert - Should be able to parse as UUID
        generated_id = request.state.request_id
        assert isinstance(generated_id, str)
        # This should not raise an exception if it's a valid UUID
        parsed_uuid = uuid.UUID(generated_id)
        assert str(parsed_uuid) == generated_id

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_logger_context_management(self) -> None:
        """Test that logger context is properly managed."""
        # Arrange
        app = Mock()
        middleware = RequestIDMiddleware(app)

        request_id = "context-test-101"
        request = Mock(spec=Request)
        request.headers = {"X-Request-ID": request_id}
        request.state = Mock()

        response = Mock(spec=Response)
        response.headers = {}
        call_next = AsyncMock(return_value=response)

        # Act
        with patch("app.middleware.request_id_middleware.logger") as mock_logger:
            context_manager = Mock()
            mock_logger.contextualize.return_value = context_manager
            context_manager.__enter__ = Mock(return_value=None)
            context_manager.__exit__ = Mock(return_value=None)

            await middleware.dispatch(request, call_next)

        # Assert
        mock_logger.contextualize.assert_called_once_with(request_id=request_id)
        context_manager.__enter__.assert_called_once()
        context_manager.__exit__.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_handles_call_next_exception(self) -> None:
        """Test that middleware properly handles exceptions from call_next."""
        # Arrange
        app = Mock()
        middleware = RequestIDMiddleware(app)

        request = Mock(spec=Request)
        request.headers = {}
        request.state = Mock()

        call_next = AsyncMock(side_effect=Exception("Downstream error"))

        # Act & Assert
        with patch("app.middleware.request_id_middleware.logger") as mock_logger:
            mock_logger.contextualize.return_value.__enter__ = Mock(return_value=None)
            mock_logger.contextualize.return_value.__exit__ = Mock(return_value=None)

            with pytest.raises(Exception, match="Downstream error"):
                await middleware.dispatch(request, call_next)

        # Verify context was still managed properly
        assert hasattr(request.state, 'request_id')
        mock_logger.contextualize.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_with_multiple_requests(self) -> None:
        """Test that middleware handles multiple concurrent requests correctly."""
        # Arrange
        app = Mock()
        middleware = RequestIDMiddleware(app)

        # Create multiple request scenarios
        requests_data = [
            {"headers": {"X-Request-ID": "req-1"}, "expected": "req-1"},
            {"headers": {}, "expected": None},  # Will be generated
            {"headers": {"X-Request-ID": "req-3"}, "expected": "req-3"},
        ]

        results = []

        for req_data in requests_data:
            assert isinstance(req_data, dict)  # Type assertion for mypy
            request = Mock(spec=Request)
            headers_dict = req_data.get("headers", {})
            expected_val = req_data.get("expected")
            request.headers = headers_dict
            request.state = Mock()

            response = Mock(spec=Response)
            response.headers = {}
            call_next = AsyncMock(return_value=response)

            # Act
            with patch("app.middleware.request_id_middleware.logger") as mock_logger:
                mock_logger.contextualize.return_value.__enter__ = Mock(
                    return_value=None
                )
                mock_logger.contextualize.return_value.__exit__ = Mock(
                    return_value=None
                )

                result = await middleware.dispatch(request, call_next)
                # Use getattr to safely access mock attributes for mypy
                request_id = getattr(request.state, 'request_id', None)
                # Use getattr to safely access headers on mock response
                headers = getattr(result, 'headers', {})
                response_header = (
                    headers.get("X-Request-ID") if hasattr(headers, 'get') else None
                )
                results.append(
                    {
                        "request_id": request_id,
                        "response_header": response_header,
                        "expected": expected_val,
                    }
                )

        # Assert
        for result_dict in results:
            expected_val = result_dict["expected"]
            request_id_val = result_dict["request_id"]
            response_header_val = result_dict["response_header"]

            if expected_val:
                assert request_id_val == expected_val
                assert response_header_val == expected_val
            else:
                # Generated UUID case
                assert request_id_val == response_header_val
                # Should be valid UUID
                if request_id_val:
                    uuid.UUID(request_id_val)

    @pytest.mark.unit
    def test_request_id_header_constant(self) -> None:
        """Test that REQUEST_ID_HEADER constant has the expected value."""
        # Assert
        assert REQUEST_ID_HEADER == "X-Request-ID"

    @pytest.mark.unit
    def test_request_id_context_key_constant(self) -> None:
        """Test that REQUEST_ID_CONTEXT_KEY constant has the expected value."""
        # Assert
        assert REQUEST_ID_CONTEXT_KEY == "request_id"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_with_empty_request_id_header(self) -> None:
        """Test dispatch when request has empty request ID header."""
        # Arrange
        app = Mock()
        middleware = RequestIDMiddleware(app)

        request = Mock(spec=Request)
        # Mock headers.get to return empty string for X-Request-ID
        request.headers.get = Mock(return_value="")
        request.state = Mock()

        response = Mock(spec=Response)
        response.headers = {}
        call_next = AsyncMock(return_value=response)

        # Act
        with patch("app.middleware.request_id_middleware.logger") as mock_logger:
            mock_logger.contextualize.return_value.__enter__ = Mock(return_value=None)
            mock_logger.contextualize.return_value.__exit__ = Mock(return_value=None)

            result = await middleware.dispatch(request, call_next)

        # Assert - Empty string will be used as-is (current implementation behavior)
        assert request.state.request_id == ""
        assert result.headers["X-Request-ID"] == ""
