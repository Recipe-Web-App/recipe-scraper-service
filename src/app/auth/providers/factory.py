"""Authentication provider factory.

This module provides factory functions for creating auth providers
based on application configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.auth.providers.exceptions import ConfigurationError
from app.auth.providers.header import HeaderAuthProvider
from app.auth.providers.introspection import IntrospectionAuthProvider
from app.auth.providers.local_jwt import LocalJWTAuthProvider
from app.auth.providers.models import AuthResult
from app.core.config import AuthMode, get_settings
from app.observability.logging import get_logger


if TYPE_CHECKING:
    from redis.asyncio import Redis

    from app.auth.providers.protocol import AuthProvider
    from app.core.config import Settings

logger = get_logger(__name__)

# Fixed development secret - safe for local dev, blocked in production
_DEV_JWT_SECRET = "insecure-dev-key-do-not-use-in-production"  # noqa: S105


def _get_jwt_secret(settings: Settings) -> str:
    """Get JWT secret, validating it's set in production.

    Args:
        settings: Application settings.

    Returns:
        JWT secret key to use.

    Raises:
        ConfigurationError: If secret is not set in production.
    """
    if settings.JWT_SECRET_KEY:
        return settings.JWT_SECRET_KEY

    if settings.is_production:
        msg = "JWT_SECRET_KEY must be set in production for local_jwt auth mode"
        raise ConfigurationError(msg)

    logger.warning("Using insecure development JWT secret - do not use in production")
    return _DEV_JWT_SECRET


# Provider state container (avoids global statement for mutation)
_state: dict[str, AuthProvider | None] = {"provider": None}


class DisabledAuthProvider:
    """Auth provider that allows all requests (for disabled auth mode).

    WARNING: This provider bypasses all authentication. Only use for
    internal services that don't require authentication.
    """

    @property
    def provider_name(self) -> str:
        return "disabled"

    async def validate_token(
        self,
        _token: str,
        _request: object = None,
    ) -> AuthResult:
        """Return a default anonymous user result."""
        return AuthResult(
            user_id="anonymous",
            roles=["anonymous"],
            permissions=[],
            scopes=[],
            token_type="none",  # noqa: S106 - not a password
            raw_claims={"auth_disabled": True},
        )

    async def initialize(self) -> None:
        logger.warning(
            "DisabledAuthProvider initialized - authentication is disabled! "
            "Ensure this is intentional and not a production deployment."
        )

    async def shutdown(self) -> None:
        pass


def create_auth_provider(
    settings: Settings | None = None,
    cache_client: Redis[Any] | None = None,
) -> AuthProvider:
    """Create an authentication provider based on configuration.

    This factory function creates the appropriate provider based on
    the AUTH_MODE setting:
    - INTROSPECTION: Validates via external auth-service
    - LOCAL_JWT: Validates JWTs locally
    - HEADER: Extracts user from headers (development only)
    - DISABLED: Allows all requests (testing only)

    Args:
        settings: Application settings. If None, loaded from environment.
        cache_client: Optional Redis client for caching (used by introspection).

    Returns:
        Configured AuthProvider instance.

    Raises:
        ConfigurationError: If required settings are missing for the auth mode.
    """
    if settings is None:
        settings = get_settings()

    mode = settings.auth_mode_enum
    logger.info("Creating auth provider", mode=mode.value)

    if mode == AuthMode.DISABLED:
        return DisabledAuthProvider()

    if mode == AuthMode.HEADER:
        return HeaderAuthProvider(
            user_id_header=settings.auth.headers.user_id,
            roles_header=settings.auth.headers.roles,
            permissions_header=settings.auth.headers.permissions,
        )

    if mode == AuthMode.LOCAL_JWT:
        secret_key = _get_jwt_secret(settings)
        return LocalJWTAuthProvider(
            secret_key=secret_key,
            algorithm=settings.auth.jwt.algorithm,
            issuer=settings.auth.jwt_validation.issuer,
            audience=settings.auth.jwt_validation.audience or None,
        )

    if mode == AuthMode.INTROSPECTION:
        # Validate required settings
        if not settings.auth.service.url:
            msg = "auth.service.url is required for introspection mode"
            raise ConfigurationError(msg)
        if not settings.auth.service.client_id:
            msg = "auth.service.client_id is required for introspection mode"
            raise ConfigurationError(msg)
        if not settings.AUTH_SERVICE_CLIENT_SECRET:
            msg = "AUTH_SERVICE_CLIENT_SECRET is required for introspection mode"
            raise ConfigurationError(msg)

        # Create fallback provider if configured
        fallback: AuthProvider | None = None
        if settings.auth.introspection.fallback_local:
            logger.info("Configuring local JWT fallback for introspection")
            fallback = LocalJWTAuthProvider(
                secret_key=_get_jwt_secret(settings),
                algorithm=settings.auth.jwt.algorithm,
                issuer=settings.auth.jwt_validation.issuer,
                audience=settings.auth.jwt_validation.audience or None,
            )

        return IntrospectionAuthProvider(
            base_url=settings.auth.service.url,
            client_id=settings.auth.service.client_id,
            client_secret=settings.AUTH_SERVICE_CLIENT_SECRET,
            timeout=settings.auth.introspection.timeout,
            cache_client=cache_client,
            cache_ttl=settings.auth.introspection.cache_ttl,
            fallback_provider=fallback,
        )

    # Should not reach here due to enum validation
    msg = f"Unknown auth mode: {mode}"
    raise ConfigurationError(msg)


def get_auth_provider() -> AuthProvider:
    """Get the current auth provider instance.

    This returns the globally initialized provider. Call set_auth_provider()
    during application startup to initialize it.

    Returns:
        The current AuthProvider instance.

    Raises:
        RuntimeError: If the provider has not been initialized.
    """
    provider = _state["provider"]
    if provider is None:
        msg = "Auth provider not initialized. Call set_auth_provider() during startup."
        raise RuntimeError(msg)
    return provider


def set_auth_provider(provider: AuthProvider) -> None:
    """Set the global auth provider instance.

    Called during application startup after creating the provider.

    Args:
        provider: The auth provider to use globally.
    """
    _state["provider"] = provider
    logger.info("Auth provider set", provider=provider.provider_name)


async def initialize_auth_provider(
    cache_client: Redis[Any] | None = None,
) -> AuthProvider:
    """Create, initialize, and set the auth provider.

    Convenience function that creates the provider, calls initialize(),
    and sets it as the global provider.

    Args:
        cache_client: Optional Redis client for caching.

    Returns:
        The initialized auth provider.
    """
    provider = create_auth_provider(cache_client=cache_client)
    await provider.initialize()
    set_auth_provider(provider)
    return provider


async def shutdown_auth_provider() -> None:
    """Shutdown the global auth provider.

    Calls shutdown() on the provider and clears the global instance.
    """
    provider = _state["provider"]
    if provider is not None:
        await provider.shutdown()
        _state["provider"] = None
        logger.info("Auth provider shutdown complete")
