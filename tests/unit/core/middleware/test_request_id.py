"""Unit tests for request ID middleware.

Tests cover:
- Request ID generation
- Request ID propagation from headers
- Response header addition
- Request state storage
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.middleware.request_id import RequestIDMiddleware


pytestmark = pytest.mark.unit


class TestRequestIDMiddleware:
    """Tests for RequestIDMiddleware."""

    def test_init_default_header(self) -> None:
        """Should use default header name."""
        app = MagicMock()
        middleware = RequestIDMiddleware(app)
        assert middleware.header_name == "X-Request-ID"

    def test_init_custom_header(self) -> None:
        """Should accept custom header name."""
        app = MagicMock()
        middleware = RequestIDMiddleware(app, header_name="X-Correlation-ID")
        assert middleware.header_name == "X-Correlation-ID"

    @pytest.mark.asyncio
    async def test_generates_request_id_when_missing(self) -> None:
        """Should generate new UUID when no request ID header present."""
        app = MagicMock()
        middleware = RequestIDMiddleware(app)

        request = MagicMock()
        request.headers = {}
        request.state = MagicMock()

        response = MagicMock()
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        with (
            patch("app.core.middleware.request_id.clear_context"),
            patch("app.core.middleware.request_id.bind_context"),
        ):
            result = await middleware.dispatch(request, call_next)

        # Should have set request_id on state
        assert hasattr(request.state, "request_id")
        # Should have added header to response
        assert "X-Request-ID" in result.headers

    @pytest.mark.asyncio
    async def test_propagates_existing_request_id(self) -> None:
        """Should use existing request ID from header."""
        app = MagicMock()
        middleware = RequestIDMiddleware(app)

        existing_id = "existing-request-id-123"
        request = MagicMock()
        request.headers = {"X-Request-ID": existing_id}
        request.state = MagicMock()

        response = MagicMock()
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        with (
            patch("app.core.middleware.request_id.clear_context"),
            patch("app.core.middleware.request_id.bind_context") as mock_bind,
        ):
            result = await middleware.dispatch(request, call_next)

        assert request.state.request_id == existing_id
        assert result.headers["X-Request-ID"] == existing_id
        mock_bind.assert_called_once_with(request_id=existing_id)

    @pytest.mark.asyncio
    async def test_clears_context_at_start(self) -> None:
        """Should clear logging context at request start."""
        app = MagicMock()
        middleware = RequestIDMiddleware(app)

        request = MagicMock()
        request.headers = {}
        request.state = MagicMock()

        response = MagicMock()
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        with (
            patch("app.core.middleware.request_id.clear_context") as mock_clear,
            patch("app.core.middleware.request_id.bind_context"),
        ):
            await middleware.dispatch(request, call_next)

        mock_clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_binds_request_id_to_context(self) -> None:
        """Should bind request ID to logging context."""
        app = MagicMock()
        middleware = RequestIDMiddleware(app)

        request = MagicMock()
        request.headers = {}
        request.state = MagicMock()

        response = MagicMock()
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        with (
            patch("app.core.middleware.request_id.clear_context"),
            patch("app.core.middleware.request_id.bind_context") as mock_bind,
        ):
            await middleware.dispatch(request, call_next)

        mock_bind.assert_called_once()
        call_args = mock_bind.call_args
        assert "request_id" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_calls_next_middleware(self) -> None:
        """Should call next middleware in chain."""
        app = MagicMock()
        middleware = RequestIDMiddleware(app)

        request = MagicMock()
        request.headers = {}
        request.state = MagicMock()

        response = MagicMock()
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        with (
            patch("app.core.middleware.request_id.clear_context"),
            patch("app.core.middleware.request_id.bind_context"),
        ):
            await middleware.dispatch(request, call_next)

        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_custom_header_name_used(self) -> None:
        """Should use custom header name for both request and response."""
        app = MagicMock()
        middleware = RequestIDMiddleware(app, header_name="X-Trace-ID")

        existing_id = "trace-123"
        request = MagicMock()
        request.headers = {"X-Trace-ID": existing_id}
        request.state = MagicMock()

        response = MagicMock()
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        with (
            patch("app.core.middleware.request_id.clear_context"),
            patch("app.core.middleware.request_id.bind_context"),
        ):
            result = await middleware.dispatch(request, call_next)

        assert result.headers["X-Trace-ID"] == existing_id
