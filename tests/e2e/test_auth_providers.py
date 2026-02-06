"""E2E tests for authentication providers.

Tests cover all three auth modes:
- Header mode: X-User-ID header authentication (development/testing)
- Local JWT mode: Local JWT validation with shared secret
- Introspection mode: External auth-service token introspection
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Annotated, Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.client.auth_service import AuthServiceClient
from app.auth.dependencies import CurrentUser, get_current_user
from app.auth.jwt import create_access_token
from app.auth.providers import (
    set_auth_provider,
    shutdown_auth_provider,
)
from app.auth.providers.exceptions import (
    AuthServiceUnavailableError,
    ConfigurationError,
)
from app.auth.providers.factory import create_auth_provider
from app.auth.providers.header import HeaderAuthProvider
from app.auth.providers.introspection import IntrospectionAuthProvider
from app.auth.providers.local_jwt import LocalJWTAuthProvider
from app.auth.providers.models import IntrospectionResponse
from app.core.config import Settings
from app.core.config.settings import (
    ApiSettings,
    AppSettings,
    AuthJwtValidationSettings,
    AuthServiceSettings,
    AuthSettings,
    JwtSettings,
    LoggingSettings,
    ObservabilitySettings,
    RateLimitingSettings,
    RedisSettings,
    ServerSettings,
)


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


pytestmark = pytest.mark.e2e


# =============================================================================
# Test App Factory
# =============================================================================


def create_test_app_with_protected_endpoint() -> FastAPI:
    """Create a minimal FastAPI app with a protected endpoint for testing."""
    app = FastAPI()

    @app.get("/protected")
    async def protected_endpoint(
        user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> dict[str, Any]:
        """Protected endpoint that requires authentication."""
        return {
            "user_id": user.id,
            "roles": user.roles,
            "permissions": user.permissions,
        }

    @app.get("/public")
    async def public_endpoint() -> dict[str, str]:
        """Public endpoint for comparison."""
        return {"message": "public"}

    return app


# =============================================================================
# Header Mode Tests
# =============================================================================


class TestHeaderAuthMode:
    """E2E tests for header-based authentication mode."""

    @pytest.fixture
    async def header_app(self) -> AsyncGenerator[FastAPI]:
        """Create app configured for header auth mode."""
        app = create_test_app_with_protected_endpoint()

        # Set up header auth provider
        provider = HeaderAuthProvider(
            user_id_header="X-User-ID",
            roles_header="X-User-Roles",
            permissions_header="X-User-Permissions",
        )
        await provider.initialize()
        set_auth_provider(provider)

        yield app

        await shutdown_auth_provider()

    @pytest.fixture
    async def header_client(self, header_app: FastAPI) -> AsyncGenerator[AsyncClient]:
        """Create async client for header auth mode."""
        async with AsyncClient(
            transport=ASGITransport(app=header_app),
            base_url="http://test",
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_header_auth_valid_user(self, header_client: AsyncClient) -> None:
        """Should authenticate user via X-User-ID header."""
        # Note: A dummy Authorization header is needed because oauth2_scheme
        # has auto_error=True. The HeaderAuthProvider ignores the token value.
        response = await header_client.get(
            "/protected",
            headers={
                "Authorization": "Bearer ignored-in-header-mode",
                "X-User-ID": "test-user-123",
                "X-User-Roles": "admin,user",
                "X-User-Permissions": "recipe:read,recipe:write",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-user-123"
        assert "admin" in data["roles"]
        assert "user" in data["roles"]
        assert "recipe:read" in data["permissions"]

    @pytest.mark.asyncio
    async def test_header_auth_missing_user_id(
        self, header_client: AsyncClient
    ) -> None:
        """Should reject request without X-User-ID header."""
        response = await header_client.get(
            "/protected",
            headers={
                "Authorization": "Bearer ignored-in-header-mode",
                "X-User-Roles": "user",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_header_auth_empty_user_id(self, header_client: AsyncClient) -> None:
        """Should reject request with empty X-User-ID header."""
        response = await header_client.get(
            "/protected",
            headers={
                "Authorization": "Bearer ignored-in-header-mode",
                "X-User-ID": "",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_header_auth_optional_roles(self, header_client: AsyncClient) -> None:
        """Should work with only user ID, using default roles when header is missing."""
        response = await header_client.get(
            "/protected",
            headers={
                "Authorization": "Bearer ignored-in-header-mode",
                "X-User-ID": "minimal-user",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "minimal-user"
        # Default roles are ["user"] when no roles header is provided
        assert data["roles"] == ["user"]
        assert data["permissions"] == []

    @pytest.mark.asyncio
    async def test_header_auth_public_endpoint(
        self, header_client: AsyncClient
    ) -> None:
        """Should allow access to public endpoints without headers."""
        response = await header_client.get("/public")

        assert response.status_code == 200
        assert response.json()["message"] == "public"


# =============================================================================
# Local JWT Mode Tests
# =============================================================================


class TestLocalJWTAuthMode:
    """E2E tests for local JWT authentication mode."""

    @pytest.fixture
    def jwt_settings(self) -> Settings:
        """Create settings for JWT testing."""
        return Settings(
            APP_ENV="test",
            JWT_SECRET_KEY="test-secret-key-for-jwt-validation",
            REDIS_PASSWORD="",
            app=AppSettings(
                name="jwt-test-app",
                version="0.0.1",
                debug=True,
            ),
            server=ServerSettings(
                host="0.0.0.0",
                port=8000,
            ),
            api=ApiSettings(
                cors_origins=["http://localhost:3000"],
            ),
            auth=AuthSettings(
                mode="local_jwt",
                jwt=JwtSettings(
                    algorithm="HS256",
                    access_token_expire_minutes=30,
                    refresh_token_expire_days=7,
                ),
                jwt_validation=AuthJwtValidationSettings(
                    issuer="test-issuer",
                ),
            ),
            redis=RedisSettings(
                host="localhost",
                port=6379,
                cache_db=0,
                queue_db=1,
                rate_limit_db=2,
            ),
            rate_limiting=RateLimitingSettings(
                default="100/minute",
                auth="10/minute",
            ),
            logging=LoggingSettings(),
            observability=ObservabilitySettings(),
        )

    @pytest.fixture
    async def jwt_app(self, jwt_settings: Settings) -> AsyncGenerator[FastAPI]:
        """Create app configured for local JWT auth mode."""
        app = create_test_app_with_protected_endpoint()

        # Set up local JWT auth provider (no issuer validation since
        # create_access_token doesn't add issuer claim by default)
        provider = LocalJWTAuthProvider(
            secret_key=jwt_settings.JWT_SECRET_KEY,
            algorithm=jwt_settings.auth.jwt.algorithm,
            issuer=None,  # Don't validate issuer
        )
        await provider.initialize()
        set_auth_provider(provider)

        yield app

        await shutdown_auth_provider()

    @pytest.fixture
    async def jwt_client(self, jwt_app: FastAPI) -> AsyncGenerator[AsyncClient]:
        """Create async client for JWT auth mode."""
        async with AsyncClient(
            transport=ASGITransport(app=jwt_app),
            base_url="http://test",
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_jwt_auth_valid_token(
        self, jwt_client: AsyncClient, jwt_settings: Settings
    ) -> None:
        """Should authenticate user with valid JWT token."""
        with patch("app.auth.jwt.get_settings", return_value=jwt_settings):
            token = create_access_token(
                subject="jwt-test-user",
                roles=["admin", "user"],
                permissions=["recipe:read", "recipe:write"],
            )

        response = await jwt_client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "jwt-test-user"
        assert "admin" in data["roles"]
        assert "recipe:read" in data["permissions"]

    @pytest.mark.asyncio
    async def test_jwt_auth_expired_token(
        self, jwt_client: AsyncClient, jwt_settings: Settings
    ) -> None:
        """Should reject expired JWT token."""
        # Create token that's already expired
        with patch("app.auth.jwt.get_settings", return_value=jwt_settings):
            token = create_access_token(
                subject="expired-user",
                roles=["user"],
                expires_delta=timedelta(seconds=-10),  # Expired 10 seconds ago
            )

        response = await jwt_client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_jwt_auth_invalid_token(self, jwt_client: AsyncClient) -> None:
        """Should reject malformed JWT token."""
        response = await jwt_client.get(
            "/protected",
            headers={"Authorization": "Bearer not-a-valid-jwt-token"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_jwt_auth_wrong_secret(
        self, jwt_client: AsyncClient, jwt_settings: Settings
    ) -> None:
        """Should reject token signed with wrong secret."""
        # Create settings with different secret
        wrong_settings = Settings(
            **{
                **jwt_settings.model_dump(),
                "JWT_SECRET_KEY": "wrong-secret-key",
            }
        )

        with patch("app.auth.jwt.get_settings", return_value=wrong_settings):
            token = create_access_token(
                subject="wrong-secret-user",
                roles=["user"],
            )

        response = await jwt_client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_jwt_auth_missing_token(self, jwt_client: AsyncClient) -> None:
        """Should reject request without Authorization header."""
        response = await jwt_client.get("/protected")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_jwt_auth_empty_bearer(self, jwt_client: AsyncClient) -> None:
        """Should reject request with empty bearer token."""
        response = await jwt_client.get(
            "/protected",
            headers={"Authorization": "Bearer "},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_jwt_auth_public_endpoint(self, jwt_client: AsyncClient) -> None:
        """Should allow access to public endpoints without token."""
        response = await jwt_client.get("/public")

        assert response.status_code == 200
        assert response.json()["message"] == "public"


# =============================================================================
# Introspection Mode Tests
# =============================================================================


class TestIntrospectionAuthMode:
    """E2E tests for introspection-based authentication mode."""

    @pytest.fixture
    def introspection_settings(self) -> Settings:
        """Create settings for introspection testing."""
        return Settings(
            APP_ENV="test",
            JWT_SECRET_KEY="fallback-secret-for-introspection",
            REDIS_PASSWORD="",
            AUTH_SERVICE_CLIENT_SECRET="client-secret",
            app=AppSettings(
                name="introspection-test-app",
                version="0.0.1",
                debug=True,
            ),
            server=ServerSettings(
                host="0.0.0.0",
                port=8000,
            ),
            api=ApiSettings(
                cors_origins=["http://localhost:3000"],
            ),
            auth=AuthSettings(
                mode="introspection",
                jwt=JwtSettings(
                    algorithm="HS256",
                    access_token_expire_minutes=30,
                    refresh_token_expire_days=7,
                ),
                service=AuthServiceSettings(
                    url="http://auth-service:8080/api/v1/auth",
                    client_id="recipe-scraper",
                ),
            ),
            redis=RedisSettings(
                host="localhost",
                port=6379,
                cache_db=0,
                queue_db=1,
                rate_limit_db=2,
            ),
            rate_limiting=RateLimitingSettings(
                default="100/minute",
                auth="10/minute",
            ),
            logging=LoggingSettings(),
            observability=ObservabilitySettings(),
        )

    @pytest.fixture
    async def introspection_app(
        self, introspection_settings: Settings
    ) -> AsyncGenerator[FastAPI]:
        """Create app configured for introspection auth mode."""
        app = create_test_app_with_protected_endpoint()

        # These are guaranteed to be set in introspection_settings fixture
        assert introspection_settings.auth.service.url is not None
        assert introspection_settings.auth.service.client_id is not None
        assert introspection_settings.AUTH_SERVICE_CLIENT_SECRET is not None

        # Set up introspection auth provider (without actually calling external service)
        provider = IntrospectionAuthProvider(
            base_url=introspection_settings.auth.service.url,
            client_id=introspection_settings.auth.service.client_id,
            client_secret=introspection_settings.AUTH_SERVICE_CLIENT_SECRET,
            timeout=5.0,
        )
        await provider.initialize()
        set_auth_provider(provider)

        yield app

        await shutdown_auth_provider()

    @pytest.fixture
    async def introspection_client(
        self, introspection_app: FastAPI
    ) -> AsyncGenerator[AsyncClient]:
        """Create async client for introspection auth mode."""
        async with AsyncClient(
            transport=ASGITransport(app=introspection_app),
            base_url="http://test",
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_introspection_valid_token(
        self, introspection_client: AsyncClient
    ) -> None:
        """Should authenticate user via token introspection."""
        # Mock the auth service response
        # Note: roles are extracted from the scope string, not the roles field
        mock_response = IntrospectionResponse(
            active=True,
            sub="introspection-user-123",
            client_id="recipe-scraper",
            scope="openid profile user premium recipe:read recipe:write",
            token_type="Bearer",
            exp=9999999999,
            iat=1700000000,
        )

        with patch.object(
            AuthServiceClient,
            "introspect_token",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            response = await introspection_client.get(
                "/protected",
                headers={"Authorization": "Bearer valid-oauth-token"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "introspection-user-123"
        assert "user" in data["roles"]
        assert "premium" in data["roles"]

    @pytest.mark.asyncio
    async def test_introspection_inactive_token(
        self, introspection_client: AsyncClient
    ) -> None:
        """Should reject inactive/revoked token."""
        mock_response = IntrospectionResponse(
            active=False,
        )

        with patch.object(
            AuthServiceClient,
            "introspect_token",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            response = await introspection_client.get(
                "/protected",
                headers={"Authorization": "Bearer revoked-token"},
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_introspection_service_unavailable(
        self, introspection_client: AsyncClient
    ) -> None:
        """Should return 503 when auth service is unavailable."""
        with patch.object(
            AuthServiceClient,
            "introspect_token",
            new_callable=AsyncMock,
            side_effect=AuthServiceUnavailableError("Connection refused"),
        ):
            response = await introspection_client.get(
                "/protected",
                headers={"Authorization": "Bearer some-token"},
            )

        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_introspection_with_fallback(
        self, introspection_settings: Settings
    ) -> None:
        """Should fall back to local JWT when introspection fails."""
        app = create_test_app_with_protected_endpoint()

        # Create provider with fallback enabled
        fallback_provider = LocalJWTAuthProvider(
            secret_key=introspection_settings.JWT_SECRET_KEY,
            algorithm=introspection_settings.auth.jwt.algorithm,
        )

        # These are guaranteed to be set in introspection_settings fixture
        assert introspection_settings.auth.service.url is not None
        assert introspection_settings.auth.service.client_id is not None
        assert introspection_settings.AUTH_SERVICE_CLIENT_SECRET is not None

        provider = IntrospectionAuthProvider(
            base_url=introspection_settings.auth.service.url,
            client_id=introspection_settings.auth.service.client_id,
            client_secret=introspection_settings.AUTH_SERVICE_CLIENT_SECRET,
            fallback_provider=fallback_provider,
        )
        await provider.initialize()
        set_auth_provider(provider)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                # Create a valid JWT token
                with patch(
                    "app.auth.jwt.get_settings", return_value=introspection_settings
                ):
                    token = create_access_token(
                        subject="fallback-user",
                        roles=["user"],
                        permissions=["recipe:read"],
                    )

                # Mock introspection to fail, triggering fallback
                with patch.object(
                    AuthServiceClient,
                    "introspect_token",
                    new_callable=AsyncMock,
                    side_effect=AuthServiceUnavailableError("Timeout"),
                ):
                    response = await client.get(
                        "/protected",
                        headers={"Authorization": f"Bearer {token}"},
                    )

                # Should succeed via fallback
                assert response.status_code == 200
                data = response.json()
                assert data["user_id"] == "fallback-user"
        finally:
            await shutdown_auth_provider()

    @pytest.mark.asyncio
    async def test_introspection_missing_token(
        self, introspection_client: AsyncClient
    ) -> None:
        """Should reject request without Authorization header."""
        response = await introspection_client.get("/protected")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_introspection_public_endpoint(
        self, introspection_client: AsyncClient
    ) -> None:
        """Should allow access to public endpoints without token."""
        response = await introspection_client.get("/public")

        assert response.status_code == 200
        assert response.json()["message"] == "public"


# =============================================================================
# Factory Tests (Auth Mode Selection)
# =============================================================================


class TestAuthModeFactory:
    """E2E tests for auth provider factory and mode selection."""

    @pytest.mark.asyncio
    async def test_factory_creates_header_provider(self) -> None:
        """Should create HeaderAuthProvider for header mode."""
        settings = Settings(
            APP_ENV="test",
            JWT_SECRET_KEY="test-secret",
            REDIS_PASSWORD="",
            app=AppSettings(name="test", version="0.0.1", debug=True),
            server=ServerSettings(host="0.0.0.0", port=8000),
            api=ApiSettings(cors_origins=[]),
            auth=AuthSettings(mode="header"),
            redis=RedisSettings(
                host="localhost", port=6379, cache_db=0, queue_db=1, rate_limit_db=2
            ),
            rate_limiting=RateLimitingSettings(default="100/minute", auth="10/minute"),
            logging=LoggingSettings(),
            observability=ObservabilitySettings(),
        )

        provider = create_auth_provider(settings)
        assert isinstance(provider, HeaderAuthProvider)
        assert provider.provider_name == "header"

    @pytest.mark.asyncio
    async def test_factory_creates_local_jwt_provider(self) -> None:
        """Should create LocalJWTAuthProvider for local_jwt mode."""
        settings = Settings(
            APP_ENV="test",
            JWT_SECRET_KEY="test-secret",
            REDIS_PASSWORD="",
            app=AppSettings(name="test", version="0.0.1", debug=True),
            server=ServerSettings(host="0.0.0.0", port=8000),
            api=ApiSettings(cors_origins=[]),
            auth=AuthSettings(mode="local_jwt"),
            redis=RedisSettings(
                host="localhost", port=6379, cache_db=0, queue_db=1, rate_limit_db=2
            ),
            rate_limiting=RateLimitingSettings(default="100/minute", auth="10/minute"),
            logging=LoggingSettings(),
            observability=ObservabilitySettings(),
        )

        provider = create_auth_provider(settings)
        assert isinstance(provider, LocalJWTAuthProvider)
        assert provider.provider_name == "local_jwt"

    @pytest.mark.asyncio
    async def test_factory_creates_introspection_provider(self) -> None:
        """Should create IntrospectionAuthProvider for introspection mode."""
        settings = Settings(
            APP_ENV="test",
            JWT_SECRET_KEY="test-secret",
            REDIS_PASSWORD="",
            AUTH_SERVICE_CLIENT_SECRET="test-secret",
            app=AppSettings(name="test", version="0.0.1", debug=True),
            server=ServerSettings(host="0.0.0.0", port=8000),
            api=ApiSettings(cors_origins=[]),
            auth=AuthSettings(
                mode="introspection",
                service=AuthServiceSettings(
                    url="http://auth:8080", client_id="test-client"
                ),
            ),
            redis=RedisSettings(
                host="localhost", port=6379, cache_db=0, queue_db=1, rate_limit_db=2
            ),
            rate_limiting=RateLimitingSettings(default="100/minute", auth="10/minute"),
            logging=LoggingSettings(),
            observability=ObservabilitySettings(),
        )

        provider = create_auth_provider(settings)
        assert isinstance(provider, IntrospectionAuthProvider)
        assert provider.provider_name == "introspection"

    @pytest.mark.asyncio
    async def test_factory_raises_for_missing_introspection_config(self) -> None:
        """Should raise ConfigurationError when introspection config is missing."""
        settings = Settings(
            APP_ENV="test",
            JWT_SECRET_KEY="test-secret",
            REDIS_PASSWORD="",
            app=AppSettings(name="test", version="0.0.1", debug=True),
            server=ServerSettings(host="0.0.0.0", port=8000),
            api=ApiSettings(cors_origins=[]),
            auth=AuthSettings(mode="introspection"),
            redis=RedisSettings(
                host="localhost", port=6379, cache_db=0, queue_db=1, rate_limit_db=2
            ),
            rate_limiting=RateLimitingSettings(default="100/minute", auth="10/minute"),
            logging=LoggingSettings(),
            observability=ObservabilitySettings(),
            # Missing AUTH_SERVICE_CLIENT_SECRET and auth.service.url/client_id
        )

        with pytest.raises(ConfigurationError):
            create_auth_provider(settings)
