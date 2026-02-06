"""Unit tests for LocalJWTAuthProvider."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.auth.providers.exceptions import TokenExpiredError, TokenInvalidError
from app.auth.providers.local_jwt import LocalJWTAuthProvider


pytestmark = pytest.mark.unit


class TestLocalJWTAuthProvider:
    """Tests for LocalJWTAuthProvider."""

    @pytest.fixture
    def secret_key(self) -> str:
        """Return a test secret key."""
        return "test-secret-key-for-testing-only-32chars"

    @pytest.fixture
    def provider(self, secret_key: str) -> LocalJWTAuthProvider:
        """Create a LocalJWTAuthProvider instance."""
        return LocalJWTAuthProvider(
            secret_key=secret_key,
            algorithm="HS256",
        )

    @pytest.fixture
    def valid_token(self, secret_key: str) -> str:
        """Create a valid JWT token."""
        now = datetime.now(UTC)
        payload = {
            "sub": "test-user-123",
            "exp": now + timedelta(hours=1),
            "iat": now,
            "type": "access",
            "roles": ["user", "premium"],
            "permissions": ["recipe:read", "recipe:write"],
        }
        return jwt.encode(payload, secret_key, algorithm="HS256")

    @pytest.fixture
    def expired_token(self, secret_key: str) -> str:
        """Create an expired JWT token."""
        now = datetime.now(UTC)
        payload = {
            "sub": "test-user-123",
            "exp": now - timedelta(hours=1),  # Expired
            "iat": now - timedelta(hours=2),
            "type": "access",
        }
        return jwt.encode(payload, secret_key, algorithm="HS256")

    @pytest.mark.asyncio
    async def test_validates_valid_token(
        self, provider: LocalJWTAuthProvider, valid_token: str
    ) -> None:
        """Should return AuthResult for valid token."""
        result = await provider.validate_token(valid_token)

        assert result.user_id == "test-user-123"
        assert "user" in result.roles
        assert "premium" in result.roles
        assert "recipe:read" in result.permissions
        assert result.token_type == "access"

    @pytest.mark.asyncio
    async def test_raises_for_expired_token(
        self, provider: LocalJWTAuthProvider, expired_token: str
    ) -> None:
        """Should raise TokenExpiredError for expired token."""
        with pytest.raises(TokenExpiredError):
            await provider.validate_token(expired_token)

    @pytest.mark.asyncio
    async def test_raises_for_invalid_signature(
        self, provider: LocalJWTAuthProvider
    ) -> None:
        """Should raise TokenInvalidError for token with wrong signature."""
        # Create token with different secret
        now = datetime.now(UTC)
        payload = {
            "sub": "test-user",
            "exp": now + timedelta(hours=1),
            "iat": now,
            "type": "access",
        }
        token = jwt.encode(payload, "wrong-secret", algorithm="HS256")

        with pytest.raises(TokenInvalidError):
            await provider.validate_token(token)

    @pytest.mark.asyncio
    async def test_raises_for_malformed_token(
        self, provider: LocalJWTAuthProvider
    ) -> None:
        """Should raise TokenInvalidError for malformed token."""
        with pytest.raises(TokenInvalidError):
            await provider.validate_token("not.a.valid.jwt")

    @pytest.mark.asyncio
    async def test_raises_for_missing_subject(
        self, secret_key: str, provider: LocalJWTAuthProvider
    ) -> None:
        """Should raise TokenInvalidError if token has no subject."""
        now = datetime.now(UTC)
        payload = {
            "exp": now + timedelta(hours=1),
            "iat": now,
            "type": "access",
            # No "sub" claim
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")

        with pytest.raises(TokenInvalidError, match="missing 'sub'"):
            await provider.validate_token(token)

    @pytest.mark.asyncio
    async def test_raises_for_invalid_token_type(
        self, secret_key: str, provider: LocalJWTAuthProvider
    ) -> None:
        """Should raise TokenInvalidError for refresh token."""
        now = datetime.now(UTC)
        payload = {
            "sub": "test-user",
            "exp": now + timedelta(hours=1),
            "iat": now,
            "type": "refresh",  # Not access type
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")

        with pytest.raises(TokenInvalidError, match="Invalid token type"):
            await provider.validate_token(token)

    @pytest.mark.asyncio
    async def test_validates_issuer(self, secret_key: str) -> None:
        """Should validate issuer claim when configured."""
        provider = LocalJWTAuthProvider(
            secret_key=secret_key,
            algorithm="HS256",
            issuer="https://auth.example.com",
        )

        now = datetime.now(UTC)
        payload = {
            "sub": "test-user",
            "exp": now + timedelta(hours=1),
            "iat": now,
            "type": "access",
            "iss": "https://auth.example.com",
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")

        result = await provider.validate_token(token)
        assert result.user_id == "test-user"
        assert result.issuer == "https://auth.example.com"

    @pytest.mark.asyncio
    async def test_rejects_wrong_issuer(self, secret_key: str) -> None:
        """Should reject token with wrong issuer."""
        provider = LocalJWTAuthProvider(
            secret_key=secret_key,
            algorithm="HS256",
            issuer="https://auth.example.com",
        )

        now = datetime.now(UTC)
        payload = {
            "sub": "test-user",
            "exp": now + timedelta(hours=1),
            "iat": now,
            "type": "access",
            "iss": "https://wrong.issuer.com",
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")

        with pytest.raises(TokenInvalidError):
            await provider.validate_token(token)

    @pytest.mark.asyncio
    async def test_provider_name(self, provider: LocalJWTAuthProvider) -> None:
        """Should return correct provider name."""
        assert provider.provider_name == "local_jwt"

    @pytest.mark.asyncio
    async def test_initialize(self, provider: LocalJWTAuthProvider) -> None:
        """Should initialize without error."""
        await provider.initialize()
        assert provider._initialized is True

    @pytest.mark.asyncio
    async def test_shutdown(self, provider: LocalJWTAuthProvider) -> None:
        """Should shutdown without error."""
        await provider.initialize()
        await provider.shutdown()
        assert provider._initialized is False

    @pytest.mark.asyncio
    async def test_parses_scopes_from_token(self, secret_key: str) -> None:
        """Should parse scope claim into scopes list."""
        provider = LocalJWTAuthProvider(secret_key=secret_key)

        now = datetime.now(UTC)
        payload = {
            "sub": "test-user",
            "exp": now + timedelta(hours=1),
            "iat": now,
            "type": "access",
            "scope": "read write admin",
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")

        result = await provider.validate_token(token)
        assert result.scopes == ["read", "write", "admin"]

    @pytest.mark.asyncio
    async def test_default_roles_when_missing(
        self, secret_key: str, provider: LocalJWTAuthProvider
    ) -> None:
        """Should return empty roles when not in token."""
        now = datetime.now(UTC)
        payload = {
            "sub": "test-user",
            "exp": now + timedelta(hours=1),
            "iat": now,
            "type": "access",
            # No roles
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")

        result = await provider.validate_token(token)
        assert result.roles == []

    @pytest.mark.asyncio
    async def test_parses_string_audience_from_token(self, secret_key: str) -> None:
        """Should parse audience as string and convert to list."""
        # Provider without audience validation - tests the parsing of aud from payload
        provider = LocalJWTAuthProvider(
            secret_key=secret_key,
            algorithm="HS256",
        )

        now = datetime.now(UTC)
        payload = {
            "sub": "test-user",
            "exp": now + timedelta(hours=1),
            "iat": now,
            "type": "access",
            # No aud - tests the else branch (aud is None, audience_list stays [])
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")

        result = await provider.validate_token(token)
        assert result.user_id == "test-user"
        assert result.audience == []

    @pytest.mark.asyncio
    async def test_handles_single_audience_in_token(self, secret_key: str) -> None:
        """Should handle single audience string in token payload."""
        from unittest.mock import patch

        provider = LocalJWTAuthProvider(
            secret_key=secret_key,
            algorithm="HS256",
        )

        now = datetime.now(UTC)
        # Mock jwt.decode to return a payload with string aud
        mock_payload = {
            "sub": "test-user",
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "type": "access",
            "aud": "api-service",
        }

        with patch(
            "app.auth.providers.local_jwt.jwt.decode", return_value=mock_payload
        ):
            result = await provider.validate_token("mock-token")

        assert result.user_id == "test-user"
        assert result.audience == ["api-service"]

    @pytest.mark.asyncio
    async def test_handles_list_audience_in_token(self, secret_key: str) -> None:
        """Should handle list audience in token payload."""
        from unittest.mock import patch

        provider = LocalJWTAuthProvider(
            secret_key=secret_key,
            algorithm="HS256",
        )

        now = datetime.now(UTC)
        # Mock jwt.decode to return a payload with list aud
        mock_payload = {
            "sub": "test-user",
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "type": "access",
            "aud": ["api-service", "web-app"],
        }

        with patch(
            "app.auth.providers.local_jwt.jwt.decode", return_value=mock_payload
        ):
            result = await provider.validate_token("mock-token")

        assert result.user_id == "test-user"
        assert result.audience == ["api-service", "web-app"]

    @pytest.mark.asyncio
    async def test_initialize_raises_without_secret(self) -> None:
        """Should raise TokenInvalidError when secret key is empty."""
        provider = LocalJWTAuthProvider(
            secret_key="",
            algorithm="HS256",
        )

        with pytest.raises(TokenInvalidError, match="JWT secret key is not configured"):
            await provider.initialize()

    @pytest.mark.asyncio
    async def test_accepts_api_key_token_type(self, secret_key: str) -> None:
        """Should accept 'api_key' as a valid token type."""
        provider = LocalJWTAuthProvider(secret_key=secret_key)

        now = datetime.now(UTC)
        payload = {
            "sub": "api-client-123",
            "exp": now + timedelta(hours=1),
            "iat": now,
            "type": "api_key",
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")

        result = await provider.validate_token(token)
        assert result.user_id == "api-client-123"
        assert result.token_type == "api_key"

    @pytest.mark.asyncio
    async def test_defaults_to_access_token_type(self, secret_key: str) -> None:
        """Should default to 'access' token type when not specified."""
        provider = LocalJWTAuthProvider(secret_key=secret_key)

        now = datetime.now(UTC)
        payload = {
            "sub": "test-user",
            "exp": now + timedelta(hours=1),
            "iat": now,
            # No "type" claim
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")

        result = await provider.validate_token(token)
        assert result.token_type == "access"

    @pytest.mark.asyncio
    async def test_passes_audience_to_jwt_decode(self, secret_key: str) -> None:
        """Should pass audience to jwt.decode when configured."""
        from unittest.mock import patch

        provider = LocalJWTAuthProvider(
            secret_key=secret_key,
            algorithm="HS256",
            audience=["api-service"],
        )

        now = datetime.now(UTC)
        mock_payload = {
            "sub": "test-user",
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "type": "access",
            "aud": "api-service",
        }

        with patch(
            "app.auth.providers.local_jwt.jwt.decode", return_value=mock_payload
        ) as mock_decode:
            result = await provider.validate_token("mock-token")

            # Verify that audience was passed to jwt.decode
            mock_decode.assert_called_once()
            call_kwargs = mock_decode.call_args.kwargs
            assert call_kwargs.get("audience") == ["api-service"]

        assert result.user_id == "test-user"
