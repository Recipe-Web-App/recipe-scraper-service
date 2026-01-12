"""Unit tests for rate limiting.

Tests cover:
- Rate limiter configuration
- Key generation for rate limiting
- Rate limit exceeded handler
- Setup functions
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from slowapi.errors import RateLimitExceeded

from app.cache.rate_limit import (
    _get_auth_rate_limit_key,
    _get_rate_limit_key,
    limiter,
    rate_limit,
    rate_limit_auth,
    rate_limit_exceeded_handler,
    setup_rate_limiting,
)


pytestmark = pytest.mark.unit


class TestRateLimiter:
    """Tests for rate limiter configuration."""

    def test_limiter_exists(self) -> None:
        """Should have a configured limiter instance."""
        assert limiter is not None

    def test_limiter_has_key_func(self) -> None:
        """Limiter should have a key function configured."""
        assert hasattr(limiter, "_key_func") or hasattr(limiter, "key_func")


class TestGetRateLimitKey:
    """Tests for _get_rate_limit_key function."""

    def test_returns_user_key_when_authenticated(self) -> None:
        """Should return user-based key when user is authenticated."""
        mock_request = MagicMock()
        mock_request.state.user = MagicMock()
        mock_request.state.user.id = "user-123"

        result = _get_rate_limit_key(mock_request)

        assert result == "user:user-123"

    def test_returns_ip_when_no_user(self) -> None:
        """Should return IP address when no user is authenticated."""
        mock_request = MagicMock()
        mock_request.state.user = None

        with patch(
            "app.cache.rate_limit.get_remote_address",
            return_value="192.168.1.1",
        ):
            result = _get_rate_limit_key(mock_request)

        assert result == "192.168.1.1"

    def test_returns_ip_when_state_has_no_user(self) -> None:
        """Should return IP when state has no user attribute."""
        mock_request = MagicMock()
        # Configure state to not have a 'user' attribute
        mock_request.state = MagicMock(spec=[])

        with patch(
            "app.cache.rate_limit.get_remote_address",
            return_value="10.0.0.1",
        ):
            result = _get_rate_limit_key(mock_request)

        assert result == "10.0.0.1"


class TestGetAuthRateLimitKey:
    """Tests for _get_auth_rate_limit_key function."""

    def test_always_returns_ip_based_key(self) -> None:
        """Should always return IP-based key for auth endpoints."""
        mock_request = MagicMock()

        with patch(
            "app.cache.rate_limit.get_remote_address",
            return_value="192.168.1.1",
        ):
            result = _get_auth_rate_limit_key(mock_request)

        assert result == "auth:192.168.1.1"


class TestRateLimitExceededHandler:
    """Tests for rate_limit_exceeded_handler function."""

    @pytest.mark.asyncio
    async def test_returns_429_status(self) -> None:
        """Should return 429 status code."""
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/recipe-scraper/test"
        mock_request.method = "GET"
        mock_request.headers = {}

        # Create a proper mock limit object
        mock_limit = MagicMock()
        mock_limit.error_message = None
        exc = RateLimitExceeded(mock_limit)
        exc.detail = "10/minute"

        with patch("app.cache.rate_limit.get_remote_address", return_value="1.2.3.4"):
            response = await rate_limit_exceeded_handler(mock_request, exc)

        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_includes_error_details(self) -> None:
        """Should include error details in response body."""
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/recipe-scraper/test"
        mock_request.method = "GET"
        mock_request.headers = {}

        # Create a proper mock limit object
        mock_limit = MagicMock()
        mock_limit.error_message = None
        exc = RateLimitExceeded(mock_limit)
        exc.detail = "10/minute"

        with patch("app.cache.rate_limit.get_remote_address", return_value="1.2.3.4"):
            response = await rate_limit_exceeded_handler(mock_request, exc)

        # Parse response body
        body = json.loads(response.body)
        assert body["error"] == "rate_limit_exceeded"
        assert "message" in body


class TestSetupRateLimiting:
    """Tests for setup_rate_limiting function."""

    def test_stores_limiter_in_app_state(self) -> None:
        """Should store limiter in app state."""
        mock_app = MagicMock()

        setup_rate_limiting(mock_app)

        assert mock_app.state.limiter is limiter

    def test_registers_exception_handler(self) -> None:
        """Should register rate limit exception handler."""
        mock_app = MagicMock()

        setup_rate_limiting(mock_app)

        mock_app.add_exception_handler.assert_called_once()


class TestRateLimitDecorator:
    """Tests for rate_limit decorator function."""

    def test_returns_callable(self) -> None:
        """Should return a callable decorator."""
        result = rate_limit("10/minute")

        assert callable(result)


class TestRateLimitAuthDecorator:
    """Tests for rate_limit_auth decorator function."""

    def test_returns_callable(self) -> None:
        """Should return a callable decorator."""
        result = rate_limit_auth()

        assert callable(result)
