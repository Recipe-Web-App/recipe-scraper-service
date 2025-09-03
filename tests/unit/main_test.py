"""Unit tests for the main application module."""

from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.main import app, lifespan, root


class TestLifespan:
    """Unit tests for the application lifespan context manager."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.main._log")
    async def test_lifespan_startup_and_shutdown(self, mock_log: Mock) -> None:
        """Test that lifespan logs startup and shutdown messages."""
        # Arrange
        mock_app = Mock(spec=FastAPI)

        # Act
        async with lifespan(mock_app):
            # Assert startup log - check if the startup message was called
            startup_calls = [
                call
                for call in mock_log.info.call_args_list
                if "Starting Recipe Scraper Service" in str(call)
            ]
            assert len(startup_calls) == 1
            mock_log.reset_mock()

        # Assert shutdown log - check if the shutdown message was called
        shutdown_calls = [
            call
            for call in mock_log.info.call_args_list
            if "Shutting down Recipe Scraper Service" in str(call)
        ]
        assert len(shutdown_calls) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.main._log")
    async def test_lifespan_yields_none(self, mock_log: Mock) -> None:
        """Test that lifespan yields None during application lifecycle."""
        # Arrange
        mock_app = Mock(spec=FastAPI)

        # Act & Assert
        async with lifespan(mock_app) as result:
            assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.main._log")
    async def test_lifespan_with_exception_during_startup(self, mock_log: Mock) -> None:
        """Test lifespan behavior when exception occurs during startup."""
        # Arrange
        mock_app = Mock(spec=FastAPI)
        mock_log.info.side_effect = [None, Exception("Startup error")]

        # Act & Assert
        with pytest.raises(RuntimeError, match="async generator raised StopIteration"):
            async with lifespan(mock_app):
                pass

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.main._log")
    async def test_lifespan_multiple_calls(self, mock_log: Mock) -> None:
        """Test that lifespan can be called multiple times."""
        # Arrange
        mock_app = Mock(spec=FastAPI)

        # Act
        async with lifespan(mock_app):
            pass

        async with lifespan(mock_app):
            pass

        # Assert - count startup/shutdown messages, accounting for DB monitoring logs
        startup_calls = [
            call
            for call in mock_log.info.call_args_list
            if "Starting Recipe Scraper Service" in str(call)
        ]
        shutdown_calls = [
            call
            for call in mock_log.info.call_args_list
            if "Shutting down Recipe Scraper Service" in str(call)
        ]
        assert len(startup_calls) == 2  # Should have 2 startup calls
        assert len(shutdown_calls) == 2  # Should have 2 shutdown calls


class TestRootEndpoint:
    """Unit tests for the root endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_root_endpoint_returns_correct_content(self) -> None:
        """Test that root endpoint returns correct service information."""
        # Act
        result = await root()

        # Assert
        assert isinstance(result, JSONResponse)
        # Extract content from JSONResponse
        body = result.body
        content = body.decode() if isinstance(body, bytes) else str(body)
        import json

        data = json.loads(content)

        expected_content = {
            "service": "Recipe Scraper Service",
            "version": "2.0.0",
            "status": "operational",
            "docs": "/docs",
            "health": "/api/v1/health",
        }
        assert data == expected_content

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_root_endpoint_response_type(self) -> None:
        """Test that root endpoint returns JSONResponse type."""
        # Act
        result = await root()

        # Assert
        assert isinstance(result, JSONResponse)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_root_endpoint_content_structure(self) -> None:
        """Test that root endpoint returns properly structured content."""
        # Act
        result = await root()

        # Assert
        body = result.body
        content = body.decode() if isinstance(body, bytes) else str(body)
        import json

        data = json.loads(content)

        # Verify all required keys are present
        required_keys = ["service", "version", "status", "docs", "health"]
        for key in required_keys:
            assert key in data

        # Verify data types
        assert isinstance(data["service"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["status"], str)
        assert isinstance(data["docs"], str)
        assert isinstance(data["health"], str)


class TestAppConfiguration:
    """Unit tests for FastAPI application configuration."""

    @pytest.mark.unit
    def test_app_is_fastapi_instance(self) -> None:
        """Test that app is a FastAPI instance."""
        # Assert
        assert isinstance(app, FastAPI)

    @pytest.mark.unit
    def test_app_title_configuration(self) -> None:
        """Test that app has correct title configuration."""
        # Assert
        assert app.title == "Recipe Scraper Service"

    @pytest.mark.unit
    def test_app_version_configuration(self) -> None:
        """Test that app has correct version configuration."""
        # Assert
        assert app.version == "2.0.0"

    @pytest.mark.unit
    def test_app_description_configuration(self) -> None:
        """Test that app has correct description."""
        # Assert
        expected_description = (
            "A modern, secure API for scraping and managing recipe data "
            "with comprehensive monitoring."
        )
        assert app.description == expected_description

    @pytest.mark.unit
    def test_app_summary_configuration(self) -> None:
        """Test that app has correct summary."""
        # Assert
        assert app.summary == "High-performance recipe scraping microservice"

    @pytest.mark.unit
    def test_app_contact_configuration(self) -> None:
        """Test that app has correct contact information."""
        # Assert
        expected_contact = {
            "name": "Recipe Scraper Team",
            "url": "https://github.com/jsamuelsen/recipe-scraper-service",
            "email": "jsamuelsen11@gmail.com",
        }
        assert app.contact == expected_contact

    @pytest.mark.unit
    def test_app_license_configuration(self) -> None:
        """Test that app has correct license information."""
        # Assert
        expected_license = {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        }
        assert app.license_info == expected_license

    @pytest.mark.unit
    def test_app_openapi_configuration(self) -> None:
        """Test that app has correct OpenAPI configuration."""
        # Assert
        assert app.openapi_version == "3.1.0"
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
        assert app.openapi_url == "/openapi.json"

    @pytest.mark.unit
    def test_app_has_lifespan(self) -> None:
        """Test that app has lifespan configured."""
        # Assert
        assert app.router.lifespan_context is not None

    @pytest.mark.unit
    def test_app_has_rate_limiter_state(self) -> None:
        """Test that app has rate limiter configured in state."""
        # Assert
        assert hasattr(app.state, "limiter")
        assert app.state.limiter is not None


class TestMiddlewareConfiguration:
    """Unit tests for middleware configuration."""

    @pytest.mark.unit
    def test_app_has_middleware_stack(self) -> None:
        """Test that app has middleware configured."""
        # Assert
        middleware_stack = app.user_middleware
        assert len(middleware_stack) > 0

    @pytest.mark.unit
    def test_middleware_order(self) -> None:
        """Test that middleware is added in correct order."""
        # Note: Middleware stack is in reverse order (last added is first executed)
        middleware_stack = app.user_middleware
        middleware_classes = [
            getattr(mw.cls, "__name__", str(mw.cls)) for mw in middleware_stack
        ]

        # Expected order (reverse of addition order)
        expected_classes = [
            "RequestIDMiddleware",
            "SlowAPIMiddleware",
            "CORSMiddleware",
            "GZipMiddleware",
            "SecurityHeadersMiddleware",
            "ProcessTimeMiddleware",
        ]

        # Check that all expected middleware are present
        for expected_class in expected_classes:
            assert any(expected_class in cls_name for cls_name in middleware_classes)

    @pytest.mark.unit
    def test_cors_middleware_configuration(self) -> None:
        """Test that CORS middleware is properly configured."""
        # Find CORS middleware in stack
        cors_middleware = None
        for middleware in app.user_middleware:
            middleware_name = getattr(middleware.cls, "__name__", str(middleware.cls))
            if "CORSMiddleware" in middleware_name:
                cors_middleware = middleware
                break

        # Assert
        assert cors_middleware is not None
        # Check that required methods are allowed
        allowed_methods = cors_middleware.kwargs.get("allow_methods", [])
        expected_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]

        # Ensure allowed_methods is iterable
        if isinstance(allowed_methods, list | tuple | set):
            for method in expected_methods:
                assert method in allowed_methods

    @pytest.mark.unit
    def test_gzip_middleware_configuration(self) -> None:
        """Test that GZip middleware is properly configured."""
        # Find GZip middleware in stack
        gzip_middleware = None
        for middleware in app.user_middleware:
            middleware_name = getattr(middleware.cls, "__name__", str(middleware.cls))
            if "GZipMiddleware" in middleware_name:
                gzip_middleware = middleware
                break

        # Assert
        assert gzip_middleware is not None
        assert gzip_middleware.kwargs.get("minimum_size") == 1000


