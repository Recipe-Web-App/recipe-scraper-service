"""Unit tests for auth endpoints.

Tests cover:
- Login endpoint
- Token refresh endpoint
- Current user endpoint
- Logout endpoint
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.auth import (
    _DEMO_EMAIL,
    _DEMO_PASSWORD,
    BEARER,
    get_current_user_info,
    login,
    logout,
    refresh_token,
)
from app.auth.dependencies import CurrentUser
from app.auth.jwt import TokenExpiredError, TokenInvalidError


pytestmark = pytest.mark.unit


class TestLogin:
    """Tests for login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success_with_valid_credentials(self) -> None:
        """Should return tokens for valid credentials."""
        mock_form = MagicMock()
        mock_form.username = _DEMO_EMAIL
        mock_form.password = _DEMO_PASSWORD

        mock_settings = MagicMock()
        mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30

        with (
            patch(
                "app.api.v1.endpoints.auth.create_access_token",
                return_value="access-token",
            ),
            patch(
                "app.api.v1.endpoints.auth.create_refresh_token",
                return_value="refresh-token",
            ),
        ):
            result = await login(mock_form, mock_settings)

        assert result.access_token == "access-token"
        assert result.refresh_token == "refresh-token"
        assert result.token_type == BEARER
        assert result.expires_in == 30 * 60

    @pytest.mark.asyncio
    async def test_login_fails_with_wrong_email(self) -> None:
        """Should raise 401 for wrong email."""
        mock_form = MagicMock()
        mock_form.username = "wrong@example.com"
        mock_form.password = _DEMO_PASSWORD

        mock_settings = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await login(mock_form, mock_settings)

        assert exc_info.value.status_code == 401
        assert "Incorrect email or password" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_login_fails_with_wrong_password(self) -> None:
        """Should raise 401 for wrong password."""
        mock_form = MagicMock()
        mock_form.username = _DEMO_EMAIL
        mock_form.password = "wrongpassword"

        mock_settings = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await login(mock_form, mock_settings)

        assert exc_info.value.status_code == 401
        assert "Incorrect email or password" in exc_info.value.detail


class TestRefreshToken:
    """Tests for refresh token endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_success_with_valid_token(self) -> None:
        """Should return new tokens for valid refresh token."""
        mock_request = MagicMock()
        mock_request.refresh_token = "valid-refresh-token"

        mock_settings = MagicMock()
        mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30

        mock_payload = MagicMock()
        mock_payload.sub = "user-123"
        mock_payload.roles = ["user"]
        mock_payload.permissions = []

        with (
            patch(
                "app.api.v1.endpoints.auth.decode_token",
                return_value=mock_payload,
            ),
            patch(
                "app.api.v1.endpoints.auth.create_access_token",
                return_value="new-access-token",
            ),
            patch(
                "app.api.v1.endpoints.auth.create_refresh_token",
                return_value="new-refresh-token",
            ),
        ):
            result = await refresh_token(mock_request, mock_settings)

        assert result.access_token == "new-access-token"
        assert result.refresh_token == "new-refresh-token"
        assert result.token_type == BEARER

    @pytest.mark.asyncio
    async def test_refresh_fails_with_expired_token(self) -> None:
        """Should raise 401 for expired refresh token."""
        mock_request = MagicMock()
        mock_request.refresh_token = "expired-token"

        mock_settings = MagicMock()

        with (
            patch(
                "app.api.v1.endpoints.auth.decode_token",
                side_effect=TokenExpiredError("Token expired"),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await refresh_token(mock_request, mock_settings)

        assert exc_info.value.status_code == 401
        assert "Refresh token has expired" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_refresh_fails_with_invalid_token(self) -> None:
        """Should raise 401 for invalid refresh token."""
        mock_request = MagicMock()
        mock_request.refresh_token = "invalid-token"

        mock_settings = MagicMock()

        with (
            patch(
                "app.api.v1.endpoints.auth.decode_token",
                side_effect=TokenInvalidError("Invalid token"),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await refresh_token(mock_request, mock_settings)

        assert exc_info.value.status_code == 401
        assert "Invalid refresh token" in exc_info.value.detail


class TestGetCurrentUserInfo:
    """Tests for get current user info endpoint."""

    @pytest.mark.asyncio
    async def test_returns_user_info(self) -> None:
        """Should return current user info from token."""
        current_user = CurrentUser(
            id="user-123",
            roles=["admin", "user"],
            permissions=["recipe:read"],
            token_type="access",
        )

        result = await get_current_user_info(current_user)

        assert result.sub == "user-123"
        assert result.roles == ["admin", "user"]
        assert result.permissions == ["recipe:read"]
        assert result.type == "access"


class TestLogout:
    """Tests for logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_returns_none(self) -> None:
        """Should return None (no-op for now)."""
        current_user = CurrentUser(id="user-123")

        result = await logout(current_user)

        assert result is None
