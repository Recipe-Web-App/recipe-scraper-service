"""Authentication providers package.

This package provides pluggable authentication providers that implement
the AuthProvider protocol. The factory module creates the appropriate
provider based on configuration.

Available providers:
- IntrospectionAuthProvider: Validates via external auth-service
- LocalJWTAuthProvider: Validates JWTs locally
- HeaderAuthProvider: Extracts user from headers (development only)
- DisabledAuthProvider: Allows all requests (testing only)

Usage:
    from app.auth.providers import get_auth_provider, AuthResult

    provider = get_auth_provider()
    result = await provider.validate_token(token, request)
"""

from app.auth.providers.exceptions import (
    AuthenticationError,
    AuthProviderError,
    AuthServiceUnavailableError,
    ConfigurationError,
    TokenExpiredError,
    TokenInvalidError,
)
from app.auth.providers.factory import (
    create_auth_provider,
    get_auth_provider,
    initialize_auth_provider,
    set_auth_provider,
    shutdown_auth_provider,
)
from app.auth.providers.header import HeaderAuthProvider
from app.auth.providers.introspection import IntrospectionAuthProvider
from app.auth.providers.local_jwt import LocalJWTAuthProvider
from app.auth.providers.models import AuthResult, IntrospectionResponse
from app.auth.providers.protocol import AuthProvider


__all__ = [
    "AuthProvider",
    "AuthProviderError",
    "AuthResult",
    "AuthServiceUnavailableError",
    "AuthenticationError",
    "ConfigurationError",
    "HeaderAuthProvider",
    "IntrospectionAuthProvider",
    "IntrospectionResponse",
    "LocalJWTAuthProvider",
    "TokenExpiredError",
    "TokenInvalidError",
    "create_auth_provider",
    "get_auth_provider",
    "initialize_auth_provider",
    "set_auth_provider",
    "shutdown_auth_provider",
]
