"""Authentication endpoints.

Provides OAuth2 password flow authentication:
- Login (token generation)
- Token refresh
- Token info/verification
- Logout (token revocation - requires Redis)
"""

from __future__ import annotations

from typing import Annotated, Final

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.dependencies import CurrentUser, get_current_user
from app.auth.jwt import (
    TokenExpiredError,
    TokenInvalidError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import Settings, get_settings
from app.schemas.auth import RefreshTokenRequest, TokenInfo, TokenResponse


# OAuth2 bearer token type (standard value per RFC 6749)
BEARER: Final[str] = "bearer"

# Demo credentials (REMOVE IN PRODUCTION - use proper auth service)
_DEMO_EMAIL: Final[str] = "demo@example.com"
_DEMO_PASSWORD: Final[str] = "demo1234"  # noqa: S105


router = APIRouter(prefix="/auth", tags=["auth"])


# NOTE: This is a simplified implementation for demonstration.
# In production, you would:
# 1. Store users in a database
# 2. Hash passwords with bcrypt/argon2
# 3. Implement proper user lookup
# 4. Add rate limiting to prevent brute force attacks


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login for access token",
    description="OAuth2 compatible token login, get an access token for future requests.",
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends(OAuth2PasswordRequestForm)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """Authenticate user and return access/refresh tokens.

    This endpoint follows the OAuth2 password flow specification.
    The username field can accept either email or username.
    """
    # TODO: Replace with actual user authentication
    # This is a placeholder that demonstrates the token flow
    # In production:
    # 1. Look up user by email/username
    # 2. Verify password hash
    # 3. Check if user is active
    # 4. Get user's roles and permissions

    # Placeholder authentication (REMOVE IN PRODUCTION)
    if form_data.username != _DEMO_EMAIL or form_data.password != _DEMO_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens with user data
    user_id = "demo-user-id"
    roles = ["user"]
    permissions: list[str] = []

    access_token = create_access_token(
        subject=user_id,
        roles=roles,
        permissions=permissions,
    )

    refresh_token = create_refresh_token(subject=user_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type=BEARER,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Get a new access token using a valid refresh token.",
)
async def refresh_token(
    request: RefreshTokenRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """Refresh access token using refresh token.

    This allows clients to get new access tokens without re-authenticating.
    """
    try:
        payload = decode_token(request.refresh_token, verify_type="refresh")
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except TokenInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    # TODO: Check if refresh token is revoked (requires Redis)
    # TODO: Look up current user roles/permissions from database

    # Create new tokens
    access_token = create_access_token(
        subject=payload.sub,
        roles=payload.roles,
        permissions=payload.permissions,
    )

    new_refresh_token = create_refresh_token(subject=payload.sub)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type=BEARER,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get(
    "/me",
    response_model=TokenInfo,
    summary="Get current user info",
    description="Get information about the currently authenticated user from their token.",
)
async def get_current_user_info(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> TokenInfo:
    """Get information about the current user from their access token.

    This is useful for:
    - Verifying token validity
    - Getting user roles/permissions for frontend authorization
    - Debugging authentication issues
    """
    return TokenInfo(
        sub=current_user.id,
        exp=0,  # Would need to extract from actual token
        iat=0,  # Would need to extract from actual token
        type=current_user.token_type,
        roles=current_user.roles,
        permissions=current_user.permissions,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout / revoke tokens",
    description="Revoke the current access and refresh tokens.",
)
async def logout(
    _current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> None:
    """Logout the current user by revoking their tokens.

    Note: Full token revocation requires Redis for storing revoked tokens.
    This will be implemented in Phase 4 (Caching & Rate Limiting).
    """
    # TODO: Add token to revocation list in Redis
    # This requires:
    # 1. Extracting the JTI (JWT ID) from the token
    # 2. Storing it in Redis with TTL matching token expiration
    # 3. Checking revocation list in token validation

    # For now, logout is a no-op on the server side
    # Clients should discard their tokens
    return