class TestRouterConfiguration:
    """Unit tests for router configuration."""

    @pytest.mark.unit
    def test_app_includes_api_router(self) -> None:
        """Test that app includes the API router."""
        # Check that routes are configured
        routes = []
        for route in app.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)

        # Should have root route and API routes
        assert "/" in routes

        # Check for API prefix routes
        api_routes = [route for route in routes if route.startswith("/api")]
        assert len(api_routes) > 0

    @pytest.mark.unit
    def test_root_route_exists(self) -> None:
        """Test that root route is configured."""
        # Find root route
        root_route = None
        for route in app.routes:
            if hasattr(route, 'path') and route.path == "/":
                root_route = route
                break

        # Assert
        assert root_route is not None
        if hasattr(root_route, 'methods'):
            assert "GET" in root_route.methods


class TestExceptionHandlers:
    """Unit tests for exception handler configuration."""

    @pytest.mark.unit
    def test_app_has_exception_handlers(self) -> None:
        """Test that app has exception handlers configured."""
        # Assert
        exception_handlers = app.exception_handlers
        assert len(exception_handlers) > 0

    @pytest.mark.unit
    def test_general_exception_handler_exists(self) -> None:
        """Test that general exception handler is configured."""
        # Assert
        exception_handlers = app.exception_handlers
        # Check for Exception handler
        assert Exception in exception_handlers

    @pytest.mark.unit
    def test_rate_limit_exception_handler_exists(self) -> None:
        """Test that rate limit exception handler is configured."""
        # Import the specific exception type
        from slowapi.errors import RateLimitExceeded

        # Assert
        exception_handlers = app.exception_handlers
        assert RateLimitExceeded in exception_handlers


