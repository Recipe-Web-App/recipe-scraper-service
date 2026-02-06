"""Unit tests for RBAC permissions.

Tests cover:
- Permission and Role enums
- Role to permissions mapping
- Permission checking functions
- Role checking functions
"""

from __future__ import annotations

import pytest

from app.auth.permissions import (
    ROLE_PERMISSIONS,
    Permission,
    Role,
    get_permissions_for_role,
    get_permissions_for_roles,
    has_all_permissions,
    has_any_permission,
    has_any_role,
    has_permission,
    has_role,
)


pytestmark = pytest.mark.unit


# =============================================================================
# Enum Tests
# =============================================================================


class TestPermissionEnum:
    """Tests for Permission enum."""

    def test_permission_values_follow_pattern(self):
        """All permissions should follow resource:action pattern."""
        for perm in Permission:
            assert ":" in str(perm), f"Permission {perm} doesn't follow pattern"

    def test_recipe_permissions_exist(self):
        """Should have all recipe permissions."""
        assert Permission.RECIPE_READ == "recipe:read"
        assert Permission.RECIPE_CREATE == "recipe:create"
        assert Permission.RECIPE_UPDATE == "recipe:update"
        assert Permission.RECIPE_DELETE == "recipe:delete"
        assert Permission.RECIPE_SCRAPE == "recipe:scrape"

    def test_user_permissions_exist(self):
        """Should have all user permissions."""
        assert Permission.USER_READ == "user:read"
        assert Permission.USER_UPDATE == "user:update"
        assert Permission.USER_DELETE == "user:delete"

    def test_admin_permissions_exist(self):
        """Should have all admin permissions."""
        assert Permission.ADMIN_READ == "admin:read"
        assert Permission.ADMIN_WRITE == "admin:write"
        assert Permission.ADMIN_USERS == "admin:users"
        assert Permission.ADMIN_SYSTEM == "admin:system"


class TestRoleEnum:
    """Tests for Role enum."""

    def test_all_roles_exist(self):
        """Should have all expected roles."""
        assert Role.USER == "user"
        assert Role.PREMIUM == "premium"
        assert Role.MODERATOR == "moderator"
        assert Role.ADMIN == "admin"
        assert Role.SERVICE == "service"

    def test_role_count(self):
        """Should have expected number of roles."""
        assert len(Role) == 5


# =============================================================================
# Role Permissions Mapping Tests
# =============================================================================


class TestRolePermissionsMapping:
    """Tests for ROLE_PERMISSIONS mapping."""

    def test_all_roles_have_permissions(self):
        """Every role should have permissions defined."""
        for role in Role:
            assert role in ROLE_PERMISSIONS, (
                f"Role {role} missing from ROLE_PERMISSIONS"
            )

    def test_user_role_permissions(self):
        """User role should have basic permissions."""
        user_perms = ROLE_PERMISSIONS[Role.USER]
        assert Permission.RECIPE_READ in user_perms
        assert Permission.RECIPE_CREATE in user_perms
        assert Permission.USER_READ in user_perms
        assert Permission.RECIPE_SCRAPE not in user_perms  # Premium only

    def test_premium_role_permissions(self):
        """Premium role should have scrape permission."""
        premium_perms = ROLE_PERMISSIONS[Role.PREMIUM]
        assert Permission.RECIPE_SCRAPE in premium_perms
        assert Permission.API_KEY_CREATE in premium_perms

    def test_admin_has_all_permissions(self):
        """Admin role should have all permissions."""
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        for perm in Permission:
            assert perm in admin_perms, f"Admin missing permission {perm}"

    def test_service_role_limited_permissions(self):
        """Service role should have specific limited permissions."""
        service_perms = ROLE_PERMISSIONS[Role.SERVICE]
        assert Permission.RECIPE_READ in service_perms
        assert Permission.ADMIN_SYSTEM in service_perms
        assert Permission.USER_DELETE not in service_perms


# =============================================================================
# get_permissions_for_role Tests
# =============================================================================


class TestGetPermissionsForRole:
    """Tests for get_permissions_for_role function."""

    def test_returns_permissions_for_role_enum(self):
        """Should return permissions when given Role enum."""
        perms = get_permissions_for_role(Role.USER)
        assert Permission.RECIPE_READ in perms

    def test_returns_permissions_for_role_string(self):
        """Should return permissions when given role string."""
        perms = get_permissions_for_role("user")
        assert Permission.RECIPE_READ in perms

    def test_returns_empty_for_invalid_role(self):
        """Should return empty set for invalid role."""
        perms = get_permissions_for_role("nonexistent-role")
        assert perms == set()


# =============================================================================
# get_permissions_for_roles Tests
# =============================================================================


class TestGetPermissionsForRoles:
    """Tests for get_permissions_for_roles function."""

    def test_combines_permissions_from_multiple_roles(self):
        """Should combine permissions from all roles."""
        perms = get_permissions_for_roles([Role.USER, Role.PREMIUM])

        # Should have USER permissions
        assert Permission.RECIPE_READ in perms
        # Should also have PREMIUM permissions
        assert Permission.RECIPE_SCRAPE in perms

    def test_handles_string_roles(self):
        """Should handle string role values."""
        perms = get_permissions_for_roles(["user", "premium"])

        assert Permission.RECIPE_READ in perms
        assert Permission.RECIPE_SCRAPE in perms

    def test_handles_empty_list(self):
        """Should return empty set for empty list."""
        perms = get_permissions_for_roles([])
        assert perms == set()

    def test_skips_invalid_roles(self):
        """Should skip invalid roles and continue."""
        perms = get_permissions_for_roles(["user", "invalid-role", "premium"])

        # Should still have valid role permissions
        assert Permission.RECIPE_READ in perms
        assert Permission.RECIPE_SCRAPE in perms


