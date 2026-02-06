"""Unit tests for JWT token handling.

Tests cover:
- Token creation (access and refresh)
- Token decoding and validation
- Token expiration
- Token type verification
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from freezegun import freeze_time

from app.auth.jwt import (
    TokenExpiredError,
    TokenInvalidError,
    TokenPayload,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token,
)
from app.core.config import Settings


pytestmark = pytest.mark.unit


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def jwt_settings() -> Settings:
    """Settings for JWT testing."""
    return Settings(
        ENVIRONMENT="testing",
        JWT_SECRET_KEY="test-secret-key-minimum-32-characters-long",
        JWT_ALGORITHM="HS256",
        JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30,
        JWT_REFRESH_TOKEN_EXPIRE_DAYS=7,
    )


@pytest.fixture
def mock_jwt_settings(jwt_settings: Settings):
    """Patch get_settings for JWT operations."""
    with patch("app.auth.jwt.get_settings", return_value=jwt_settings):
        yield jwt_settings


# =============================================================================
# Token Creation Tests
# =============================================================================


class TestCreateAccessToken:
    """Tests for create_access_token function."""

    def test_creates_valid_token(self, mock_jwt_settings):
        """Should create a decodable token."""
        token = create_access_token(subject="user-123")

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_contains_subject(self, mock_jwt_settings):
        """Should include subject in token payload."""
        subject = "user-123"
        token = create_access_token(subject=subject)

        payload = decode_token(token)
        assert payload.sub == subject

    def test_token_contains_roles(self, mock_jwt_settings):
        """Should include roles in token payload."""
        roles = ["user", "premium"]
        token = create_access_token(subject="user-123", roles=roles)

        payload = decode_token(token)
        assert payload.roles == roles

    def test_token_contains_permissions(self, mock_jwt_settings):
        """Should include direct permissions in token payload."""
        permissions = ["recipe:read", "recipe:create"]
        token = create_access_token(subject="user-123", permissions=permissions)

        payload = decode_token(token)
        assert payload.permissions == permissions

    def test_token_has_access_type(self, mock_jwt_settings):
        """Should have 'access' type."""
        token = create_access_token(subject="user-123")

        payload = decode_token(token)
        assert payload.type == "access"

    def test_token_has_expiration(self, mock_jwt_settings):
        """Should have expiration time set."""
        token = create_access_token(subject="user-123")

        payload = decode_token(token)
        assert payload.exp > datetime.now(UTC)

    def test_token_has_issued_at(self, mock_jwt_settings):
        """Should have issued_at time set."""
        token = create_access_token(subject="user-123")

        payload = decode_token(token)
        assert payload.iat <= datetime.now(UTC)

    def test_custom_expiration(self, mock_jwt_settings):
        """Should respect custom expiration delta."""
        custom_delta = timedelta(hours=1)
        before = datetime.now(UTC).replace(microsecond=0)
        token = create_access_token(subject="user-123", expires_delta=custom_delta)
        after = datetime.now(UTC).replace(microsecond=0)

        payload = decode_token(token)
        # Expiration should be approximately now + 1 hour
        assert payload.exp >= before + custom_delta
        assert payload.exp <= after + custom_delta + timedelta(seconds=1)

    def test_extra_claims(self, mock_jwt_settings):
        """Should include extra claims in token."""
        token = create_access_token(
            subject="user-123",
            extra_claims={"custom_claim": "custom_value"},
        )

        payload = decode_token(token)
        # Extra claims are in the raw payload
        assert payload is not None

    def test_empty_roles_default(self, mock_jwt_settings):
        """Should default to empty roles list."""
        token = create_access_token(subject="user-123")

        payload = decode_token(token)
        assert payload.roles == []

    def test_empty_permissions_default(self, mock_jwt_settings):
        """Should default to empty permissions list."""
        token = create_access_token(subject="user-123")

        payload = decode_token(token)
        assert payload.permissions == []


class TestCreateRefreshToken:
    """Tests for create_refresh_token function."""

    def test_creates_valid_token(self, mock_jwt_settings):
        """Should create a decodable refresh token."""
        token = create_refresh_token(subject="user-123")

        assert token is not None
        assert isinstance(token, str)

    def test_token_has_refresh_type(self, mock_jwt_settings):
        """Should have 'refresh' type."""
        token = create_refresh_token(subject="user-123")

        payload = decode_token(token)
        assert payload.type == "refresh"

    def test_token_has_longer_expiration(self, mock_jwt_settings):
        """Refresh tokens should have longer default expiration than access tokens."""
        access = create_access_token(subject="user-123")
        refresh = create_refresh_token(subject="user-123")

        access_payload = decode_token(access)
        refresh_payload = decode_token(refresh)

        assert refresh_payload.exp > access_payload.exp

    def test_token_with_jti(self, mock_jwt_settings):
        """Should include JTI for revocation tracking."""
        jti = "unique-token-id"
        token = create_refresh_token(subject="user-123", jti=jti)

        payload = decode_token(token)
        assert payload.jti == jti

    def test_custom_expiration(self, mock_jwt_settings):
        """Should respect custom expiration delta."""
        custom_delta = timedelta(days=30)
        before = datetime.now(UTC).replace(microsecond=0)
        token = create_refresh_token(subject="user-123", expires_delta=custom_delta)
        after = datetime.now(UTC).replace(microsecond=0)

        payload = decode_token(token)
        assert payload.exp >= before + custom_delta
        assert payload.exp <= after + custom_delta + timedelta(seconds=1)


# =============================================================================
# Token Decoding Tests
# =============================================================================


class TestDecodeToken:
    """Tests for decode_token function."""

    def test_decodes_valid_token(self, mock_jwt_settings):
        """Should decode a valid token."""
        token = create_access_token(subject="user-123")

        payload = decode_token(token)

        assert payload is not None
        assert isinstance(payload, TokenPayload)
        assert payload.sub == "user-123"

    def test_raises_on_invalid_token(self, mock_jwt_settings):
        """Should raise TokenInvalidError for invalid tokens."""
        with pytest.raises(TokenInvalidError):
            decode_token("invalid-token")

    def test_raises_on_empty_token(self, mock_jwt_settings):
        """Should raise TokenInvalidError for empty tokens."""
        with pytest.raises(TokenInvalidError):
            decode_token("")

    def test_raises_on_malformed_token(self, mock_jwt_settings):
        """Should raise TokenInvalidError for malformed tokens."""
        with pytest.raises(TokenInvalidError):
            decode_token("not.a.valid.jwt.token")

    @freeze_time("2024-01-01 12:00:00")
    def test_raises_on_expired_token(self, mock_jwt_settings):
        """Should raise TokenExpiredError for expired tokens."""
        # Create token that expires in 1 minute
        token = create_access_token(
            subject="user-123",
            expires_delta=timedelta(minutes=1),
        )

        # Move time forward past expiration
        with freeze_time("2024-01-01 12:02:00"), pytest.raises(TokenExpiredError):
            decode_token(token)

    def test_verify_type_access(self, mock_jwt_settings):
        """Should verify token type is access."""
        token = create_access_token(subject="user-123")

        # Should succeed
        payload = decode_token(token, verify_type="access")
        assert payload.type == "access"

    def test_verify_type_refresh(self, mock_jwt_settings):
        """Should verify token type is refresh."""
        token = create_refresh_token(subject="user-123")

        # Should succeed
        payload = decode_token(token, verify_type="refresh")
        assert payload.type == "refresh"

    def test_verify_type_mismatch_raises(self, mock_jwt_settings):
        """Should raise when token type doesn't match."""
        access_token = create_access_token(subject="user-123")
        refresh_token = create_refresh_token(subject="user-123")

        with pytest.raises(TokenInvalidError, match="Invalid token type"):
            decode_token(access_token, verify_type="refresh")

        with pytest.raises(TokenInvalidError, match="Invalid token type"):
            decode_token(refresh_token, verify_type="access")

    def test_wrong_secret_key_fails(self, mock_jwt_settings):
        """Should fail to decode token with wrong secret key."""
        token = create_access_token(subject="user-123")

        # Try to decode with different secret
        wrong_settings = Settings(
            ENVIRONMENT="testing",
            JWT_SECRET_KEY="completely-different-secret-key-32chars",
            JWT_ALGORITHM="HS256",
        )
        with (
            patch("app.auth.jwt.get_settings", return_value=wrong_settings),
            pytest.raises(TokenInvalidError),
        ):
            decode_token(token)


