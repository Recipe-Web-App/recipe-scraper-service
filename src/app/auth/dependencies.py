"""FastAPI security dependencies.

This module provides reusable dependencies for authentication and authorization
in FastAPI route handlers.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.oauth2 import validate_token, validate_token_optional
from app.auth.permissions import (
    Permission,
    Role,
    has_any_permission,
    has_any_role,
    has_permission,
)


class CurrentUser(BaseModel):
    """Representation of the current authenticated user.

    This model is created from the JWT token payload.
    """

    id: str  # User ID from token subject
    roles: list[str] = []
    permissions: list[str] = []
    token_type: str = "access"

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

    def has_permission(self, permission: Permission | str) -> bool:
        """Check if user has a specific permission."""
        return has_permission(self.roles, self.permissions, permission)

    def has_role(self, role: Role | str) -> bool:
        """Check if user has a specific role."""
        return str(role) in self.roles

    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.has_role(Role.ADMIN)


async def get_current_user(
    payload: Annotated[dict, Depends(validate_token)],
) -> CurrentUser:
    """Get the current authenticated user.

    This is the primary dependency for protected routes.

    Args:
        payload: Validated JWT token payload.

    Returns:
        CurrentUser instance.

    Raises:
        HTTPException: 401 if user cannot be identified.
    """
    if not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser.from_token_payload(payload)


async def get_current_user_optional(
    payload: Annotated[dict | None, Depends(validate_token_optional)],
) -> CurrentUser | None:
    """Optionally get the current authenticated user.

    Use this for routes that work for both authenticated and anonymous users.

    Args:
        payload: Optional JWT token payload.

    Returns:
        CurrentUser instance if authenticated, None otherwise.
    """
    if not payload or not payload.get("sub"):
        return None

    return CurrentUser.from_token_payload(payload)


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
