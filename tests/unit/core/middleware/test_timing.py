"""Unit tests for timing middleware.

Tests cover:
- Request timing measurement
- Response header addition
- Slow request logging
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.middleware.timing import SLOW_REQUEST_THRESHOLD, TimingMiddleware


pytestmark = pytest.mark.unit


class TestTimingMiddleware:
    """Tests for TimingMiddleware."""

    def test_init_defaults(self) -> None:
        """Should use default values."""
        app = MagicMock()
        middleware = TimingMiddleware(app)
        assert middleware.header_name == "X-Process-Time"
        assert middleware.slow_threshold == SLOW_REQUEST_THRESHOLD

    def test_init_custom_values(self) -> None:
        """Should accept custom values."""
        app = MagicMock()
        middleware = TimingMiddleware(
            app, header_name="X-Response-Time", slow_threshold=2.0
        )
        assert middleware.header_name == "X-Response-Time"
        assert middleware.slow_threshold == 2.0

    @pytest.mark.asyncio
    async def test_adds_timing_header(self) -> None:
        """Should add timing header to response."""
        app = MagicMock()
        middleware = TimingMiddleware(app)

        request = MagicMock()
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/test"

        response = MagicMock()
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        assert "X-Process-Time" in result.headers
        assert result.headers["X-Process-Time"].endswith("ms")

    @pytest.mark.asyncio
    async def test_timing_header_format(self) -> None:
        """Should format timing as milliseconds."""
        app = MagicMock()
        middleware = TimingMiddleware(app)

        request = MagicMock()
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/test"

        response = MagicMock()
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        # Should be a valid number followed by "ms"
        timing_value = result.headers["X-Process-Time"]
        assert timing_value.endswith("ms")
        numeric_part = timing_value[:-2]
        assert float(numeric_part) >= 0

    @pytest.mark.asyncio
    async def test_logs_slow_requests(self) -> None:
        """Should log warning for slow requests."""
        app = MagicMock()
        middleware = TimingMiddleware(app, slow_threshold=0.0)  # Very low threshold

        request = MagicMock()
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/slow-endpoint"

        response = MagicMock()
        response.headers = {}

        # Simulate slow response by delaying
        async def slow_call_next(req: MagicMock) -> MagicMock:
            return response

        call_next = AsyncMock(side_effect=slow_call_next)

        with patch("app.core.middleware.timing.logger") as mock_logger:
            await middleware.dispatch(request, call_next)

            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert "Slow request detected" in call_args.args

    @pytest.mark.asyncio
    async def test_no_warning_for_fast_requests(self) -> None:
        """Should not log warning for fast requests."""
        app = MagicMock()
        middleware = TimingMiddleware(app, slow_threshold=10.0)  # High threshold

        request = MagicMock()
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/fast-endpoint"

        response = MagicMock()
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        with patch("app.core.middleware.timing.logger") as mock_logger:
            await middleware.dispatch(request, call_next)

            mock_logger.warning.assert_not_called()

    @pytest.mark.asyncio
    async def test_calls_next_middleware(self) -> None:
        """Should call next middleware in chain."""
        app = MagicMock()
        middleware = TimingMiddleware(app)

        request = MagicMock()
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/test"

        response = MagicMock()
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        await middleware.dispatch(request, call_next)

        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_custom_header_name(self) -> None:
        """Should use custom header name."""
        app = MagicMock()
        middleware = TimingMiddleware(app, header_name="X-Server-Time")

        request = MagicMock()
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/test"

        response = MagicMock()
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        assert "X-Server-Time" in result.headers
        assert "X-Process-Time" not in result.headers


class TestSlowRequestThreshold:
    """Tests for slow request threshold constant."""

    def test_threshold_is_positive(self) -> None:
        """Threshold should be a positive number."""
        assert SLOW_REQUEST_THRESHOLD > 0

    def test_threshold_is_reasonable(self) -> None:
        """Threshold should be a reasonable value (< 10 seconds)."""
        assert SLOW_REQUEST_THRESHOLD < 10