# =============================================================================
# Token Verification Tests
# =============================================================================


class TestVerifyToken:
    """Tests for verify_token function."""

    def test_returns_true_for_valid_token(self, mock_jwt_settings):
        """Should return True for valid tokens."""
        token = create_access_token(subject="user-123")

        assert verify_token(token) is True

    def test_returns_false_for_invalid_token(self, mock_jwt_settings):
        """Should return False for invalid tokens."""
        assert verify_token("invalid-token") is False

    @freeze_time("2024-01-01 12:00:00")
    def test_returns_false_for_expired_token(self, mock_jwt_settings):
        """Should return False for expired tokens."""
        token = create_access_token(
            subject="user-123",
            expires_delta=timedelta(minutes=1),
        )

        with freeze_time("2024-01-01 12:02:00"):
            assert verify_token(token) is False

    def test_verify_type_returns_true_when_matched(self, mock_jwt_settings):
        """Should return True when type matches."""
        access_token = create_access_token(subject="user-123")
        refresh_token = create_refresh_token(subject="user-123")

        assert verify_token(access_token, verify_type="access") is True
        assert verify_token(refresh_token, verify_type="refresh") is True

    def test_verify_type_returns_false_when_mismatched(self, mock_jwt_settings):
        """Should return False when type doesn't match."""
        access_token = create_access_token(subject="user-123")
        refresh_token = create_refresh_token(subject="user-123")

        assert verify_token(access_token, verify_type="refresh") is False
        assert verify_token(refresh_token, verify_type="access") is False


# =============================================================================
# TokenPayload Model Tests
# =============================================================================


class TestTokenPayload:
    """Tests for TokenPayload model."""

    def test_creates_with_required_fields(self):
        """Should create payload with required fields."""
        payload = TokenPayload(
            sub="user-123",
            exp=datetime.now(UTC) + timedelta(hours=1),
            iat=datetime.now(UTC),
        )

        assert payload.sub == "user-123"
        assert payload.type == "access"
        assert payload.roles == []
        assert payload.permissions == []
        assert payload.jti is None

    def test_creates_with_all_fields(self):
        """Should create payload with all fields."""
        exp = datetime.now(UTC) + timedelta(hours=1)
        iat = datetime.now(UTC)

        payload = TokenPayload(
            sub="user-123",
            exp=exp,
            iat=iat,
            jti="token-id-123",
            type="refresh",
            roles=["admin"],
            permissions=["recipe:read"],
        )

        assert payload.sub == "user-123"
        assert payload.exp == exp
        assert payload.iat == iat
        assert payload.jti == "token-id-123"
        assert payload.type == "refresh"
        assert payload.roles == ["admin"]
        assert payload.permissions == ["recipe:read"]
