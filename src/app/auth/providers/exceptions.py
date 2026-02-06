"""Authentication provider exceptions.

This module defines exceptions specific to authentication providers.
These exceptions are caught by the dependency layer and converted to
appropriate HTTP responses.
"""

from __future__ import annotations


class AuthProviderError(Exception):
    """Base exception for auth provider errors."""


class AuthenticationError(AuthProviderError):
    """Raised when authentication fails for any reason."""


class TokenExpiredError(AuthenticationError):
    """Raised when a token has expired."""


class TokenInvalidError(AuthenticationError):
    """Raised when a token is malformed or signature verification fails."""


class AuthServiceUnavailableError(AuthProviderError):
    """Raised when the external auth service cannot be reached."""


class ConfigurationError(AuthProviderError):
    """Raised when the auth provider is misconfigured."""
