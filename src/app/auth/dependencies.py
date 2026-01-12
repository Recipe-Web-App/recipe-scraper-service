"""FastAPI security dependencies.

This module provides reusable dependencies for authentication and authorization
in FastAPI route handlers.

The dependencies use the configured auth provider (introspection, local_jwt,
header, or disabled) to validate tokens and extract user information.
"""

from __future__ import annotations

from typing import Annotated, Any, Final

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from app.auth.permissions import (
    Permission,
    Role,
    has_any_permission,
    has_any_role,
    has_permission,
)
from app.auth.providers import (
    AuthenticationError,
    AuthResult,
    AuthServiceUnavailableError,
    TokenExpiredError,
    TokenInvalidError,
    get_auth_provider,
)
from app.core.config import AuthMode, get_settings


# Default JWT type for access tokens
DEFAULT_JWT_TYPE: Final[str] = "access"

# OAuth2 password bearer scheme (used for token extraction, not validation)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/oauth/token",  # External auth service OAuth2 endpoint
    scheme_name="JWT",
    description="JWT Bearer token authentication",
    auto_error=True,
)

oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/oauth/token",
    scheme_name="JWT",
    auto_error=False,
)


class CurrentUser(BaseModel):
    """Representation of the current authenticated user.

    This model is created from the JWT token payload.
    """

    id: str  # User ID from token subject
    roles: list[str] = []
    permissions: list[str] = []
    token_type: str = DEFAULT_JWT_TYPE

    @classmethod
    def from_token_payload(cls, payload: dict[str, Any]) -> CurrentUser:
        """Create CurrentUser from token payload.

        Args:
            payload: Decoded JWT token payload.

        Returns:
            CurrentUser instance.
        """
        return cls(
            id=payload.get("sub", ""),
            roles=payload.get("roles", []),
            permissions=payload.get("permissions", []),
            token_type=payload.get("type", "access"),
        )

    @classmethod
    def from_auth_result(cls, result: AuthResult) -> CurrentUser:
        """Create CurrentUser from AuthResult.

        Args:
            result: Authentication result from provider.

        Returns:
            CurrentUser instance.
        """
        return cls(
            id=result.user_id,
            roles=result.roles,
            permissions=result.permissions,
            token_type=result.token_type,
        )

    def has_permission(self, permission: Permission | str) -> bool:
        """Check if user has a specific permission."""
        return has_permission(self.roles, self.permissions, permission)

    def has_role(self, role: Role | str) -> bool:
        """Check if user has a specific role."""
        return str(role) in self.roles

    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.has_role(Role.ADMIN)


async def get_auth_result(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)],
) -> AuthResult:
    """Validate token using the configured auth provider.

    This is the core authentication dependency. It delegates to the
    configured auth provider (introspection, local_jwt, header, or disabled).

    Args:
        request: The incoming request (needed for header-based auth).
        token: Bearer token from Authorization header.

    Returns:
        AuthResult with validated user information.

    Raises:
        HTTPException: 401 if authentication fails, 503 if auth service unavailable.
    """
    settings = get_settings()

    # In header mode, token may be empty - that's OK
    if settings.auth_mode_enum == AuthMode.HEADER:
        token = ""  # Header provider ignores token

    try:
        provider = get_auth_provider()
        return await provider.validate_token(token, request)

    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    except TokenInvalidError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e) or "Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e) or "Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    except AuthServiceUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Authentication service unavailable: {e}",
        ) from None


async def get_auth_result_optional(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme_optional)],
) -> AuthResult | None:
    """Optionally validate token using the configured auth provider.

    Returns None if no token is provided instead of raising an error.

    Args:
        request: The incoming request.
        token: Optional bearer token.

    Returns:
        AuthResult if token is valid, None if no token provided.

    Raises:
        HTTPException: 401 if token is provided but invalid.
    """
    settings = get_settings()

    # In header mode, always try to authenticate (token is ignored)
    if settings.auth_mode_enum == AuthMode.HEADER:
        try:
            provider = get_auth_provider()
            return await provider.validate_token("", request)
        except AuthenticationError:
            return None  # No X-User-ID header is OK for optional auth

    # For other modes, no token means no auth
    if not token:
        return None

    try:
        provider = get_auth_provider()
        return await provider.validate_token(token, request)
    except (TokenExpiredError, TokenInvalidError, AuthenticationError):
        return None


