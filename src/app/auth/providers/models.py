"""Authentication provider models.

This module defines data models used by authentication providers.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AuthResult(BaseModel):
    """Result of successful token validation.

    This model represents the authenticated user information extracted
    from a token, regardless of which auth provider performed the validation.
    It provides a consistent interface for the rest of the application.

    Attributes:
        user_id: Unique identifier for the authenticated user (from 'sub' claim).
        roles: List of role names assigned to the user.
        permissions: List of permission strings for fine-grained access control.
        scopes: OAuth2 scopes from the token (from auth-service introspection).
        token_type: Type of token that was validated (access, refresh, api_key, header).
        issuer: Token issuer (from 'iss' claim).
        audience: Token audience(s) (from 'aud' claim).
        expires_at: Token expiration timestamp (from 'exp' claim).
        issued_at: Token issuance timestamp (from 'iat' claim).
        raw_claims: Original token claims for debugging/auditing.
    """

    user_id: str = Field(..., description="User identifier from token 'sub' claim")
    roles: list[str] = Field(default_factory=list, description="User roles")
    permissions: list[str] = Field(default_factory=list, description="User permissions")
    scopes: list[str] = Field(default_factory=list, description="OAuth2 scopes")
    token_type: str = Field(default="access", description="Type of validated token")
    issuer: str | None = Field(default=None, description="Token issuer")
    audience: list[str] = Field(default_factory=list, description="Token audience")
    expires_at: int | None = Field(default=None, description="Expiration timestamp")
    issued_at: int | None = Field(default=None, description="Issuance timestamp")
    raw_claims: dict[str, Any] = Field(
        default_factory=dict,
        description="Original token claims",
    )

    model_config = {"frozen": True}  # Immutable after creation


class IntrospectionResponse(BaseModel):
    """Response from OAuth2 token introspection endpoint.

    Based on RFC 7662 - OAuth 2.0 Token Introspection.
    See: https://datatracker.ietf.org/doc/html/rfc7662

    Attributes:
        active: Whether the token is currently active.
        sub: Subject identifier (user ID).
        scope: Space-separated list of scopes.
        client_id: Client that requested the token.
        token_type: Type of token (e.g., "Bearer").
        exp: Expiration timestamp.
        iat: Issuance timestamp.
        nbf: Not-before timestamp.
        aud: Audience(s) for the token.
        iss: Issuer of the token.
    """

    active: bool
    sub: str | None = None
    scope: str | None = None
    client_id: str | None = None
    token_type: str | None = None
    exp: int | None = None
    iat: int | None = None
    nbf: int | None = None
    aud: str | list[str] | None = None
    iss: str | None = None

    @property
    def scopes(self) -> list[str]:
        """Parse scope string into list."""
        if not self.scope:
            return []
        return self.scope.split()

    @property
    def audience_list(self) -> list[str]:
        """Get audience as list."""
        if not self.aud:
            return []
        if isinstance(self.aud, str):
            return [self.aud]
        return self.aud
