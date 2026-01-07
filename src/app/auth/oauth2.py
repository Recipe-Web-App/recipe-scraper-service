"""OAuth2 authentication schemes.

This module provides OAuth2 security schemes for FastAPI:
- OAuth2PasswordBearer for password-based authentication
- OAuth2AuthorizationCodeBearer for authorization code flow
- API Key authentication for service-to-service communication
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    APIKeyHeader,
    OAuth2PasswordBearer,
)

from app.auth.jwt import TokenExpiredError, TokenInvalidError, decode_token
from app.core.config import get_settings

# OAuth2 password bearer scheme
# Token URL is relative to the API prefix
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scheme_name="JWT",
    description="JWT Bearer token authentication",
    auto_error=True,  # Raises 401 if token is missing
)

# Optional OAuth2 scheme - doesn't raise error if token is missing
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scheme_name="JWT",
    auto_error=False,
)

# API Key header for service-to-service authentication
api_key_header = APIKeyHeader(
    name="X-API-Key",
    scheme_name="API Key",
    description="API key for service-to-service authentication",
    auto_error=False,
)


async def validate_token(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> dict:
    """Validate JWT token and return payload.

    This is the main token validation dependency used in protected routes.

    Args:
        token: JWT token from Authorization header.

    Returns:
        Decoded token payload as dictionary.

    Raises:
        HTTPException: 401 if token is invalid or expired.
    """
    try:
        payload = decode_token(token, verify_type="access")
        return payload.model_dump()
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except TokenInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def validate_token_optional(
    token: Annotated[str | None, Depends(oauth2_scheme_optional)],
) -> dict | None:
    """Optionally validate JWT token.

    Use this for routes that work differently for authenticated vs anonymous users.

    Args:
        token: Optional JWT token from Authorization header.

    Returns:
        Decoded token payload if valid, None if missing or invalid.
    """
    if not token:
        return None

    try:
        payload = decode_token(token, verify_type="access")
        return payload.model_dump()
    except (TokenExpiredError, TokenInvalidError):
        return None


async def validate_api_key(
    api_key: Annotated[str | None, Depends(api_key_header)],
) -> str | None:
    """Validate API key for service-to-service authentication.

    Args:
        api_key: API key from X-API-Key header.

    Returns:
        The API key if valid, None if missing.

    Raises:
        HTTPException: 401 if API key is invalid.
    """
    if not api_key:
        return None

    settings = get_settings()

    # Check against configured service API keys
    # In production, this would validate against a database or secret store
    if api_key not in settings.SERVICE_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return api_key


async def validate_token_or_api_key(
    token_payload: Annotated[dict | None, Depends(validate_token_optional)],
    api_key: Annotated[str | None, Depends(validate_api_key)],
) -> dict:
    """Validate either JWT token or API key.

    Useful for endpoints that accept both user and service authentication.

    Args:
        token_payload: Optional JWT token payload.
        api_key: Optional API key.

    Returns:
        Token payload if JWT, or synthetic payload for API key.

    Raises:
        HTTPException: 401 if neither token nor API key is valid.
    """
    if token_payload:
        return token_payload

    if api_key:
        # Create a synthetic payload for API key authentication
        return {
            "sub": f"service:{api_key[:8]}",
            "type": "api_key",
            "roles": ["service"],
            "permissions": [],
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