# =============================================================================
# has_permission Tests
# =============================================================================


class TestHasPermission:
    """Tests for has_permission function."""

    def test_returns_true_for_direct_permission(self):
        """Should return True when permission is in user's direct permissions."""
        result = has_permission(
            user_roles=[],
            user_permissions=["recipe:read"],
            required_permission=Permission.RECIPE_READ,
        )
        assert result is True

    def test_returns_true_for_role_permission(self):
        """Should return True when permission comes from role."""
        result = has_permission(
            user_roles=["user"],
            user_permissions=[],
            required_permission=Permission.RECIPE_READ,
        )
        assert result is True

    def test_returns_false_when_missing(self):
        """Should return False when permission is missing."""
        result = has_permission(
            user_roles=["user"],
            user_permissions=[],
            required_permission=Permission.ADMIN_WRITE,
        )
        assert result is False

    def test_handles_string_permission(self):
        """Should handle permission as string."""
        result = has_permission(
            user_roles=["user"],
            user_permissions=[],
            required_permission="recipe:read",
        )
        assert result is True

    def test_direct_permission_overrides_role(self):
        """Direct permission should be checked before role permissions."""
        result = has_permission(
            user_roles=[],  # No roles
            user_permissions=["admin:write"],  # But has direct permission
            required_permission=Permission.ADMIN_WRITE,
        )
        assert result is True


# =============================================================================
# has_any_permission Tests
# =============================================================================


class TestHasAnyPermission:
    """Tests for has_any_permission function."""

    def test_returns_true_when_has_one(self):
        """Should return True when user has any of the permissions."""
        result = has_any_permission(
            user_roles=["user"],
            user_permissions=[],
            required_permissions=[Permission.RECIPE_READ, Permission.ADMIN_WRITE],
        )
        assert result is True

    def test_returns_false_when_has_none(self):
        """Should return False when user has none of the permissions."""
        result = has_any_permission(
            user_roles=["user"],
            user_permissions=[],
            required_permissions=[Permission.ADMIN_WRITE, Permission.ADMIN_READ],
        )
        assert result is False

    def test_returns_false_for_empty_list(self):
        """Should return False for empty required permissions list."""
        result = has_any_permission(
            user_roles=["admin"],
            user_permissions=[],
            required_permissions=[],
        )
        assert result is False


# =============================================================================
# has_all_permissions Tests
# =============================================================================


class TestHasAllPermissions:
    """Tests for has_all_permissions function."""

    def test_returns_true_when_has_all(self):
        """Should return True when user has all permissions."""
        result = has_all_permissions(
            user_roles=["user"],
            user_permissions=[],
            required_permissions=[Permission.RECIPE_READ, Permission.RECIPE_CREATE],
        )
        assert result is True

    def test_returns_false_when_missing_one(self):
        """Should return False when user is missing any permission."""
        result = has_all_permissions(
            user_roles=["user"],
            user_permissions=[],
            required_permissions=[Permission.RECIPE_READ, Permission.ADMIN_WRITE],
        )
        assert result is False

    def test_returns_true_for_empty_list(self):
        """Should return True for empty required permissions list."""
        result = has_all_permissions(
            user_roles=[],
            user_permissions=[],
            required_permissions=[],
        )
        assert result is True


# =============================================================================
# has_role Tests
# =============================================================================


class TestHasRole:
    """Tests for has_role function."""

    def test_returns_true_when_has_role(self):
        """Should return True when user has the role."""
        result = has_role(
            user_roles=["user", "premium"],
            required_role=Role.USER,
        )
        assert result is True

    def test_returns_false_when_missing_role(self):
        """Should return False when user doesn't have the role."""
        result = has_role(
            user_roles=["user"],
            required_role=Role.ADMIN,
        )
        assert result is False

    def test_handles_string_role(self):
        """Should handle role as string."""
        result = has_role(
            user_roles=["admin"],
            required_role="admin",
        )
        assert result is True


# =============================================================================
# has_any_role Tests
# =============================================================================


class TestHasAnyRole:
    """Tests for has_any_role function."""

    def test_returns_true_when_has_one(self):
        """Should return True when user has any of the roles."""
        result = has_any_role(
            user_roles=["user"],
            required_roles=[Role.USER, Role.ADMIN],
        )
        assert result is True

    def test_returns_false_when_has_none(self):
        """Should return False when user has none of the roles."""
        result = has_any_role(
            user_roles=["user"],
            required_roles=[Role.ADMIN, Role.MODERATOR],
        )
        assert result is False

    def test_returns_false_for_empty_required_roles(self):
        """Should return False for empty required roles list."""
        result = has_any_role(
            user_roles=["admin"],
            required_roles=[],
        )
        assert result is False

    def test_returns_false_for_empty_user_roles(self):
        """Should return False for empty user roles."""
        result = has_any_role(
            user_roles=[],
            required_roles=[Role.USER],
        )
        assert result is False
