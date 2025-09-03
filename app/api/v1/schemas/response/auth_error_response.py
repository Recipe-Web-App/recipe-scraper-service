"""Authentication error response schemas.

Defines the Pydantic models for authentication-related error responses.
"""

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema


class AuthErrorResponse(BaseSchema):
    """Base authentication error response model.

    Attributes:
        detail: Human-readable error message.
        error_type: Machine-readable error type identifier.
    """

    detail: str = Field(
        ...,
        description="Human-readable error message describing authentication failure.",
        examples=["Authentication required"],
    )
    error_type: str = Field(
        ...,
        description="Machine-readable error type identifier.",
        examples=["authentication_required"],
    )


class AuthenticationRequiredResponse(AuthErrorResponse):
    """Response for when authentication is required but not provided."""

    detail: str = Field(
        default="Authentication required",
        description="Authentication is required to access this resource.",
    )
    error_type: str = Field(
        default="authentication_required",
        description="Error type indicating missing authentication.",
    )


class InvalidTokenResponse(AuthErrorResponse):
    """Response for invalid authentication tokens."""

    detail: str = Field(
        default="Invalid authentication token",
        description="The provided authentication token is invalid or malformed.",
    )
    error_type: str = Field(
        default="invalid_token",
        description="Error type indicating invalid token.",
    )


class ExpiredTokenResponse(AuthErrorResponse):
    """Response for expired authentication tokens."""

    detail: str = Field(
        default="Authentication token has expired",
        description="The provided authentication token has expired.",
    )
    error_type: str = Field(
        default="expired_token",
        description="Error type indicating expired token.",
    )


class InsufficientPermissionsResponse(AuthErrorResponse):
    """Response for insufficient permissions."""

    detail: str = Field(
        default="Insufficient permissions",
        description="The authenticated user lacks the required permissions.",
    )
    error_type: str = Field(
        default="insufficient_permissions",
        description="Error type indicating insufficient permissions.",
    )


class IntrospectionFailedResponse(AuthErrorResponse):
    """Response for OAuth2 introspection failures."""

    detail: str = Field(
        default="OAuth2 token introspection failed",
        description="Failed to validate token via OAuth2 introspection.",
    )
    error_type: str = Field(
        default="introspection_failed",
        description="Error type indicating introspection failure.",
    )
