"""Introspection-based authentication provider.

This provider validates tokens by calling the external auth-service's
token introspection endpoint (RFC 7662). Use this for production
deployments with centralized authentication.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.auth.client.auth_service import AuthServiceClient
from app.auth.providers.exceptions import (
    AuthServiceUnavailableError,
    ConfigurationError,
    TokenInvalidError,
)
from app.auth.providers.models import AuthResult
from app.observability.logging import get_logger


if TYPE_CHECKING:
    from redis.asyncio import Redis
    from starlette.requests import Request

    from app.auth.providers.protocol import AuthProvider

logger = get_logger(__name__)


class IntrospectionAuthProvider:
    """Validates tokens via external auth-service introspection endpoint.

    This provider calls the auth-service's /oauth2/introspect endpoint
    to validate tokens. It supports:
    - Caching introspection results in Redis
    - Optional fallback to local JWT validation
    - Connection pooling for performance

    Attributes:
        auth_client: HTTP client for the auth-service.
        fallback_provider: Optional provider to use when introspection fails.
    """

    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        timeout: float = 5.0,
        cache_client: Redis[Any] | None = None,
        cache_ttl: int = 60,
        fallback_provider: AuthProvider | None = None,
    ) -> None:
        """Initialize the introspection auth provider.

        Args:
            base_url: Base URL of the auth service.
            client_id: OAuth2 client ID for introspection.
            client_secret: OAuth2 client secret.
            timeout: HTTP request timeout in seconds.
            cache_client: Optional Redis client for caching.
            cache_ttl: Cache TTL in seconds.
            fallback_provider: Optional provider to use when introspection fails.

        Raises:
            ConfigurationError: If required parameters are missing.
        """
        if not all([base_url, client_id, client_secret]):
            msg = (
                "IntrospectionAuthProvider requires base_url, client_id, "
                "and client_secret"
            )
            raise ConfigurationError(msg)

        self.auth_client = AuthServiceClient(
            base_url=base_url,
            client_id=client_id,
            client_secret=client_secret,
            timeout=timeout,
            cache_client=cache_client,
            cache_ttl=cache_ttl,
        )
        self.fallback_provider = fallback_provider
        self._initialized = False

    @property
    def provider_name(self) -> str:
        """Return provider name for logging."""
        return "introspection"

    async def validate_token(
        self,
        token: str,
        _request: Request | None = None,
    ) -> AuthResult:
        """Validate token via introspection endpoint.

        Args:
            token: The bearer token to validate.
            _request: Unused in this provider.

        Returns:
            AuthResult with validated user information.

        Raises:
            TokenInvalidError: If the token is inactive or invalid.
            AuthServiceUnavailableError: If auth service cannot be reached
                and no fallback is configured.
        """
        try:
            response = await self.auth_client.introspect_token(token)

            if not response.active:
                msg = "Token is not active"
                raise TokenInvalidError(msg)

            if not response.sub:
                msg = "Token introspection missing 'sub' claim"
                raise TokenInvalidError(msg)

            # Parse scopes into roles and permissions
            scopes = response.scopes
            roles = self._extract_roles(scopes)
            permissions = self._extract_permissions(scopes)

            return AuthResult(
                user_id=response.sub,
                roles=roles,
                permissions=permissions,
                scopes=scopes,
                token_type=response.token_type or "access",
                issuer=response.iss,
                audience=response.audience_list,
                expires_at=response.exp,
                issued_at=response.iat,
                raw_claims={
                    "active": response.active,
                    "client_id": response.client_id,
                    "scope": response.scope,
                },
            )

        except AuthServiceUnavailableError:
            if self.fallback_provider:
                logger.warning(
                    "Auth service unavailable, using fallback provider",
                    fallback=self.fallback_provider.provider_name,
                )
                return await self.fallback_provider.validate_token(token, _request)
            raise

    def _extract_roles(self, scopes: list[str]) -> list[str]:
        """Extract role names from scopes.

        Roles are scopes that match known role names or have a 'role:' prefix.
        """
        known_roles = {"user", "premium", "moderator", "admin", "service"}
        roles = []

        for scope in scopes:
            # Direct role match
            if scope.lower() in known_roles:
                roles.append(scope.lower())
            # Prefixed role (e.g., "role:admin")
            elif scope.lower().startswith("role:"):
                roles.append(scope[5:])  # Remove "role:" prefix

        return roles or ["user"]  # Default to user role

    def _extract_permissions(self, scopes: list[str]) -> list[str]:
        """Extract permissions from scopes.

        Permissions are scopes with a colon that aren't role prefixes.
        E.g., "recipe:read", "recipe:write", "user:delete"
        """
        permissions = []

        for scope in scopes:
            # Skip role prefixes
            if scope.lower().startswith("role:"):
                continue
            # Include scopes with resource:action format
            if ":" in scope:
                permissions.append(scope)

        return permissions

    async def initialize(self) -> None:
        """Initialize the provider and auth client."""
        await self.auth_client.initialize()

        if self.fallback_provider:
            await self.fallback_provider.initialize()
            logger.info(
                "IntrospectionAuthProvider initialized with fallback",
                fallback=self.fallback_provider.provider_name,
            )
        else:
            logger.info("IntrospectionAuthProvider initialized")

        self._initialized = True

    async def shutdown(self) -> None:
        """Shutdown the provider and close connections."""
        await self.auth_client.shutdown()

        if self.fallback_provider:
            await self.fallback_provider.shutdown()

        logger.debug("IntrospectionAuthProvider shutdown")
        self._initialized = False
