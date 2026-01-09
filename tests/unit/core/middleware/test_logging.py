"""Unit tests for logging middleware.

Tests cover:
- Request/response logging
- Excluded paths
- Client IP extraction
- Context binding
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.middleware.logging import LoggingMiddleware


pytestmark = pytest.mark.unit


class TestLoggingMiddleware:
    """Tests for LoggingMiddleware."""

    def test_init_defaults(self) -> None:
        """Should use default values."""
        app = MagicMock()
        middleware = LoggingMiddleware(app)

        assert middleware.log_request_body is False
        assert "/health" in middleware.exclude_paths
        assert "/metrics" in middleware.exclude_paths

    def test_init_custom_values(self) -> None:
        """Should accept custom values."""
        app = MagicMock()
        middleware = LoggingMiddleware(
            app, log_request_body=True, exclude_paths={"/custom", "/ignore"}
        )

        assert middleware.log_request_body is True
        assert middleware.exclude_paths == {"/custom", "/ignore"}

    @pytest.mark.asyncio
    async def test_skips_excluded_paths(self) -> None:
        """Should skip logging for excluded paths."""
        app = MagicMock()
        middleware = LoggingMiddleware(app)

        request = MagicMock()
        request.url = MagicMock()
        request.url.path = "/health"

        response = MagicMock()
        call_next = AsyncMock(return_value=response)

        with (
            patch("app.core.middleware.logging.bind_context") as mock_bind,
            patch("app.core.middleware.logging.logger") as mock_logger,
        ):
            await middleware.dispatch(request, call_next)

            # Should not bind context or log for excluded paths
            mock_bind.assert_not_called()
            mock_logger.info.assert_not_called()

    @pytest.mark.asyncio
    async def test_logs_non_excluded_paths(self) -> None:
        """Should log requests for non-excluded paths."""
        app = MagicMock()
        middleware = LoggingMiddleware(app)

        request = MagicMock()
        request.url = MagicMock()
        request.url.path = "/api/users"
        request.method = "GET"
        request.headers = {"user-agent": "TestClient/1.0"}
        request.query_params = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        response = MagicMock()
        response.status_code = 200
        call_next = AsyncMock(return_value=response)

        with (
            patch("app.core.middleware.logging.bind_context"),
            patch("app.core.middleware.logging.logger") as mock_logger,
        ):
            await middleware.dispatch(request, call_next)

            # Should log request start and completion
            assert mock_logger.info.call_count == 2

    @pytest.mark.asyncio
    async def test_binds_request_context(self) -> None:
        """Should bind request context for logging."""
        app = MagicMock()
        middleware = LoggingMiddleware(app)

        request = MagicMock()
        request.url = MagicMock()
        request.url.path = "/api/test"
        request.method = "POST"
        request.headers = {"user-agent": "TestAgent"}
        request.query_params = {}
        request.client = MagicMock()
        request.client.host = "192.168.1.1"

        response = MagicMock()
        response.status_code = 201
        call_next = AsyncMock(return_value=response)

        with (
            patch("app.core.middleware.logging.bind_context") as mock_bind,
            patch("app.core.middleware.logging.logger"),
        ):
            await middleware.dispatch(request, call_next)

            mock_bind.assert_called_once()
            call_kwargs = mock_bind.call_args.kwargs
            assert call_kwargs["method"] == "POST"
            assert call_kwargs["path"] == "/api/test"
            assert call_kwargs["user_agent"] == "TestAgent"

    @pytest.mark.asyncio
    async def test_calls_next_middleware(self) -> None:
        """Should call next middleware in chain."""
        app = MagicMock()
        middleware = LoggingMiddleware(app)

        request = MagicMock()
        request.url = MagicMock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {}
        request.query_params = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        response = MagicMock()
        response.status_code = 200
        call_next = AsyncMock(return_value=response)

        with (
            patch("app.core.middleware.logging.bind_context"),
            patch("app.core.middleware.logging.logger"),
        ):
            await middleware.dispatch(request, call_next)

            call_next.assert_called_once_with(request)


class TestGetClientIP:
    """Tests for _get_client_ip method."""

    def test_extracts_from_x_forwarded_for(self) -> None:
        """Should extract IP from X-Forwarded-For header."""
        app = MagicMock()
        middleware = LoggingMiddleware(app)

        request = MagicMock()
        request.headers = {
            "x-forwarded-for": "203.0.113.1, 70.41.3.18, 150.172.238.178"
        }
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "203.0.113.1"

    def test_extracts_from_x_real_ip(self) -> None:
        """Should extract IP from X-Real-IP header."""
        app = MagicMock()
        middleware = LoggingMiddleware(app)

        request = MagicMock()
        request.headers = {"x-real-ip": "10.0.0.1"}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "10.0.0.1"

    def test_prefers_x_forwarded_for_over_x_real_ip(self) -> None:
        """Should prefer X-Forwarded-For over X-Real-IP."""
        app = MagicMock()
        middleware = LoggingMiddleware(app)

        request = MagicMock()
        request.headers = {
            "x-forwarded-for": "203.0.113.1",
            "x-real-ip": "10.0.0.1",
        }
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "203.0.113.1"

    def test_falls_back_to_client_host(self) -> None:
        """Should fall back to direct client host."""
        app = MagicMock()
        middleware = LoggingMiddleware(app)

        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "172.16.0.1"

        ip = middleware._get_client_ip(request)
        assert ip == "172.16.0.1"

    def test_returns_unknown_when_no_client(self) -> None:
        """Should return 'unknown' when no client info available."""
        app = MagicMock()
        middleware = LoggingMiddleware(app)

        request = MagicMock()
        request.headers = {}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "unknown"

    def test_handles_x_forwarded_for_with_spaces(self) -> None:
        """Should handle X-Forwarded-For with spaces."""
        app = MagicMock()
        middleware = LoggingMiddleware(app)

        request = MagicMock()
        request.headers = {"x-forwarded-for": "  192.168.1.1  , 10.0.0.1"}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.1"