async def get_current_user(
    auth_result: Annotated[AuthResult, Depends(get_auth_result)],
) -> CurrentUser:
    """Get the current authenticated user.

    This is the primary dependency for protected routes. It uses the
    configured auth provider to validate the token and returns a
    CurrentUser instance.

    Args:
        auth_result: Validated authentication result.

    Returns:
        CurrentUser instance.
    """
    return CurrentUser.from_auth_result(auth_result)


async def get_current_user_optional(
    auth_result: Annotated[AuthResult | None, Depends(get_auth_result_optional)],
) -> CurrentUser | None:
    """Optionally get the current authenticated user.

    Use this for routes that work for both authenticated and anonymous users.

    Args:
        auth_result: Optional authentication result.

    Returns:
        CurrentUser instance if authenticated, None otherwise.
    """
    if auth_result is None:
        return None

    return CurrentUser.from_auth_result(auth_result)


class RequirePermissions:
    """Dependency class for requiring specific permissions.

    Usage:
        @router.get("/recipes")
        async def list_recipes(
            user: Annotated[CurrentUser, Depends(RequirePermissions(Permission.RECIPE_READ))]
        ):
            ...
    """

    def __init__(
        self,
        *permissions: Permission | str,
        require_all: bool = False,
    ) -> None:
        """Initialize permission requirement.

        Args:
            permissions: Required permissions.
            require_all: If True, user must have ALL permissions.
                        If False, user needs at least one.
        """
        self.permissions = list(permissions)
        self.require_all = require_all

    async def __call__(
        self,
        user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        """Check if user has required permissions.

        Args:
            user: The current authenticated user.

        Returns:
            The user if authorized.

        Raises:
            HTTPException: 403 if user lacks required permissions.
        """
        if self.require_all:
            has_perms = all(user.has_permission(p) for p in self.permissions)
        else:
            has_perms = has_any_permission(
                user.roles, user.permissions, self.permissions
            )

        if not has_perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return user


class RequireRoles:
    """Dependency class for requiring specific roles.

    Usage:
        @router.get("/admin/users")
        async def list_users(
            user: Annotated[CurrentUser, Depends(RequireRoles(Role.ADMIN))]
        ):
            ...
    """

    def __init__(self, *roles: Role | str, require_all: bool = False) -> None:
        """Initialize role requirement.

        Args:
            roles: Required roles.
            require_all: If True, user must have ALL roles.
                        If False, user needs at least one.
        """
        self.roles = list(roles)
        self.require_all = require_all

    async def __call__(
        self,
        user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        """Check if user has required roles.

        Args:
            user: The current authenticated user.

        Returns:
            The user if authorized.

        Raises:
            HTTPException: 403 if user lacks required roles.
        """
        if self.require_all:
            has_roles = all(user.has_role(r) for r in self.roles)
        else:
            has_roles = has_any_role(user.roles, self.roles)

        if not has_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )

        return user


# Convenience aliases for common permission checks
def require_permissions(
    *permissions: Permission | str,
    require_all: bool = False,
) -> RequirePermissions:
    """Create a permission requirement dependency.

    Args:
        permissions: Required permissions.
        require_all: If True, user must have ALL permissions.

    Returns:
        RequirePermissions dependency instance.
    """
    return RequirePermissions(*permissions, require_all=require_all)


def require_roles(*roles: Role | str, require_all: bool = False) -> RequireRoles:
    """Create a role requirement dependency.

    Args:
        roles: Required roles.
        require_all: If True, user must have ALL roles.

    Returns:
        RequireRoles dependency instance.
    """
    return RequireRoles(*roles, require_all=require_all)


# Pre-built dependencies for common use cases
RequireAdmin = RequireRoles(Role.ADMIN)
RequireModerator = RequireRoles(Role.ADMIN, Role.MODERATOR)
RequirePremium = RequireRoles(Role.ADMIN, Role.PREMIUM)
