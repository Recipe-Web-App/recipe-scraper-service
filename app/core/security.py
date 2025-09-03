"""Security utilities and configurations.

Contains security-related functions and settings, including authentication,
authorization, and encryption utilities.
"""

import httpx
from fastapi import Request

from app.api.v1.schemas.downstream.auth_service.introspection_response import (
    OAuth2IntrospectionResponse,
)
from app.core.config.config import get_settings
from app.core.logging import get_logger
from app.exceptions.custom_exceptions import (
    AuthenticationRequiredError,
    InvalidTokenError,
    OAuth2IntrospectionError,
)
from app.utils.tokens import decode_jwt_token, extract_bearer_token

_log = get_logger(__name__)
settings = get_settings()


async def validate_token_via_jwt(token: str) -> OAuth2IntrospectionResponse:
    """Validate a token using JWT validation.

    Args:
        token: The JWT token to validate.

    Returns:
        OAuth2IntrospectionResponse: Token info in standard introspection format.

    Raises:
        InvalidTokenError: If the token is invalid.
        ExpiredTokenError: If the token has expired.
    """
    if not settings.jwt_secret:
        raise InvalidTokenError("JWT secret not configured")

    # Decode JWT token - already returns OAuth2IntrospectionResponse schema
    return decode_jwt_token(token)


async def validate_token_via_introspection(token: str) -> OAuth2IntrospectionResponse:
    """Validate a token using OAuth2 introspection.

    Args:
        token: The access token to introspect.

    Returns:
        OAuth2IntrospectionResponse: Introspection response with token information.

    Raises:
        OAuth2IntrospectionError: If introspection fails or token is invalid.
    """
    if not settings.oauth2_client_id or not settings.oauth2_client_secret:
        raise OAuth2IntrospectionError("OAuth2 client credentials not configured")

    # This would typically point to your auth-service's introspection endpoint
    introspection_url = "http://auth-service/oauth/introspect"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                introspection_url,
                data={
                    "token": token,
                    "client_id": settings.oauth2_client_id,
                    "client_secret": settings.oauth2_client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                raise OAuth2IntrospectionError(
                    f"Introspection endpoint returned {response.status_code}"
                )

            # Parse and validate the response using our schema
            parsed_response = OAuth2IntrospectionResponse.model_validate(
                response.json()
            )

            # Check if token is active
            if not parsed_response.active:
                raise OAuth2IntrospectionError("Token is not active")

            return parsed_response

    except httpx.RequestError as e:
        _log.error("Failed to connect to introspection endpoint: {}", str(e))
        raise OAuth2IntrospectionError(f"Connection failed: {str(e)}") from e
    except Exception as e:
        _log.error("Unexpected error during token introspection: {}", str(e))
        raise OAuth2IntrospectionError(f"Introspection failed: {str(e)}") from e


async def authenticate_token(request: Request) -> OAuth2IntrospectionResponse | None:
    """Authenticate a request using the configured authentication method.

    Args:
        request: The FastAPI request object.

    Returns:
        OAuth2IntrospectionResponse | None: Token info if auth succeeds, None otherwise.

    Raises:
        AuthenticationRequiredError: If authentication is required but missing.
        InvalidTokenError: If the provided token is invalid.
        ExpiredTokenError: If the provided token has expired.
        OAuth2IntrospectionError: If OAuth2 introspection fails.
    """
    # Skip authentication if OAuth2 service is not enabled
    if not settings.oauth2_service_enabled:
        return None

    # Extract token from Authorization header
    authorization_header = request.headers.get("authorization")
    if not authorization_header:
        return None

    try:
        token = extract_bearer_token(authorization_header)
    except InvalidTokenError:
        return None

    # Choose validation method based on configuration
    if settings.oauth2_introspection_enabled:
        return await validate_token_via_introspection(token)
    else:
        return await validate_token_via_jwt(token)


async def require_authentication(request: Request) -> OAuth2IntrospectionResponse:
    """Require authentication for a request.

    Args:
        request: The FastAPI request object.

    Returns:
        OAuth2IntrospectionResponse: The token information.

    Raises:
        AuthenticationRequiredError: If authentication is required but missing.
        InvalidTokenError: If the provided token is invalid.
        ExpiredTokenError: If the provided token has expired.
        OAuth2IntrospectionError: If OAuth2 introspection fails.
    """
    token_payload = await authenticate_token(request)
    if token_payload is None:
        raise AuthenticationRequiredError()
    return token_payload


def is_authentication_enabled() -> bool:
    """Check if authentication is enabled.

    Returns:
        bool: True if OAuth2 authentication is enabled, False otherwise.
    """
    return settings.oauth2_service_enabled
