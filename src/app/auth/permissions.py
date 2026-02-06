"""Role-Based Access Control (RBAC) system.

This module defines roles and permissions for the application.
Permissions are granular actions, while roles are collections of permissions.
"""

from __future__ import annotations

from enum import StrEnum


class Permission(StrEnum):
    """Application permissions.

    Permissions follow the pattern: resource:action
    """

    # Recipe permissions
    RECIPE_READ = "recipe:read"
    RECIPE_CREATE = "recipe:create"
    RECIPE_UPDATE = "recipe:update"
    RECIPE_DELETE = "recipe:delete"
    RECIPE_SCRAPE = "recipe:scrape"

    # User permissions
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # Admin permissions
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"
    ADMIN_USERS = "admin:users"
    ADMIN_SYSTEM = "admin:system"

    # API key permissions
    API_KEY_READ = "api_key:read"
    API_KEY_CREATE = "api_key:create"
    API_KEY_REVOKE = "api_key:revoke"


class Role(StrEnum):
    """Application roles.

    Each role has a set of associated permissions.
    """

    # Basic user - can read and create recipes
    USER = "user"

    # Premium user - can also scrape recipes
    PREMIUM = "premium"

    # Moderator - can manage all recipes
    MODERATOR = "moderator"

    # Admin - full access
    ADMIN = "admin"

    # Service account - for internal services
    SERVICE = "service"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.USER: {
        Permission.RECIPE_READ,
        Permission.RECIPE_CREATE,
        Permission.RECIPE_UPDATE,  # Own recipes only - enforced in handlers
        Permission.RECIPE_DELETE,  # Own recipes only - enforced in handlers
        Permission.USER_READ,  # Own profile only
        Permission.USER_UPDATE,  # Own profile only
    },
    Role.PREMIUM: {
        # Inherits all USER permissions
        Permission.RECIPE_READ,
        Permission.RECIPE_CREATE,
        Permission.RECIPE_UPDATE,
        Permission.RECIPE_DELETE,
        Permission.RECIPE_SCRAPE,  # Premium feature
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.API_KEY_READ,
        Permission.API_KEY_CREATE,
    },
    Role.MODERATOR: {
        # All recipe permissions without ownership restriction
        Permission.RECIPE_READ,
        Permission.RECIPE_CREATE,
        Permission.RECIPE_UPDATE,
        Permission.RECIPE_DELETE,
        Permission.RECIPE_SCRAPE,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.API_KEY_READ,
        Permission.API_KEY_CREATE,
        Permission.API_KEY_REVOKE,
    },
    Role.ADMIN: {
        # Full access
        *Permission,
    },
    Role.SERVICE: {
        # Service accounts can read everything and perform system operations
        Permission.RECIPE_READ,
        Permission.RECIPE_SCRAPE,
        Permission.USER_READ,
        Permission.ADMIN_READ,
        Permission.ADMIN_SYSTEM,
    },
}


def get_permissions_for_role(role: Role | str) -> set[Permission]:
    """Get all permissions associated with a role.

    Args:
        role: The role to get permissions for.

    Returns:
        Set of permissions for the role.
    """
    if isinstance(role, str):
        try:
            role = Role(role)
        except ValueError:
            return set()

    return ROLE_PERMISSIONS.get(role, set())


def get_permissions_for_roles(roles: list[Role | str]) -> set[Permission]:
    """Get all permissions for a list of roles.

    Args:
        roles: List of roles to get permissions for.

    Returns:
        Combined set of permissions from all roles.
    """
    permissions: set[Permission] = set()
    for role in roles:
        permissions.update(get_permissions_for_role(role))
    return permissions


def has_permission(
    user_roles: list[str],
    user_permissions: list[str],
    required_permission: Permission | str,
) -> bool:
    """Check if user has a specific permission.

    Permission can come from:
    1. Direct user permissions
    2. Permissions inherited from roles

    Args:
        user_roles: List of user's roles.
        user_permissions: List of user's direct permissions.
        required_permission: The permission to check.

    Returns:
        True if user has the permission, False otherwise.
    """
    required = str(required_permission)

    # Check direct permissions
    if required in user_permissions:
        return True

    # Check role-based permissions
    role_permissions = get_permissions_for_roles(user_roles)
    return required in {str(p) for p in role_permissions}


def has_any_permission(
    user_roles: list[str],
    user_permissions: list[str],
    required_permissions: list[Permission | str],
) -> bool:
    """Check if user has any of the specified permissions.

    Args:
        user_roles: List of user's roles.
        user_permissions: List of user's direct permissions.
        required_permissions: List of permissions, user needs at least one.

    Returns:
        True if user has any of the permissions, False otherwise.
    """
    return any(
        has_permission(user_roles, user_permissions, perm)
        for perm in required_permissions
    )


def has_all_permissions(
    user_roles: list[str],
    user_permissions: list[str],
    required_permissions: list[Permission | str],
) -> bool:
    """Check if user has all of the specified permissions.

    Args:
        user_roles: List of user's roles.
        user_permissions: List of user's direct permissions.
        required_permissions: List of permissions, user needs all of them.

    Returns:
        True if user has all permissions, False otherwise.
    """
    return all(
        has_permission(user_roles, user_permissions, perm)
        for perm in required_permissions
    )


def has_role(user_roles: list[str], required_role: Role | str) -> bool:
    """Check if user has a specific role.

    Args:
        user_roles: List of user's roles.
        required_role: The role to check.

    Returns:
        True if user has the role, False otherwise.
    """
    return str(required_role) in user_roles


def has_any_role(user_roles: list[str], required_roles: list[Role | str]) -> bool:
    """Check if user has any of the specified roles.

    Args:
        user_roles: List of user's roles.
        required_roles: List of roles, user needs at least one.

    Returns:
        True if user has any of the roles, False otherwise.
    """
    return any(str(role) in user_roles for role in required_roles)
