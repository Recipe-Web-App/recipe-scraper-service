"""Unit tests for auth provider factory."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.auth.providers.exceptions import ConfigurationError
from app.auth.providers.factory import (
    DisabledAuthProvider,
    _get_jwt_secret,
    _state,
    create_auth_provider,
    get_auth_provider,
    initialize_auth_provider,
    set_auth_provider,
    shutdown_auth_provider,
)
from app.auth.providers.header import HeaderAuthProvider
from app.auth.providers.introspection import IntrospectionAuthProvider
from app.auth.providers.local_jwt import LocalJWTAuthProvider
from app.core.config import AuthMode


pytestmark = pytest.mark.unit


class TestCreateAuthProvider:
    """Tests for create_auth_provider factory function."""

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        """Create mock settings with defaults."""
        settings = MagicMock()
        settings.auth_mode_enum = AuthMode.LOCAL_JWT
        settings.JWT_SECRET_KEY = "test-secret-key-for-testing-32chars"
        settings.is_production = False
        # Nested auth settings
        settings.auth.jwt.algorithm = "HS256"
        settings.auth.jwt_validation.issuer = None
        settings.auth.jwt_validation.audience = []
        settings.auth.headers.user_id = "X-User-ID"
        settings.auth.headers.roles = "X-User-Roles"
        settings.auth.headers.permissions = "X-User-Permissions"
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
        mock_settings.auth.service.url = "http://auth:8080"
        mock_settings.auth.service.client_id = "client-id"
        mock_settings.AUTH_SERVICE_CLIENT_SECRET = "client-secret"
        mock_settings.auth.introspection.timeout = 5.0
        mock_settings.auth.introspection.cache_ttl = 60
        mock_settings.auth.introspection.fallback_local = False

        provider = create_auth_provider(settings=mock_settings)

        assert isinstance(provider, IntrospectionAuthProvider)

    def test_introspection_requires_url(self, mock_settings: MagicMock) -> None:
        """Should raise ConfigurationError if auth.service.url is missing."""
        mock_settings.auth_mode_enum = AuthMode.INTROSPECTION
        mock_settings.auth.service.url = None
        mock_settings.auth.service.client_id = "client-id"
        mock_settings.AUTH_SERVICE_CLIENT_SECRET = "client-secret"

        with pytest.raises(ConfigurationError, match=r"auth\.service\.url"):
            create_auth_provider(settings=mock_settings)

    def test_introspection_requires_client_id(self, mock_settings: MagicMock) -> None:
        """Should raise ConfigurationError if auth.service.client_id is missing."""
        mock_settings.auth_mode_enum = AuthMode.INTROSPECTION
        mock_settings.auth.service.url = "http://auth:8080"
        mock_settings.auth.service.client_id = None
        mock_settings.AUTH_SERVICE_CLIENT_SECRET = "client-secret"

        with pytest.raises(ConfigurationError, match=r"auth\.service\.client_id"):
            create_auth_provider(settings=mock_settings)

    def test_introspection_requires_client_secret(
        self, mock_settings: MagicMock
    ) -> None:
        """Should raise ConfigurationError if AUTH_SERVICE_CLIENT_SECRET is missing."""
        mock_settings.auth_mode_enum = AuthMode.INTROSPECTION
        mock_settings.auth.service.url = "http://auth:8080"
        mock_settings.auth.service.client_id = "client-id"
        mock_settings.AUTH_SERVICE_CLIENT_SECRET = None

        with pytest.raises(ConfigurationError, match="AUTH_SERVICE_CLIENT_SECRET"):
            create_auth_provider(settings=mock_settings)

    def test_introspection_with_fallback(self, mock_settings: MagicMock) -> None:
        """Should create IntrospectionAuthProvider with fallback when configured."""
        mock_settings.auth_mode_enum = AuthMode.INTROSPECTION
        mock_settings.auth.service.url = "http://auth:8080"
        mock_settings.auth.service.client_id = "client-id"
        mock_settings.AUTH_SERVICE_CLIENT_SECRET = "client-secret"
        mock_settings.auth.introspection.timeout = 5.0
        mock_settings.auth.introspection.cache_ttl = 60
        mock_settings.auth.introspection.fallback_local = True

        provider = create_auth_provider(settings=mock_settings)

        assert isinstance(provider, IntrospectionAuthProvider)
        assert provider.fallback_provider is not None
        assert isinstance(provider.fallback_provider, LocalJWTAuthProvider)

    def test_local_jwt_with_issuer(self, mock_settings: MagicMock) -> None:
        """Should configure LocalJWTAuthProvider with issuer."""
        mock_settings.auth_mode_enum = AuthMode.LOCAL_JWT
        mock_settings.auth.jwt_validation.issuer = "https://auth.example.com"

        provider = create_auth_provider(settings=mock_settings)

        assert isinstance(provider, LocalJWTAuthProvider)
        assert provider.issuer == "https://auth.example.com"

    def test_local_jwt_with_audience(self, mock_settings: MagicMock) -> None:
        """Should configure LocalJWTAuthProvider with audience."""
        mock_settings.auth_mode_enum = AuthMode.LOCAL_JWT
        mock_settings.auth.jwt_validation.audience = ["api", "web"]

        provider = create_auth_provider(settings=mock_settings)

        assert isinstance(provider, LocalJWTAuthProvider)
        assert provider.audience == ["api", "web"]

    def test_header_provider_with_custom_headers(
        self, mock_settings: MagicMock
    ) -> None:
        """Should configure HeaderAuthProvider with custom header names."""
        mock_settings.auth_mode_enum = AuthMode.HEADER
        mock_settings.auth.headers.user_id = "X-Custom-User"
        mock_settings.auth.headers.roles = "X-Custom-Roles"
        mock_settings.auth.headers.permissions = "X-Custom-Perms"

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


class TestGetJwtSecret:
    """Tests for _get_jwt_secret helper function."""

    def test_returns_configured_secret(self) -> None:
        """Should return JWT_SECRET_KEY when configured."""
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "my-configured-secret"
        mock_settings.is_production = False

        result = _get_jwt_secret(mock_settings)

        assert result == "my-configured-secret"

    def test_raises_in_production_without_secret(self) -> None:
        """Should raise ConfigurationError in production without secret."""
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = None
        mock_settings.is_production = True

        with pytest.raises(ConfigurationError, match="JWT_SECRET_KEY must be set"):
            _get_jwt_secret(mock_settings)

    def test_returns_dev_secret_in_development(self) -> None:
        """Should return dev secret in development without configured secret."""
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = None
        mock_settings.is_production = False

        result = _get_jwt_secret(mock_settings)

        assert result is not None
        assert len(result) > 0


class TestInitializeAuthProvider:
    """Tests for initialize_auth_provider function."""

    def teardown_method(self) -> None:
        """Reset global provider after each test."""
        _state["provider"] = None

    @pytest.mark.asyncio
    async def test_creates_and_initializes_provider(self) -> None:
        """Should create, initialize, and set provider."""
        from unittest.mock import AsyncMock, patch

        mock_provider = AsyncMock()
        mock_provider.provider_name = "mock"

        with patch(
            "app.auth.providers.factory.create_auth_provider",
            return_value=mock_provider,
        ):
            result = await initialize_auth_provider()

            mock_provider.initialize.assert_called_once()
            assert result is mock_provider
            assert _state["provider"] is mock_provider


class TestShutdownAuthProvider:
    """Tests for shutdown_auth_provider function."""

    def teardown_method(self) -> None:
        """Reset global provider after each test."""
        _state["provider"] = None

    @pytest.mark.asyncio
    async def test_shuts_down_existing_provider(self) -> None:
        """Should call shutdown and clear state."""
        from unittest.mock import AsyncMock

        mock_provider = AsyncMock()
        _state["provider"] = mock_provider

        await shutdown_auth_provider()

        mock_provider.shutdown.assert_called_once()
        assert _state["provider"] is None

    @pytest.mark.asyncio
    async def test_handles_no_provider(self) -> None:
        """Should handle case when no provider is set."""
        _state["provider"] = None

        # Should not raise
        await shutdown_auth_provider()

        assert _state["provider"] is None


class TestCreateAuthProviderWithDefaultSettings:
    """Tests for create_auth_provider with default settings."""

    def test_uses_get_settings_when_none_provided(self) -> None:
        """Should use get_settings() when settings is None."""
        from unittest.mock import patch

        mock_settings = MagicMock()
        mock_settings.auth_mode_enum = AuthMode.DISABLED

        with patch(
            "app.auth.providers.factory.get_settings",
            return_value=mock_settings,
        ):
            provider = create_auth_provider(settings=None)

            assert isinstance(provider, DisabledAuthProvider)

    def test_raises_for_unknown_auth_mode(self) -> None:
        """Should raise ConfigurationError for unknown auth mode."""

        mock_settings = MagicMock()
        # Create a mock enum value that doesn't match any known mode
        unknown_mode = MagicMock()
        unknown_mode.value = "unknown"
        mock_settings.auth_mode_enum = unknown_mode

        with pytest.raises(ConfigurationError, match="Unknown auth mode"):
            create_auth_provider(settings=mock_settings)
