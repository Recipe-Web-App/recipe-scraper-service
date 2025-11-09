"""Auth service token response schema."""

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema


class TokenResponse(BaseSchema):
    """OAuth2 token response from auth-service.

    Represents the response from the OAuth2 token endpoint when using client credentials
    flow for service-to-service authentication.
    """

    access_token: str = Field(
        ...,
        description="The access token (JWT format)",
    )
    token_type: str = Field(
        ...,
        description="Token type (always 'Bearer')",
    )
    expires_in: int = Field(
        ...,
        description="Access token lifetime in seconds",
        gt=0,
    )
    refresh_token: str | None = Field(
        default=None,
        description="The refresh token (opaque format, optional)",
    )
    scope: str | None = Field(
        default=None,
        description="The granted scope(s)",
    )
