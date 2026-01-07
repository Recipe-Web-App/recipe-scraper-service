"""JWT token handling.

This module provides functions for creating and validating JWT tokens
using PyJWT with RS256 algorithm support (recommended for production)
or HS256 for simpler setups.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from pydantic import BaseModel

from app.core.config import get_settings
from app.observability.logging import get_logger


logger = get_logger(__name__)


class TokenPayload(BaseModel):
    """JWT token payload model."""

    sub: str  # Subject (user ID)
    exp: datetime  # Expiration time
    iat: datetime  # Issued at
    jti: str | None = None  # JWT ID for token revocation
    type: str = "access"  # Token type: "access" or "refresh"
    roles: list[str] = []  # User roles for RBAC
    permissions: list[str] = []  # Direct permissions


class TokenError(Exception):
    """Base exception for token-related errors."""


class TokenExpiredError(TokenError):
    """Raised when a token has expired."""


class TokenInvalidError(TokenError):
    """Raised when a token is invalid."""


def create_access_token(
    subject: str,
    *,
    roles: list[str] | None = None,
    permissions: list[str] | None = None,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a new JWT access token.

    Args:
        subject: The subject of the token (typically user ID).
        roles: User roles for RBAC.
        permissions: Direct permissions granted to user.
        expires_delta: Custom expiration time. If None, uses default from settings.
        extra_claims: Additional claims to include in the token.

    Returns:
        Encoded JWT token string.
    """
    settings = get_settings()

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(UTC)
    expire = now + expires_delta

    payload = {
        "sub": subject,
        "exp": expire,
        "iat": now,
        "type": "access",
        "roles": roles or [],
        "permissions": permissions or [],
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(
    subject: str,
    *,
    expires_delta: timedelta | None = None,
    jti: str | None = None,
) -> str:
    """Create a new JWT refresh token.

    Refresh tokens have longer expiration and are used to obtain new access tokens.

    Args:
        subject: The subject of the token (typically user ID).
        expires_delta: Custom expiration time. If None, uses default from settings.
        jti: JWT ID for token revocation tracking.

    Returns:
        Encoded JWT refresh token string.
    """
    settings = get_settings()

    if expires_delta is None:
        expires_delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    now = datetime.now(UTC)
    expire = now + expires_delta

    payload = {
        "sub": subject,
        "exp": expire,
        "iat": now,
        "type": "refresh",
    }

    if jti:
        payload["jti"] = jti

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str, *, verify_type: str | None = None) -> TokenPayload:
    """Decode and validate a JWT token.

    Args:
        token: The JWT token string to decode.
        verify_type: If provided, verify the token is of this type ("access" or "refresh").

    Returns:
        TokenPayload containing the decoded token data.

    Raises:
        TokenExpiredError: If the token has expired.
        TokenInvalidError: If the token is invalid.
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        # Verify token type if specified
        if verify_type and payload.get("type") != verify_type:
            msg = (
                f"Invalid token type. Expected {verify_type}, got {payload.get('type')}"
            )
            raise TokenInvalidError(msg)

        return TokenPayload(**payload)

    except ExpiredSignatureError as e:
        logger.debug("Token expired", error=str(e))
        msg = "Token has expired"
        raise TokenExpiredError(msg) from e

    except JWTError as e:
        logger.warning("Invalid token", error=str(e))
        msg = "Invalid token"
        raise TokenInvalidError(msg) from e


def verify_token(token: str, *, verify_type: str | None = None) -> bool:
    """Verify if a token is valid without raising exceptions.

    Args:
        token: The JWT token string to verify.
        verify_type: If provided, verify the token is of this type.

    Returns:
        True if the token is valid, False otherwise.
    """
    try:
        decode_token(token, verify_type=verify_type)
    except TokenError:
        return False
    else:
        return True
