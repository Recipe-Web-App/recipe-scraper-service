"""Unit tests for IntrospectionAuthProvider.

Tests cover:
- Provider initialization and configuration
- Token validation via introspection
- Role and permission extraction from scopes
- Fallback provider handling
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.auth.providers.exceptions import (
    AuthServiceUnavailableError,
    ConfigurationError,
    TokenInvalidError,
)
from app.auth.providers.introspection import IntrospectionAuthProvider
from app.auth.providers.models import IntrospectionResponse


pytestmark = pytest.mark.unit


# =============================================================================
# Initialization Tests
# =============================================================================


class TestIntrospectionAuthProviderInit:
    """Tests for provider initialization."""

    def test_creates_with_valid_config(self) -> None:
        """Should create provider with valid configuration."""
        provider = IntrospectionAuthProvider(
            base_url="https://auth.example.com",
            client_id="test-client",
            client_secret="test-secret",
        )

        assert provider.auth_client is not None
        assert provider.provider_name == "introspection"

    def test_raises_on_missing_base_url(self) -> None:
        """Should raise ConfigurationError when base_url is empty."""
        with pytest.raises(ConfigurationError):
            IntrospectionAuthProvider(
                base_url="",
                client_id="test-client",
                client_secret="test-secret",
            )

    def test_raises_on_missing_client_id(self) -> None:
        """Should raise ConfigurationError when client_id is empty."""
        with pytest.raises(ConfigurationError):
            IntrospectionAuthProvider(
                base_url="https://auth.example.com",
                client_id="",
                client_secret="test-secret",
            )

    def test_raises_on_missing_client_secret(self) -> None:
        """Should raise ConfigurationError when client_secret is empty."""
        with pytest.raises(ConfigurationError):
            IntrospectionAuthProvider(
                base_url="https://auth.example.com",
                client_id="test-client",
                client_secret="",
            )

    def test_accepts_optional_parameters(self) -> None:
        """Should accept optional configuration parameters."""
        mock_redis = MagicMock()
        mock_fallback = MagicMock()

        provider = IntrospectionAuthProvider(
            base_url="https://auth.example.com",
            client_id="test-client",
            client_secret="test-secret",
            timeout=10.0,
            cache_client=mock_redis,
            cache_ttl=120,
            fallback_provider=mock_fallback,
        )

        assert provider.fallback_provider is mock_fallback


# =============================================================================
# Token Validation Tests
# =============================================================================


class TestIntrospectionAuthProviderValidateToken:
    """Tests for token validation."""

    @pytest.fixture
    def provider(self) -> IntrospectionAuthProvider:
        """Create a provider instance for testing."""
        return IntrospectionAuthProvider(
            base_url="https://auth.example.com",
            client_id="test-client",
            client_secret="test-secret",
        )

    async def test_validate_active_token(
        self, provider: IntrospectionAuthProvider
    ) -> None:
        """Should return AuthResult for active token."""
        mock_response = IntrospectionResponse(
            active=True,
            sub="user-123",
            scope="openid profile user",
            client_id="my-client",
            token_type="Bearer",
            exp=1234567890,
            iat=1234567800,
            iss="https://auth.example.com",
            aud="https://api.example.com",
        )

        with patch.object(
            provider.auth_client,
            "introspect_token",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await provider.validate_token("valid-token")

        assert result.user_id == "user-123"
        assert "user" in result.roles
        assert result.issuer == "https://auth.example.com"

    async def test_raises_on_inactive_token(
        self, provider: IntrospectionAuthProvider
    ) -> None:
        """Should raise TokenInvalidError for inactive token."""
        mock_response = IntrospectionResponse(active=False)

        with (
            patch.object(
                provider.auth_client,
                "introspect_token",
                new=AsyncMock(return_value=mock_response),
            ),
            pytest.raises(TokenInvalidError, match="not active"),
        ):
            await provider.validate_token("invalid-token")

    async def test_raises_on_missing_sub(
        self, provider: IntrospectionAuthProvider
    ) -> None:
        """Should raise TokenInvalidError when sub claim is missing."""
        mock_response = IntrospectionResponse(
            active=True,
            sub=None,
            scope="openid profile",
        )

        with (
            patch.object(
                provider.auth_client,
                "introspect_token",
                new=AsyncMock(return_value=mock_response),
            ),
            pytest.raises(TokenInvalidError, match="missing 'sub' claim"),
        ):
            await provider.validate_token("token-without-sub")

    async def test_uses_fallback_on_service_unavailable(self) -> None:
        """Should use fallback provider when auth service is unavailable."""
        mock_fallback = MagicMock()
        mock_fallback.provider_name = "local_jwt"
        mock_fallback.validate_token = AsyncMock(
            return_value=MagicMock(user_id="fallback-user")
        )

        provider = IntrospectionAuthProvider(
            base_url="https://auth.example.com",
            client_id="test-client",
            client_secret="test-secret",
            fallback_provider=mock_fallback,
        )

        with patch.object(
            provider.auth_client,
            "introspect_token",
            new=AsyncMock(side_effect=AuthServiceUnavailableError("Service down")),
        ):
            result = await provider.validate_token("some-token")

        assert result.user_id == "fallback-user"
        mock_fallback.validate_token.assert_called_once()

    async def test_raises_when_no_fallback(
        self, provider: IntrospectionAuthProvider
    ) -> None:
        """Should raise AuthServiceUnavailableError when no fallback configured."""
        with (
            patch.object(
                provider.auth_client,
                "introspect_token",
                new=AsyncMock(side_effect=AuthServiceUnavailableError("Service down")),
            ),
            pytest.raises(AuthServiceUnavailableError),
        ):
            await provider.validate_token("some-token")


# =============================================================================
# Role Extraction Tests
# =============================================================================


class TestExtractRoles:
    """Tests for _extract_roles method."""

    @pytest.fixture
    def provider(self) -> IntrospectionAuthProvider:
        """Create a provider instance for testing."""
        return IntrospectionAuthProvider(
            base_url="https://auth.example.com",
            client_id="test-client",
            client_secret="test-secret",
        )

    def test_extracts_known_roles(self, provider: IntrospectionAuthProvider) -> None:
        """Should extract known role names from scopes."""
        scopes = ["openid", "admin", "profile"]

        roles = provider._extract_roles(scopes)

        assert "admin" in roles

    def test_extracts_prefixed_roles(self, provider: IntrospectionAuthProvider) -> None:
        """Should extract roles with 'role:' prefix."""
        scopes = ["openid", "role:moderator", "profile"]

        roles = provider._extract_roles(scopes)

        assert "moderator" in roles

    def test_defaults_to_user_when_no_roles(
        self, provider: IntrospectionAuthProvider
    ) -> None:
        """Should default to 'user' role when no roles found."""
        scopes = ["openid", "profile", "email"]

        roles = provider._extract_roles(scopes)

        assert roles == ["user"]

    def test_handles_mixed_roles(self, provider: IntrospectionAuthProvider) -> None:
        """Should handle both known and prefixed roles."""
        scopes = ["admin", "role:custom", "user"]

        roles = provider._extract_roles(scopes)

        assert "admin" in roles
        assert "custom" in roles
        assert "user" in roles

    def test_handles_case_insensitivity(
        self, provider: IntrospectionAuthProvider
    ) -> None:
        """Should handle case-insensitive role matching."""
        scopes = ["ADMIN", "Role:Premium"]

        roles = provider._extract_roles(scopes)

        assert "admin" in roles
        assert "Premium" in roles  # Prefix stripped but rest preserved


# =============================================================================
# Permission Extraction Tests
# =============================================================================


class TestExtractPermissions:
    """Tests for _extract_permissions method."""

    @pytest.fixture
    def provider(self) -> IntrospectionAuthProvider:
        """Create a provider instance for testing."""
        return IntrospectionAuthProvider(
            base_url="https://auth.example.com",
            client_id="test-client",
            client_secret="test-secret",
        )

    def test_extracts_resource_permissions(
        self, provider: IntrospectionAuthProvider
    ) -> None:
        """Should extract resource:action format permissions."""
        scopes = ["recipe:read", "recipe:write", "openid"]

        permissions = provider._extract_permissions(scopes)

        assert "recipe:read" in permissions
        assert "recipe:write" in permissions
        assert "openid" not in permissions

    def test_excludes_role_prefixes(self, provider: IntrospectionAuthProvider) -> None:
        """Should exclude role: prefixed scopes from permissions."""
        scopes = ["role:admin", "recipe:read", "user:delete"]

        permissions = provider._extract_permissions(scopes)

        assert "role:admin" not in permissions
        assert "recipe:read" in permissions
        assert "user:delete" in permissions

    def test_returns_empty_for_simple_scopes(
        self, provider: IntrospectionAuthProvider
    ) -> None:
        """Should return empty list when no resource permissions."""
        scopes = ["openid", "profile", "email"]

        permissions = provider._extract_permissions(scopes)

        assert permissions == []

    def test_handles_multiple_colons(self, provider: IntrospectionAuthProvider) -> None:
        """Should include permissions with multiple colons."""
        scopes = ["api:recipe:read", "api:user:write"]

        permissions = provider._extract_permissions(scopes)

        assert "api:recipe:read" in permissions
        assert "api:user:write" in permissions


# =============================================================================
# Lifecycle Tests
# =============================================================================


class TestIntrospectionAuthProviderLifecycle:
    """Tests for provider lifecycle methods."""

    async def test_initialize_without_fallback(self) -> None:
        """Should initialize auth client only when no fallback."""
        provider = IntrospectionAuthProvider(
            base_url="https://auth.example.com",
            client_id="test-client",
            client_secret="test-secret",
        )

        with patch.object(
            provider.auth_client, "initialize", new=AsyncMock()
        ) as mock_init:
            await provider.initialize()

        mock_init.assert_called_once()
        assert provider._initialized is True

    async def test_initialize_with_fallback(self) -> None:
        """Should initialize both auth client and fallback provider."""
        mock_fallback = MagicMock()
        mock_fallback.provider_name = "local_jwt"
        mock_fallback.initialize = AsyncMock()

        provider = IntrospectionAuthProvider(
            base_url="https://auth.example.com",
            client_id="test-client",
            client_secret="test-secret",
            fallback_provider=mock_fallback,
        )

        with patch.object(provider.auth_client, "initialize", new=AsyncMock()):
            await provider.initialize()

        mock_fallback.initialize.assert_called_once()
        assert provider._initialized is True

    async def test_shutdown_without_fallback(self) -> None:
        """Should shutdown auth client only when no fallback."""
        provider = IntrospectionAuthProvider(
            base_url="https://auth.example.com",
            client_id="test-client",
            client_secret="test-secret",
        )
        provider._initialized = True

        with patch.object(
            provider.auth_client, "shutdown", new=AsyncMock()
        ) as mock_shutdown:
            await provider.shutdown()

        mock_shutdown.assert_called_once()
        assert provider._initialized is False

    async def test_shutdown_with_fallback(self) -> None:
        """Should shutdown both auth client and fallback provider."""
        mock_fallback = MagicMock()
        mock_fallback.shutdown = AsyncMock()

        provider = IntrospectionAuthProvider(
            base_url="https://auth.example.com",
            client_id="test-client",
            client_secret="test-secret",
            fallback_provider=mock_fallback,
        )
        provider._initialized = True

        with patch.object(provider.auth_client, "shutdown", new=AsyncMock()):
            await provider.shutdown()

        mock_fallback.shutdown.assert_called_once()
        assert provider._initialized is False
