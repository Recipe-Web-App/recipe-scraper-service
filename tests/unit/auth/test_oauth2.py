"""Unit tests for OAuth2 authentication schemes.

Tests cover:
- Token validation dependencies
- API key validation
- Combined auth validation
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.auth.jwt import TokenExpiredError, TokenInvalidError, TokenPayload
from app.auth.oauth2 import (
    validate_api_key,
    validate_token,
    validate_token_optional,
    validate_token_or_api_key,
)
from app.core.config import Settings


pytestmark = pytest.mark.unit


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def oauth2_settings() -> Settings:
    """Settings for OAuth2 testing."""
    return Settings(
        ENVIRONMENT="testing",
        JWT_SECRET_KEY="test-secret-key-minimum-32-characters-long",
        JWT_ALGORITHM="HS256",
        SERVICE_API_KEYS=["valid-api-key-123", "another-key-456"],
    )


@pytest.fixture
def valid_token_payload() -> dict:
    """Valid decoded token payload."""
    return {
        "sub": "user-123",
        "exp": "2099-01-01T00:00:00",
        "iat": "2024-01-01T00:00:00",
        "type": "access",
        "roles": ["user"],
        "permissions": ["recipe:read"],
    }


# =============================================================================
# validate_token Tests
# =============================================================================


class TestValidateToken:
    """Tests for validate_token dependency."""

    async def test_returns_payload_for_valid_token(self, oauth2_settings):
        """Should return decoded payload for valid token."""
        mock_payload = TokenPayload(
            sub="user-123",
            exp="2099-01-01T00:00:00",
            iat="2024-01-01T00:00:00",
            type="access",
            roles=["user"],
            permissions=["recipe:read"],
        )

        with patch("app.auth.oauth2.decode_token", return_value=mock_payload):
            result = await validate_token("valid-token")

        assert result["sub"] == "user-123"
        assert result["roles"] == ["user"]

    async def test_raises_401_for_expired_token(self, oauth2_settings):
        """Should raise 401 for expired tokens."""
        with (
            patch(
                "app.auth.oauth2.decode_token", side_effect=TokenExpiredError("expired")
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await validate_token("expired-token")

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    async def test_raises_401_for_invalid_token(self, oauth2_settings):
        """Should raise 401 for invalid tokens."""
        with (
            patch(
                "app.auth.oauth2.decode_token", side_effect=TokenInvalidError("invalid")
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await validate_token("invalid-token")

        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.detail.lower()


# =============================================================================
# validate_token_optional Tests
# =============================================================================


class TestValidateTokenOptional:
    """Tests for validate_token_optional dependency."""

    async def test_returns_payload_for_valid_token(self):
        """Should return payload for valid token."""
        mock_payload = TokenPayload(
            sub="user-123",
            exp="2099-01-01T00:00:00",
            iat="2024-01-01T00:00:00",
            type="access",
            roles=["user"],
            permissions=[],
        )

        with patch("app.auth.oauth2.decode_token", return_value=mock_payload):
            result = await validate_token_optional("valid-token")

        assert result is not None
        assert result["sub"] == "user-123"

    async def test_returns_none_for_missing_token(self):
        """Should return None when token is missing."""
        result = await validate_token_optional(None)
        assert result is None

    async def test_returns_none_for_expired_token(self):
        """Should return None for expired token (no error)."""
        with patch(
            "app.auth.oauth2.decode_token", side_effect=TokenExpiredError("expired")
        ):
            result = await validate_token_optional("expired-token")

        assert result is None

    async def test_returns_none_for_invalid_token(self):
        """Should return None for invalid token (no error)."""
        with patch(
            "app.auth.oauth2.decode_token", side_effect=TokenInvalidError("invalid")
        ):
            result = await validate_token_optional("invalid-token")

        assert result is None


# =============================================================================
# validate_api_key Tests
# =============================================================================


class TestValidateApiKey:
    """Tests for validate_api_key dependency."""

    async def test_returns_key_for_valid_api_key(self, oauth2_settings):
        """Should return API key when valid."""
        with patch("app.auth.oauth2.get_settings", return_value=oauth2_settings):
            result = await validate_api_key("valid-api-key-123")

        assert result == "valid-api-key-123"

    async def test_returns_none_for_missing_key(self, oauth2_settings):
        """Should return None when API key is missing."""
        result = await validate_api_key(None)
        assert result is None

    async def test_raises_401_for_invalid_key(self, oauth2_settings):
        """Should raise 401 for invalid API key."""
        with (
            patch("app.auth.oauth2.get_settings", return_value=oauth2_settings),
            pytest.raises(HTTPException) as exc_info,
        ):
            await validate_api_key("invalid-api-key")

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail


# =============================================================================
# validate_token_or_api_key Tests
# =============================================================================


class TestValidateTokenOrApiKey:
    """Tests for validate_token_or_api_key dependency."""

    async def test_returns_token_payload_when_provided(self):
        """Should return token payload when JWT is provided."""
        token_payload = {
            "sub": "user-123",
            "type": "access",
            "roles": ["user"],
            "permissions": [],
        }

        result = await validate_token_or_api_key(
            token_payload=token_payload,
            api_key=None,
        )

        assert result == token_payload

    async def test_returns_synthetic_payload_for_api_key(self):
        """Should return synthetic payload when API key is provided."""
        result = await validate_token_or_api_key(
            token_payload=None,
            api_key="any-key-value",  # Value doesn't matter for this test
        )

        assert result["sub"].startswith("service:")
        assert result["type"] == "api_key"
        assert "service" in result["roles"]

    async def test_prefers_token_over_api_key(self):
        """Should prefer JWT token when both are provided."""
        token_payload = {
            "sub": "user-123",
            "type": "access",
            "roles": ["user"],
            "permissions": [],
        }

        result = await validate_token_or_api_key(
            token_payload=token_payload,
            api_key="test-api-key",
        )

        # Should return token payload, not API key payload
        assert result["sub"] == "user-123"
        assert result["type"] == "access"

    async def test_raises_401_when_neither_provided(self):
        """Should raise 401 when neither token nor API key is provided."""
        with pytest.raises(HTTPException) as exc_info:
            await validate_token_or_api_key(
                token_payload=None,
                api_key=None,
            )

        assert exc_info.value.status_code == 401
        assert "Not authenticated" in exc_info.value.detail
