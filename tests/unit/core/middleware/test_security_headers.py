"""Unit tests for security headers middleware.

Tests cover:
- Default security headers
- Custom CSP and Permissions Policy
- API path cache control
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.middleware.security_headers import SecurityHeadersMiddleware


pytestmark = pytest.mark.unit


class TestSecurityHeadersMiddleware:
    """Tests for SecurityHeadersMiddleware."""

    def test_init_defaults(self) -> None:
        """Should use default CSP and permissions policy."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)

        assert "default-src 'self'" in middleware.content_security_policy
        assert "accelerometer=()" in middleware.permissions_policy

    def test_init_custom_csp(self) -> None:
        """Should accept custom CSP."""
        app = MagicMock()
        custom_csp = "default-src 'none'; script-src 'self'"
        middleware = SecurityHeadersMiddleware(app, content_security_policy=custom_csp)

        assert middleware.content_security_policy == custom_csp

    def test_init_custom_permissions(self) -> None:
        """Should accept custom permissions policy."""
        app = MagicMock()
        custom_permissions = "geolocation=self"
        middleware = SecurityHeadersMiddleware(
            app, permissions_policy=custom_permissions
        )

        assert middleware.permissions_policy == custom_permissions

    @pytest.mark.asyncio
    async def test_adds_x_content_type_options(self) -> None:
        """Should add X-Content-Type-Options header."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)

        request = MagicMock()
        request.url = MagicMock()
        request.url.path = "/test"

        response = MagicMock()
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        assert result.headers["X-Content-Type-Options"] == "nosniff"

    @pytest.mark.asyncio
    async def test_adds_x_frame_options(self) -> None:
        """Should add X-Frame-Options header."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)

        request = MagicMock()
        request.url = MagicMock()
        request.url.path = "/test"

        response = MagicMock()
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        assert result.headers["X-Frame-Options"] == "DENY"

    @pytest.mark.asyncio
    async def test_adds_x_xss_protection(self) -> None:
        """Should add X-XSS-Protection header."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)

        request = MagicMock()
        request.url = MagicMock()
        request.url.path = "/test"

        response = MagicMock()
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        assert result.headers["X-XSS-Protection"] == "1; mode=block"

    @pytest.mark.asyncio
    async def test_adds_hsts(self) -> None:
        """Should add Strict-Transport-Security header."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)

        request = MagicMock()
        request.url = MagicMock()
        request.url.path = "/test"

        response = MagicMock()
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        hsts = result.headers["Strict-Transport-Security"]
        assert "max-age=31536000" in hsts
        assert "includeSubDomains" in hsts

    @pytest.mark.asyncio
    async def test_adds_referrer_policy(self) -> None:
        """Should add Referrer-Policy header."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)

        request = MagicMock()
        request.url = MagicMock()
        request.url.path = "/test"

        response = MagicMock()
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        assert result.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    @pytest.mark.asyncio
    async def test_adds_csp(self) -> None:
        """Should add Content-Security-Policy header."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)

        request = MagicMock()
        request.url = MagicMock()
        request.url.path = "/test"

        response = MagicMock()
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        assert "Content-Security-Policy" in result.headers

    @pytest.mark.asyncio
    async def test_adds_permissions_policy(self) -> None:
        """Should add Permissions-Policy header."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)

        request = MagicMock()
        request.url = MagicMock()
        request.url.path = "/test"

        response = MagicMock()
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        assert "Permissions-Policy" in result.headers

    @pytest.mark.asyncio
    async def test_adds_cache_control_for_api_paths(self) -> None:
        """Should add cache control headers for /api/ paths."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)

        request = MagicMock()
        request.url = MagicMock()
        request.url.path = "/api/v1/users"

        response = MagicMock()
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        assert "no-store" in result.headers["Cache-Control"]
        assert result.headers["Pragma"] == "no-cache"

    @pytest.mark.asyncio
    async def test_no_cache_control_for_non_api_paths(self) -> None:
        """Should not add cache control for non-API paths."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)

        request = MagicMock()
        request.url = MagicMock()
        request.url.path = "/docs"

        response = MagicMock()
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        assert "Cache-Control" not in result.headers
        assert "Pragma" not in result.headers

    @pytest.mark.asyncio
    async def test_calls_next_middleware(self) -> None:
        """Should call next middleware in chain."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)

        request = MagicMock()
        request.url = MagicMock()
        request.url.path = "/test"

        response = MagicMock()
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        await middleware.dispatch(request, call_next)

        call_next.assert_called_once_with(request)


class TestDefaultPolicies:
    """Tests for default policy methods."""

    def test_default_csp_contains_required_directives(self) -> None:
        """Default CSP should contain essential directives."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)

        csp = middleware._default_csp()

        assert "default-src" in csp
        assert "script-src" in csp
        assert "style-src" in csp
        assert "frame-ancestors" in csp

    def test_default_permissions_disables_sensors(self) -> None:
        """Default permissions should disable sensitive features."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)

        permissions = middleware._default_permissions()

        assert "camera=()" in permissions
        assert "microphone=()" in permissions
        assert "geolocation=()" in permissions
