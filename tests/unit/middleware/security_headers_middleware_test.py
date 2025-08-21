"""Unit tests for the SecurityHeadersMiddleware class."""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import Request, Response

from app.middleware.security_headers_middleware import SecurityHeadersMiddleware


class TestSecurityHeadersMiddleware:
    """Unit tests for SecurityHeadersMiddleware."""

    @pytest.fixture
    def middleware(self) -> SecurityHeadersMiddleware:
        """Create SecurityHeadersMiddleware instance for testing."""
        # Mock app is required by BaseHTTPMiddleware
        mock_app = Mock()
        return SecurityHeadersMiddleware(mock_app)

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
    async def test_dispatch_adds_security_headers(
        self,
        middleware: SecurityHeadersMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that dispatch adds all required security headers."""
        # Arrange
        call_next = AsyncMock(return_value=mock_response)

        # Act
        result = await middleware.dispatch(mock_request, call_next)

        # Assert
        assert call_next.called
        call_next.assert_called_once_with(mock_request)

        # Check all security headers are present
        expected_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'"
            ),
        }

        for header_name, expected_value in expected_headers.items():
            assert header_name in result.headers
            assert result.headers[header_name] == expected_value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_preserves_original_response_content(
        self,
        middleware: SecurityHeadersMiddleware,
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
        middleware: SecurityHeadersMiddleware,
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
        middleware: SecurityHeadersMiddleware,
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

        # Check security headers are also added
        assert "X-Content-Type-Options" in result.headers
        assert "X-Frame-Options" in result.headers

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_overwrites_conflicting_security_headers(
        self,
        middleware: SecurityHeadersMiddleware,
        mock_request: Request,
    ) -> None:
        """Test that dispatch overwrites any existing security headers."""
        # Arrange
        conflicting_headers = {
            "X-Content-Type-Options": "wrong-value",
            "X-Frame-Options": "SAMEORIGIN",
        }
        mock_response = Response(
            content="Test", status_code=200, headers=conflicting_headers
        )
        call_next = AsyncMock(return_value=mock_response)

        # Act
        result = await middleware.dispatch(mock_request, call_next)

        # Assert
        # Check that security headers have correct values (not the conflicting ones)
        assert result.headers["X-Content-Type-Options"] == "nosniff"
        assert result.headers["X-Frame-Options"] == "DENY"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_handles_different_request_methods(
        self,
        middleware: SecurityHeadersMiddleware,
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
            assert "X-Content-Type-Options" in result.headers
            assert result.headers["X-Content-Type-Options"] == "nosniff"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_handles_different_paths(
        self,
        middleware: SecurityHeadersMiddleware,
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
            assert "X-Frame-Options" in result.headers
            assert result.headers["X-Frame-Options"] == "DENY"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_content_security_policy_header_value(
        self,
        middleware: SecurityHeadersMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that Content-Security-Policy header has correct value."""
        # Arrange
        call_next = AsyncMock(return_value=mock_response)

        # Act
        result = await middleware.dispatch(mock_request, call_next)

        # Assert
        csp_header = result.headers["Content-Security-Policy"]
        expected_csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'"
        )
        assert csp_header == expected_csp

        # Check that CSP contains required directives
        assert "default-src 'self'" in csp_header
        assert "script-src 'self' 'unsafe-inline'" in csp_header
        assert "style-src 'self' 'unsafe-inline'" in csp_header

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_strict_transport_security_header_value(
        self,
        middleware: SecurityHeadersMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that Strict-Transport-Security header has correct value."""
        # Arrange
        call_next = AsyncMock(return_value=mock_response)

        # Act
        result = await middleware.dispatch(mock_request, call_next)

        # Assert
        hsts_header = result.headers["Strict-Transport-Security"]
        expected_hsts = "max-age=31536000; includeSubDomains"
        assert hsts_header == expected_hsts

        # Check that HSTS contains required directives
        assert "max-age=31536000" in hsts_header
        assert "includeSubDomains" in hsts_header

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_with_error_response(
        self,
        middleware: SecurityHeadersMiddleware,
        mock_request: Request,
    ) -> None:
        """Test that dispatch adds headers even for error responses."""
        # Arrange
        error_response = Response(content="Not Found", status_code=404)
        call_next = AsyncMock(return_value=error_response)

        # Act
        result = await middleware.dispatch(mock_request, call_next)

        # Assert
        assert result.status_code == 404
        assert "X-Content-Type-Options" in result.headers
        assert "X-Frame-Options" in result.headers
        assert "X-XSS-Protection" in result.headers

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_middleware_call_next_exception_propagation(
        self,
        middleware: SecurityHeadersMiddleware,
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
    async def test_all_security_headers_count(
        self,
        middleware: SecurityHeadersMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that exactly 6 security headers are added."""
        # Arrange
        call_next = AsyncMock(return_value=mock_response)

        # Act
        result = await middleware.dispatch(mock_request, call_next)

        # Assert
        security_header_names = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Referrer-Policy",
            "Content-Security-Policy",
        ]

        headers_found = 0
        for header_name in security_header_names:
            if header_name in result.headers:
                headers_found += 1

        assert headers_found == 6

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_x_xss_protection_header_value(
        self,
        middleware: SecurityHeadersMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that X-XSS-Protection header has correct value."""
        # Arrange
        call_next = AsyncMock(return_value=mock_response)

        # Act
        result = await middleware.dispatch(mock_request, call_next)

        # Assert
        xss_header = result.headers["X-XSS-Protection"]
        expected_xss = "1; mode=block"
        assert xss_header == expected_xss
        assert "1" in xss_header
        assert "mode=block" in xss_header

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_referrer_policy_header_value(
        self,
        middleware: SecurityHeadersMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that Referrer-Policy header has correct value."""
        # Arrange
        call_next = AsyncMock(return_value=mock_response)

        # Act
        result = await middleware.dispatch(mock_request, call_next)

        # Assert
        referrer_header = result.headers["Referrer-Policy"]
        expected_referrer = "strict-origin-when-cross-origin"
        assert referrer_header == expected_referrer
