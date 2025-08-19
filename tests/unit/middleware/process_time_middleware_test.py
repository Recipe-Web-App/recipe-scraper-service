"""Unit tests for the ProcessTimeMiddleware class."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import Request, Response

from app.middleware.process_time_middleware import ProcessTimeMiddleware


class TestProcessTimeMiddleware:
    """Unit tests for ProcessTimeMiddleware."""

    @pytest.fixture
    def middleware(self) -> ProcessTimeMiddleware:
        """Create ProcessTimeMiddleware instance for testing."""
        # Mock app is required by BaseHTTPMiddleware
        mock_app = Mock()
        return ProcessTimeMiddleware(mock_app)

    @pytest.fixture
    def mock_request(self) -> Request:
        """Create a mock Request for testing."""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
        }
        return Request(scope)

    @pytest.fixture
    def mock_response(self) -> Response:
        """Create a mock Response for testing."""
        return Response(content="Test response", status_code=200)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_adds_process_time_header(
        self,
        middleware: ProcessTimeMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that dispatch adds X-Process-Time header."""
        # Arrange
        call_next = AsyncMock(return_value=mock_response)

        # Act
        result = await middleware.dispatch(mock_request, call_next)

        # Assert
        assert call_next.called
        call_next.assert_called_once_with(mock_request)
        assert "X-Process-Time" in result.headers

        # Check that process time is a valid number
        process_time_str = result.headers["X-Process-Time"]
        process_time = float(process_time_str)
        assert process_time >= 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_preserves_original_response_content(
        self,
        middleware: ProcessTimeMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that dispatch preserves the original response content."""
        # Arrange
        original_content = "Original test content"
        mock_response.body = original_content.encode()
        call_next = AsyncMock(return_value=mock_response)

        # Act
        result = await middleware.dispatch(mock_request, call_next)

        # Assert
        assert result.body == original_content.encode()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_preserves_original_status_code(
        self,
        middleware: ProcessTimeMiddleware,
        mock_request: Request,
    ) -> None:
        """Test that dispatch preserves the original response status code."""
        # Arrange
        original_status = 201
        mock_response = Response(content="Created", status_code=original_status)
        call_next = AsyncMock(return_value=mock_response)

        # Act
        result = await middleware.dispatch(mock_request, call_next)

        # Assert
        assert result.status_code == original_status

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_preserves_existing_headers(
        self,
        middleware: ProcessTimeMiddleware,
        mock_request: Request,
    ) -> None:
        """Test that dispatch preserves existing headers from response."""
        # Arrange
        existing_headers = {"Content-Type": "application/json", "Custom-Header": "test"}
        mock_response = Response(
            content="Test", status_code=200, headers=existing_headers
        )
        call_next = AsyncMock(return_value=mock_response)

        # Act
        result = await middleware.dispatch(mock_request, call_next)

        # Assert
        # Check existing headers are preserved
        for header_name, header_value in existing_headers.items():
            assert header_name in result.headers
            assert result.headers[header_name] == header_value

        # Check process time header is also added
        assert "X-Process-Time" in result.headers

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_overwrites_existing_process_time_header(
        self,
        middleware: ProcessTimeMiddleware,
        mock_request: Request,
    ) -> None:
        """Test that dispatch overwrites any existing X-Process-Time header."""
        # Arrange
        existing_headers = {"X-Process-Time": "999.999"}
        mock_response = Response(
            content="Test", status_code=200, headers=existing_headers
        )
        call_next = AsyncMock(return_value=mock_response)

        # Act
        result = await middleware.dispatch(mock_request, call_next)

        # Assert
        # Check that process time header is overwritten with new value
        process_time_str = result.headers["X-Process-Time"]
        process_time = float(process_time_str)
        assert process_time != 999.999
        assert process_time >= 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.middleware.process_time_middleware.time")
    async def test_process_time_calculation_accuracy(
        self,
        mock_time: Mock,
        middleware: ProcessTimeMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that process time is calculated accurately."""
        # Arrange
        start_time = 1000.0
        end_time = 1000.5
        expected_process_time = 0.5

        mock_time.time.side_effect = [start_time, end_time]
        call_next = AsyncMock(return_value=mock_response)

        # Act
        result = await middleware.dispatch(mock_request, call_next)

        # Assert
        process_time_str = result.headers["X-Process-Time"]
        actual_process_time = float(process_time_str)
        assert abs(actual_process_time - expected_process_time) < 1e-10

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_handles_different_request_methods(
        self,
        middleware: ProcessTimeMiddleware,
        mock_response: Response,
    ) -> None:
        """Test that dispatch works with different HTTP methods."""
        # Arrange
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        call_next = AsyncMock(return_value=mock_response)

        for method in methods:
            # Create request with specific method
            scope = {
                "type": "http",
                "method": method,
                "path": "/",
                "headers": [],
                "query_string": b"",
            }
            request = Request(scope)

            # Act
            result = await middleware.dispatch(request, call_next)

            # Assert
            assert "X-Process-Time" in result.headers
            process_time = float(result.headers["X-Process-Time"])
            assert process_time >= 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_handles_different_paths(
        self,
        middleware: ProcessTimeMiddleware,
        mock_response: Response,
    ) -> None:
        """Test that dispatch works with different request paths."""
        # Arrange
        paths = ["/", "/api/v1/recipes", "/docs", "/health"]
        call_next = AsyncMock(return_value=mock_response)

        for path in paths:
            # Create request with specific path
            scope = {
                "type": "http",
                "method": "GET",
                "path": path,
                "headers": [],
                "query_string": b"",
            }
            request = Request(scope)

            # Act
            result = await middleware.dispatch(request, call_next)

            # Assert
            assert "X-Process-Time" in result.headers

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_with_error_response(
        self,
        middleware: ProcessTimeMiddleware,
        mock_request: Request,
    ) -> None:
        """Test that dispatch adds process time header even for error responses."""
        # Arrange
        error_response = Response(content="Not Found", status_code=404)
        call_next = AsyncMock(return_value=error_response)

        # Act
        result = await middleware.dispatch(mock_request, call_next)

        # Assert
        assert result.status_code == 404
        assert "X-Process-Time" in result.headers

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_middleware_call_next_exception_propagation(
        self,
        middleware: ProcessTimeMiddleware,
        mock_request: Request,
    ) -> None:
        """Test that middleware propagates exceptions from call_next."""
        # Arrange
        test_exception = ValueError("Test exception")
        call_next = AsyncMock(side_effect=test_exception)

        # Act & Assert
        with pytest.raises(ValueError, match="Test exception"):
            await middleware.dispatch(mock_request, call_next)

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.middleware.process_time_middleware.time")
    async def test_process_time_with_slow_request(
        self,
        mock_time: Mock,
        middleware: ProcessTimeMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test process time calculation with a slow request."""
        # Arrange
        start_time = 1000.0
        end_time = 1002.5  # 2.5 seconds
        expected_process_time = 2.5

        mock_time.time.side_effect = [start_time, end_time]
        call_next = AsyncMock(return_value=mock_response)

        # Act
        result = await middleware.dispatch(mock_request, call_next)

        # Assert
        process_time_str = result.headers["X-Process-Time"]
        actual_process_time = float(process_time_str)
        assert abs(actual_process_time - expected_process_time) < 1e-10

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.middleware.process_time_middleware.time")
    async def test_process_time_with_very_fast_request(
        self,
        mock_time: Mock,
        middleware: ProcessTimeMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test process time calculation with a very fast request."""
        # Arrange
        start_time = 1000.0
        end_time = 1000.001  # 1 millisecond
        expected_process_time = 0.001

        mock_time.time.side_effect = [start_time, end_time]
        call_next = AsyncMock(return_value=mock_response)

        # Act
        result = await middleware.dispatch(mock_request, call_next)

        # Assert
        process_time_str = result.headers["X-Process-Time"]
        actual_process_time = float(process_time_str)
        assert abs(actual_process_time - expected_process_time) < 1e-10

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_time_header_is_string(
        self,
        middleware: ProcessTimeMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that X-Process-Time header value is a string."""
        # Arrange
        call_next = AsyncMock(return_value=mock_response)

        # Act
        result = await middleware.dispatch(mock_request, call_next)

        # Assert
        process_time_value = result.headers["X-Process-Time"]
        assert isinstance(process_time_value, str)

        # Should be convertible to float
        float(process_time_value)  # Should not raise exception

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_time_precision(
        self,
        middleware: ProcessTimeMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that process time has reasonable precision."""
        # Arrange
        call_next = AsyncMock(return_value=mock_response)

        # Act
        result = await middleware.dispatch(mock_request, call_next)

        # Assert
        process_time_str = result.headers["X-Process-Time"]

        # Check that the string representation has decimal places
        # (even very fast operations should have some decimal precision)
        assert "." in process_time_str or process_time_str == "0"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.middleware.process_time_middleware.time")
    async def test_time_calls_order(
        self,
        mock_time: Mock,
        middleware: ProcessTimeMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that time.time() is called in correct order."""
        # Arrange
        mock_time.time.side_effect = [1000.0, 1000.1]
        call_next = AsyncMock(return_value=mock_response)

        # Act
        await middleware.dispatch(mock_request, call_next)

        # Assert
        assert mock_time.time.call_count == 2
        # First call should be before call_next, second call after

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_with_multiple_requests_sequential(
        self,
        middleware: ProcessTimeMiddleware,
        mock_response: Response,
    ) -> None:
        """Test that middleware handles multiple sequential requests correctly."""
        # Arrange
        call_next = AsyncMock(return_value=mock_response)
        requests = []

        for i in range(3):
            scope = {
                "type": "http",
                "method": "GET",
                "path": f"/test{i}",
                "headers": [],
                "query_string": b"",
            }
            requests.append(Request(scope))

        # Act & Assert
        for request in requests:
            result = await middleware.dispatch(request, call_next)
            assert "X-Process-Time" in result.headers
            process_time = float(result.headers["X-Process-Time"])
            assert process_time >= 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_time_header_value_format(
        self,
        middleware: ProcessTimeMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that process time header value has expected format."""
        # Arrange
        call_next = AsyncMock(return_value=mock_response)

        # Act
        result = await middleware.dispatch(mock_request, call_next)

        # Assert
        process_time_str = result.headers["X-Process-Time"]

        # Should be a valid float string
        process_time = float(process_time_str)
        assert process_time >= 0

        # Convert back to string and ensure it matches
        assert str(process_time) == process_time_str
