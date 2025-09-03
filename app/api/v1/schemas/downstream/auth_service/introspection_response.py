"""OAuth2 token introspection response schema.

Defines the Pydantic model for OAuth2 token introspection responses from the auth
service.
"""

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema


class OAuth2IntrospectionResponse(BaseSchema):
    """OAuth2 token introspection response model.

    Based on RFC 7662 OAuth 2.0 Token Introspection specification.

    Attributes:
        active: Boolean indicator of whether the token is currently active.
        scope: Space-separated list of scopes granted for this token.
        client_id: Client identifier for the OAuth 2.0 client.
        username: Human-readable identifier for the resource owner.
        token_type: Type of token (typically "Bearer").
        exp: Expiration timestamp (Unix timestamp).
        iat: Issued at timestamp (Unix timestamp).
        nbf: Not before timestamp (Unix timestamp).
        sub: Subject identifier for the resource owner.
        aud: Audience(s) for the token.
        iss: Issuer identifier.
        jti: JWT ID claim.
    """

    active: bool = Field(
        ...,
        description="Boolean indicator of whether the token is currently active.",
        examples=[True, False],
    )
    scope: str | None = Field(
        default=None,
        description="Space-separated list of scopes granted for this token.",
        examples=["read write", "admin"],
    )
    client_id: str | None = Field(
        default=None,
        description="Client identifier for the OAuth 2.0 client.",
        examples=["recipe-service-client"],
    )
    username: str | None = Field(
        default=None,
        description="Human-readable identifier for the resource owner.",
        examples=["john.doe"],
    )
    token_type: str | None = Field(
        default=None,
        description="Type of token.",
        examples=["Bearer"],
    )
    exp: int | None = Field(
        default=None,
        description="Expiration timestamp (Unix timestamp).",
        examples=[1699123456],
    )
    iat: int | None = Field(
        default=None,
        description="Issued at timestamp (Unix timestamp).",
        examples=[1699120000],
    )
    nbf: int | None = Field(
        default=None,
        description="Not before timestamp (Unix timestamp).",
        examples=[1699120000],
    )
    sub: str | None = Field(
        default=None,
        description="Subject identifier for the resource owner.",
        examples=["user-123"],
    )
    aud: str | list[str] | None = Field(
        default=None,
        description="Audience(s) for the token.",
        examples=["recipe-api", ["recipe-api", "user-api"]],
    )
    iss: str | None = Field(
        default=None,
        description="Issuer identifier.",
        examples=["https://auth.example.com"],
    )
    jti: str | None = Field(
        default=None,
        description="JWT ID claim.",
        examples=["jwt-id-123"],
    )
