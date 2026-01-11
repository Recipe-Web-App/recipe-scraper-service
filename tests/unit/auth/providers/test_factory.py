"""Unit tests for auth provider factory."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.auth.providers.exceptions import ConfigurationError
from app.auth.providers.factory import (
    DisabledAuthProvider,
    _state,
    create_auth_provider,
    get_auth_provider,
    set_auth_provider,
)
from app.auth.providers.header import HeaderAuthProvider
from app.auth.providers.introspection import IntrospectionAuthProvider
from app.auth.providers.local_jwt import LocalJWTAuthProvider
from app.core.config import AuthMode


class TestCreateAuthProvider:
    """Tests for create_auth_provider factory function."""

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        """Create mock settings with defaults."""
        settings = MagicMock()
        settings.AUTH_MODE = "local_jwt"
        settings.auth_mode_enum = AuthMode.LOCAL_JWT
        settings.JWT_SECRET_KEY = "test-secret-key-for-testing-32chars"
        settings.JWT_ALGORITHM = "HS256"
        settings.AUTH_JWT_ISSUER = None
        settings.AUTH_JWT_AUDIENCE = []
        settings.AUTH_HEADER_USER_ID = "X-User-ID"
        settings.AUTH_HEADER_ROLES = "X-User-Roles"
        settings.AUTH_HEADER_PERMISSIONS = "X-User-Permissions"
        return settings

    def test_creates_local_jwt_provider(self, mock_settings: MagicMock) -> None:
        """Should create LocalJWTAuthProvider for local_jwt mode."""
        mock_settings.auth_mode_enum = AuthMode.LOCAL_JWT

        provider = create_auth_provider(settings=mock_settings)

        assert isinstance(provider, LocalJWTAuthProvider)

    def test_creates_header_provider(self, mock_settings: MagicMock) -> None:
        """Should create HeaderAuthProvider for header mode."""
        mock_settings.auth_mode_enum = AuthMode.HEADER

        provider = create_auth_provider(settings=mock_settings)

        assert isinstance(provider, HeaderAuthProvider)

    def test_creates_disabled_provider(self, mock_settings: MagicMock) -> None:
        """Should create DisabledAuthProvider for disabled mode."""
        mock_settings.auth_mode_enum = AuthMode.DISABLED

        provider = create_auth_provider(settings=mock_settings)

        assert isinstance(provider, DisabledAuthProvider)

    def test_creates_introspection_provider(self, mock_settings: MagicMock) -> None:
        """Should create IntrospectionAuthProvider for introspection mode."""
        mock_settings.auth_mode_enum = AuthMode.INTROSPECTION
        mock_settings.AUTH_SERVICE_URL = "http://auth:8080"
        mock_settings.AUTH_SERVICE_CLIENT_ID = "client-id"
        mock_settings.AUTH_SERVICE_CLIENT_SECRET = "client-secret"
        mock_settings.AUTH_INTROSPECTION_TIMEOUT = 5.0
        mock_settings.AUTH_INTROSPECTION_CACHE_TTL = 60
        mock_settings.AUTH_INTROSPECTION_FALLBACK_LOCAL = False

        provider = create_auth_provider(settings=mock_settings)

        assert isinstance(provider, IntrospectionAuthProvider)

    def test_introspection_requires_url(self, mock_settings: MagicMock) -> None:
        """Should raise ConfigurationError if AUTH_SERVICE_URL is missing."""
        mock_settings.auth_mode_enum = AuthMode.INTROSPECTION
        mock_settings.AUTH_SERVICE_URL = None
        mock_settings.AUTH_SERVICE_CLIENT_ID = "client-id"
        mock_settings.AUTH_SERVICE_CLIENT_SECRET = "client-secret"

        with pytest.raises(ConfigurationError, match="AUTH_SERVICE_URL"):
            create_auth_provider(settings=mock_settings)

    def test_introspection_requires_client_id(self, mock_settings: MagicMock) -> None:
        """Should raise ConfigurationError if AUTH_SERVICE_CLIENT_ID is missing."""
        mock_settings.auth_mode_enum = AuthMode.INTROSPECTION
        mock_settings.AUTH_SERVICE_URL = "http://auth:8080"
        mock_settings.AUTH_SERVICE_CLIENT_ID = None
        mock_settings.AUTH_SERVICE_CLIENT_SECRET = "client-secret"

        with pytest.raises(ConfigurationError, match="AUTH_SERVICE_CLIENT_ID"):
            create_auth_provider(settings=mock_settings)

    def test_introspection_requires_client_secret(
        self, mock_settings: MagicMock
    ) -> None:
        """Should raise ConfigurationError if AUTH_SERVICE_CLIENT_SECRET is missing."""
        mock_settings.auth_mode_enum = AuthMode.INTROSPECTION
        mock_settings.AUTH_SERVICE_URL = "http://auth:8080"
        mock_settings.AUTH_SERVICE_CLIENT_ID = "client-id"
        mock_settings.AUTH_SERVICE_CLIENT_SECRET = None

        with pytest.raises(ConfigurationError, match="AUTH_SERVICE_CLIENT_SECRET"):
            create_auth_provider(settings=mock_settings)

    def test_introspection_with_fallback(self, mock_settings: MagicMock) -> None:
        """Should create IntrospectionAuthProvider with fallback when configured."""
        mock_settings.auth_mode_enum = AuthMode.INTROSPECTION
        mock_settings.AUTH_SERVICE_URL = "http://auth:8080"
        mock_settings.AUTH_SERVICE_CLIENT_ID = "client-id"
        mock_settings.AUTH_SERVICE_CLIENT_SECRET = "client-secret"
        mock_settings.AUTH_INTROSPECTION_TIMEOUT = 5.0
        mock_settings.AUTH_INTROSPECTION_CACHE_TTL = 60
        mock_settings.AUTH_INTROSPECTION_FALLBACK_LOCAL = True

        provider = create_auth_provider(settings=mock_settings)

        assert isinstance(provider, IntrospectionAuthProvider)
        assert provider.fallback_provider is not None
        assert isinstance(provider.fallback_provider, LocalJWTAuthProvider)

    def test_local_jwt_with_issuer(self, mock_settings: MagicMock) -> None:
        """Should configure LocalJWTAuthProvider with issuer."""
        mock_settings.auth_mode_enum = AuthMode.LOCAL_JWT
        mock_settings.AUTH_JWT_ISSUER = "https://auth.example.com"

        provider = create_auth_provider(settings=mock_settings)

        assert isinstance(provider, LocalJWTAuthProvider)
        assert provider.issuer == "https://auth.example.com"

    def test_local_jwt_with_audience(self, mock_settings: MagicMock) -> None:
        """Should configure LocalJWTAuthProvider with audience."""
        mock_settings.auth_mode_enum = AuthMode.LOCAL_JWT
        mock_settings.AUTH_JWT_AUDIENCE = ["api", "web"]

        provider = create_auth_provider(settings=mock_settings)

        assert isinstance(provider, LocalJWTAuthProvider)
        assert provider.audience == ["api", "web"]

    def test_header_provider_with_custom_headers(
        self, mock_settings: MagicMock
    ) -> None:
        """Should configure HeaderAuthProvider with custom header names."""
        mock_settings.auth_mode_enum = AuthMode.HEADER
        mock_settings.AUTH_HEADER_USER_ID = "X-Custom-User"
        mock_settings.AUTH_HEADER_ROLES = "X-Custom-Roles"
        mock_settings.AUTH_HEADER_PERMISSIONS = "X-Custom-Perms"

        provider = create_auth_provider(settings=mock_settings)

        assert isinstance(provider, HeaderAuthProvider)
        assert provider.user_id_header == "X-Custom-User"
        assert provider.roles_header == "X-Custom-Roles"
        assert provider.permissions_header == "X-Custom-Perms"


class TestDisabledAuthProvider:
    """Tests for DisabledAuthProvider."""

    @pytest.fixture
    def provider(self) -> DisabledAuthProvider:
        """Create a DisabledAuthProvider instance."""
        return DisabledAuthProvider()

    @pytest.mark.asyncio
    async def test_returns_anonymous_user(self, provider: DisabledAuthProvider) -> None:
        """Should return anonymous user result."""
        result = await provider.validate_token("any-token")

        assert result.user_id == "anonymous"
        assert "anonymous" in result.roles
        assert result.raw_claims.get("auth_disabled") is True

    @pytest.mark.asyncio
    async def test_provider_name(self, provider: DisabledAuthProvider) -> None:
        """Should return correct provider name."""
        assert provider.provider_name == "disabled"

    @pytest.mark.asyncio
    async def test_initialize(self, provider: DisabledAuthProvider) -> None:
        """Should initialize without error."""
        await provider.initialize()  # Should not raise

    @pytest.mark.asyncio
    async def test_shutdown(self, provider: DisabledAuthProvider) -> None:
        """Should shutdown without error."""
        await provider.shutdown()  # Should not raise


class TestGlobalProvider:
    """Tests for global provider management functions."""

    def teardown_method(self) -> None:
        """Reset global provider after each test."""
        _state["provider"] = None

    def test_get_provider_raises_when_not_set(self) -> None:
        """Should raise RuntimeError when provider not initialized."""
        with pytest.raises(RuntimeError, match="not initialized"):
            get_auth_provider()

    def test_set_and_get_provider(self) -> None:
        """Should be able to set and get provider."""
        provider = LocalJWTAuthProvider(secret_key="test")
        set_auth_provider(provider)

        retrieved = get_auth_provider()

        assert retrieved is provider

    def test_set_provider_replaces_existing(self) -> None:
        """Should replace existing provider when set again."""
        provider1 = LocalJWTAuthProvider(secret_key="test1")
        provider2 = LocalJWTAuthProvider(secret_key="test2")

        set_auth_provider(provider1)
        set_auth_provider(provider2)

        retrieved = get_auth_provider()

        assert retrieved is provider2
