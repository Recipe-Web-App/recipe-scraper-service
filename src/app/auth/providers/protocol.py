"""Authentication provider protocol definition.

This module defines the AuthProvider protocol that all authentication
providers must implement. Using a Protocol enables static type checking
while maintaining flexibility for different implementations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable


if TYPE_CHECKING:
    from starlette.requests import Request

    from app.auth.providers.models import AuthResult


@runtime_checkable
class AuthProvider(Protocol):
    """Protocol for authentication providers.

    All auth providers must implement this interface to ensure
    consistent behavior across different authentication modes.

    The protocol supports:
    - Token validation with optional request context
    - Lifecycle management (initialize/shutdown)
    - Provider identification for logging/metrics

    Example implementation:
        class MyAuthProvider:
            @property
            def provider_name(self) -> str:
                return "my_provider"

            async def validate_token(
                self,
                token: str,
                request: Request | None = None,
            ) -> AuthResult:
                # Validate token and return result
                ...

            async def initialize(self) -> None:
                # Setup connections, etc.
                ...

            async def shutdown(self) -> None:
                # Cleanup resources
                ...
    """

    @property
    def provider_name(self) -> str:
        """Return the provider name for logging and metrics.

        Returns:
            A short, descriptive name like 'introspection', 'local_jwt', or 'header'.
        """
        ...

    async def validate_token(
        self,
        token: str,
        request: Request | None = None,
    ) -> AuthResult:
        """Validate a token and return authentication result.

        This is the core method that all providers must implement.
        The request parameter is optional and only used by providers
        that need access to request headers (e.g., HeaderAuthProvider).

        Args:
            token: The bearer token to validate. May be empty for header-based auth.
            request: Optional request object for accessing headers.

        Returns:
            AuthResult containing validated user information.

        Raises:
            TokenExpiredError: If the token has expired.
            TokenInvalidError: If the token is malformed or signature fails.
            AuthenticationError: For other authentication failures.
            AuthServiceUnavailableError: If external auth service is unreachable.
        """
        ...

    async def initialize(self) -> None:
        """Initialize the provider.

        Called during application startup. Use this to:
        - Establish connections (HTTP clients, Redis, etc.)
        - Validate configuration
        - Warm up caches

        Raises:
            ConfigurationError: If the provider is misconfigured.
        """
        ...

    async def shutdown(self) -> None:
        """Clean up provider resources.

        Called during application shutdown. Use this to:
        - Close HTTP connections
        - Flush caches
        - Release any held resources
        """
        ...
