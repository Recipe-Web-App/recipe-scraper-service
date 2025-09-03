"""Token management utilities.

This module contains functions for generating, validating, and handling authentication
or security tokens.
"""

from datetime import UTC, datetime

import jwt
from jwt import InvalidTokenError as JWTInvalidTokenError

from app.api.v1.schemas.downstream.auth_service.introspection_response import (
    OAuth2IntrospectionResponse,
)
from app.core.config.config import get_settings
from app.core.logging import get_logger
from app.exceptions.custom_exceptions import (
    ExpiredTokenError,
    InvalidTokenError,
)

_log = get_logger(__name__)
settings = get_settings()


def decode_jwt_token(token: str) -> OAuth2IntrospectionResponse:
    """Decode and validate a JWT token.

    Args:
        token: The JWT token string to decode and validate.

    Returns:
        OAuth2IntrospectionResponse: Token info in standard introspection format.

    Raises:
        InvalidTokenError: If the token is malformed or signature is invalid.
        ExpiredTokenError: If the token has expired.
    """
    try:
        # Decode the token with signature verification
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"verify_exp": True, "verify_aud": False},
        )

        # Check expiration manually for custom handling
        exp = payload.get("exp")
        if exp is not None:
            exp_datetime = datetime.fromtimestamp(exp, tz=UTC)
            if datetime.now(UTC) >= exp_datetime:
                raise ExpiredTokenError()

        # Convert JWT payload to standard OAuth2 introspection format
        return OAuth2IntrospectionResponse(
            active=True,
            scope=payload.get("scope"),
            client_id=payload.get("client_id") or payload.get("azp"),
            username=payload.get("username") or payload.get("preferred_username"),
            token_type="Bearer",  # nosec B106 - Standard OAuth2 token type
            exp=payload.get("exp"),
            iat=payload.get("iat"),
            nbf=payload.get("nbf"),
            sub=payload.get("sub"),
            aud=payload.get("aud"),
            iss=payload.get("iss"),
            jti=payload.get("jti"),
        )

    except jwt.ExpiredSignatureError as e:
        _log.warning("JWT token has expired")
        raise ExpiredTokenError() from e
    except (jwt.InvalidTokenError, JWTInvalidTokenError) as e:
        _log.warning("JWT validation failed: {}", str(e))
        raise InvalidTokenError(f"JWT validation failed: {str(e)}") from e


def extract_bearer_token(authorization_header: str) -> str:
    """Extract the bearer token from Authorization header.

    Args:
        authorization_header: The Authorization header value.

    Returns:
        str: The extracted token.

    Raises:
        InvalidTokenError: If the header format is invalid.
    """
    if not authorization_header:
        raise InvalidTokenError("Empty authorization header")

    parts = authorization_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise InvalidTokenError("Invalid authorization header format")

    return parts[1]