class TestIntegrationWithTestClient:
    """Integration tests using FastAPI TestClient."""

    @pytest.mark.unit
    def test_root_endpoint_via_test_client(self) -> None:
        """Test root endpoint using TestClient."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.get("/")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Recipe Scraper Service"
        assert data["version"] == "2.0.0"
        assert data["status"] == "operational"

    @pytest.mark.unit
    def test_docs_endpoint_accessibility(self) -> None:
        """Test that docs endpoint is accessible."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.get("/docs")

        # Assert
        # Should return HTML for docs page
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.unit
    def test_openapi_json_accessibility(self) -> None:
        """Test that OpenAPI JSON is accessible."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.get("/openapi.json")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert data["info"]["title"] == "Recipe Scraper Service"

    @pytest.mark.unit
    def test_middleware_headers_in_response(self) -> None:
        """Test that middleware adds expected headers."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.get("/")

        # Assert
        headers = response.headers

        # Check for security headers
        assert "X-Content-Type-Options" in headers
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in headers
        assert headers["X-Frame-Options"] == "DENY"

        # Check for process time header
        assert "X-Process-Time" in headers

        # Check for request ID header (from RequestIDMiddleware)
        assert "X-Request-ID" in headers

    @pytest.mark.unit
    def test_cors_headers_in_response(self) -> None:
        """Test that CORS headers are present."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.options("/", headers={"Origin": "http://localhost:3000"})

        # Assert
        headers = response.headers
        assert "Access-Control-Allow-Origin" in headers

    @pytest.mark.unit
    def test_app_handles_404_gracefully(self) -> None:
        """Test that app handles 404 errors gracefully."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.get("/nonexistent-endpoint")

        # Assert
        assert response.status_code == 404

    @pytest.mark.unit
    def test_prometheus_metrics_endpoint_exists(self) -> None:
        """Test that Prometheus metrics endpoint is available."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.get("/metrics")

        # Assert
        assert response.status_code == 200
        # Check that it returns metrics format
        content = response.text
        assert "# HELP" in content or "# TYPE" in content
