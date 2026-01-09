"""Unit tests for authentication dependencies.

Tests cover:
- CurrentUser model
- Permission and role requirements
- Convenience functions
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.auth.dependencies import (
    DEFAULT_JWT_TYPE,
    CurrentUser,
    RequireAdmin,
    RequireModerator,
    RequirePermissions,
    RequirePremium,
    RequireRoles,
    require_permissions,
    require_roles,
)
from app.auth.permissions import Permission, Role


pytestmark = pytest.mark.unit


class TestCurrentUser:
    """Tests for CurrentUser model."""

    def test_creates_with_required_fields(self) -> None:
        """Should create with just ID."""
        user = CurrentUser(id="user-123")

        assert user.id == "user-123"
        assert user.roles == []
        assert user.permissions == []
        assert user.token_type == DEFAULT_JWT_TYPE

    def test_creates_with_all_fields(self) -> None:
        """Should create with all fields."""
        user = CurrentUser(
            id="user-123",
            roles=["admin", "user"],
            permissions=["recipe:read", "recipe:update"],
            token_type="access",
        )

        assert user.id == "user-123"
        assert user.roles == ["admin", "user"]
        assert user.permissions == ["recipe:read", "recipe:update"]
        assert user.token_type == "access"

    def test_from_token_payload(self) -> None:
        """Should create from token payload."""
        payload = {
            "sub": "user-456",
            "roles": ["admin"],
            "permissions": ["user:read"],
            "type": "access",
        }

        user = CurrentUser.from_token_payload(payload)

        assert user.id == "user-456"
        assert user.roles == ["admin"]
        assert user.permissions == ["user:read"]
        assert user.token_type == "access"

    def test_from_token_payload_with_defaults(self) -> None:
        """Should use defaults for missing payload fields."""
        payload = {}

        user = CurrentUser.from_token_payload(payload)

        assert user.id == ""
        assert user.roles == []
        assert user.permissions == []
        assert user.token_type == "access"

    def test_has_permission_with_direct_permission(self) -> None:
        """Should check direct permissions."""
        user = CurrentUser(
            id="user-123",
            permissions=["recipe:read", "recipe:update"],
        )

        assert user.has_permission(Permission.RECIPE_READ) is True
        assert user.has_permission(Permission.RECIPE_DELETE) is False

    def test_has_permission_via_role(self) -> None:
        """Should check permissions via role."""
        user = CurrentUser(
            id="user-123",
            roles=["admin"],
        )

        # Admin role should have all permissions
        assert user.has_permission(Permission.RECIPE_READ) is True
        assert user.has_permission(Permission.ADMIN_WRITE) is True

    def test_has_role(self) -> None:
        """Should check if user has specific role."""
        user = CurrentUser(
            id="user-123",
            roles=["admin", "user"],
        )

        assert user.has_role(Role.ADMIN) is True
        assert user.has_role(Role.USER) is True
        assert user.has_role(Role.MODERATOR) is False

    def test_has_role_with_string(self) -> None:
        """Should check role with string value."""
        user = CurrentUser(
            id="user-123",
            roles=["admin"],
        )

        assert user.has_role("admin") is True
        assert user.has_role("user") is False

    def test_is_admin(self) -> None:
        """Should check admin status."""
        admin_user = CurrentUser(id="admin-1", roles=["admin"])
        regular_user = CurrentUser(id="user-1", roles=["user"])

        assert admin_user.is_admin() is True
        assert regular_user.is_admin() is False


class TestRequirePermissions:
    """Tests for RequirePermissions dependency."""

    def test_init_with_single_permission(self) -> None:
        """Should initialize with single permission."""
        req = RequirePermissions(Permission.RECIPE_READ)

        assert req.permissions == [Permission.RECIPE_READ]
        assert req.require_all is False

    def test_init_with_multiple_permissions(self) -> None:
        """Should initialize with multiple permissions."""
        req = RequirePermissions(Permission.RECIPE_READ, Permission.RECIPE_UPDATE)

        assert len(req.permissions) == 2
        assert Permission.RECIPE_READ in req.permissions
        assert Permission.RECIPE_UPDATE in req.permissions

    def test_init_with_require_all(self) -> None:
        """Should initialize with require_all flag."""
        req = RequirePermissions(Permission.RECIPE_READ, require_all=True)

        assert req.require_all is True

    @pytest.mark.asyncio
    async def test_allows_user_with_permission(self) -> None:
        """Should allow user with required permission."""
        req = RequirePermissions(Permission.RECIPE_READ)
        user = CurrentUser(id="user-1", permissions=["recipe:read"])

        result = await req(user)

        assert result is user

    @pytest.mark.asyncio
    async def test_allows_user_with_any_permission(self) -> None:
        """Should allow user with any of the required permissions."""
        req = RequirePermissions(Permission.RECIPE_READ, Permission.RECIPE_UPDATE)
        user = CurrentUser(id="user-1", permissions=["recipe:read"])

        result = await req(user)

        assert result is user

    @pytest.mark.asyncio
    async def test_denies_user_without_permission(self) -> None:
        """Should deny user without required permission."""
        req = RequirePermissions(Permission.RECIPE_READ)
        user = CurrentUser(id="user-1", permissions=[])

        with pytest.raises(HTTPException) as exc_info:
            await req(user)

        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_all_needs_all_permissions(self) -> None:
        """Should require all permissions when require_all=True."""
        req = RequirePermissions(
            Permission.RECIPE_READ, Permission.RECIPE_UPDATE, require_all=True
        )
        user = CurrentUser(id="user-1", permissions=["recipe:read"])

        with pytest.raises(HTTPException) as exc_info:
            await req(user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_all_allows_with_all_permissions(self) -> None:
        """Should allow user with all required permissions."""
        req = RequirePermissions(
            Permission.RECIPE_READ, Permission.RECIPE_UPDATE, require_all=True
        )
        user = CurrentUser(id="user-1", permissions=["recipe:read", "recipe:update"])

        result = await req(user)

        assert result is user


class TestRequireRoles:
    """Tests for RequireRoles dependency."""

    def test_init_with_single_role(self) -> None:
        """Should initialize with single role."""
        req = RequireRoles(Role.ADMIN)

        assert req.roles == [Role.ADMIN]
        assert req.require_all is False

    def test_init_with_multiple_roles(self) -> None:
        """Should initialize with multiple roles."""
        req = RequireRoles(Role.ADMIN, Role.MODERATOR)

        assert len(req.roles) == 2

    @pytest.mark.asyncio
    async def test_allows_user_with_role(self) -> None:
        """Should allow user with required role."""
        req = RequireRoles(Role.ADMIN)
        user = CurrentUser(id="user-1", roles=["admin"])

        result = await req(user)

        assert result is user

    @pytest.mark.asyncio
    async def test_allows_user_with_any_role(self) -> None:
        """Should allow user with any of the required roles."""
        req = RequireRoles(Role.ADMIN, Role.MODERATOR)
        user = CurrentUser(id="user-1", roles=["moderator"])

        result = await req(user)

        assert result is user

    @pytest.mark.asyncio
    async def test_denies_user_without_role(self) -> None:
        """Should deny user without required role."""
        req = RequireRoles(Role.ADMIN)
        user = CurrentUser(id="user-1", roles=["user"])

        with pytest.raises(HTTPException) as exc_info:
            await req(user)

        assert exc_info.value.status_code == 403
        assert "Insufficient role" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_all_needs_all_roles(self) -> None:
        """Should require all roles when require_all=True."""
        req = RequireRoles(Role.ADMIN, Role.MODERATOR, require_all=True)
        user = CurrentUser(id="user-1", roles=["admin"])

        with pytest.raises(HTTPException) as exc_info:
            await req(user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_all_allows_with_all_roles(self) -> None:
        """Should allow user with all required roles."""
        req = RequireRoles(Role.ADMIN, Role.MODERATOR, require_all=True)
        user = CurrentUser(id="user-1", roles=["admin", "moderator"])

        result = await req(user)

        assert result is user


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_require_permissions_creates_dependency(self) -> None:
        """Should create RequirePermissions instance."""
        dep = require_permissions(Permission.RECIPE_READ, require_all=True)

        assert isinstance(dep, RequirePermissions)
        assert dep.require_all is True

    def test_require_roles_creates_dependency(self) -> None:
        """Should create RequireRoles instance."""
        dep = require_roles(Role.ADMIN, require_all=False)

        assert isinstance(dep, RequireRoles)
        assert dep.require_all is False


class TestPrebuiltDependencies:
    """Tests for pre-built dependency instances."""

    def test_require_admin_exists(self) -> None:
        """RequireAdmin should be configured correctly."""
        assert isinstance(RequireAdmin, RequireRoles)
        assert Role.ADMIN in RequireAdmin.roles

    def test_require_moderator_exists(self) -> None:
        """RequireModerator should include admin and moderator roles."""
        assert isinstance(RequireModerator, RequireRoles)
        assert Role.ADMIN in RequireModerator.roles
        assert Role.MODERATOR in RequireModerator.roles

    def test_require_premium_exists(self) -> None:
        """RequirePremium should include admin and premium roles."""
        assert isinstance(RequirePremium, RequireRoles)
        assert Role.ADMIN in RequirePremium.roles
        assert Role.PREMIUM in RequirePremium.roles
