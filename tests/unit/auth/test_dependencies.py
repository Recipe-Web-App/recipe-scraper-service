"""Unit tests for authentication dependencies.

Tests cover:
- CurrentUser model
- Permission and role requirements
- Convenience functions
- Async authentication dependencies
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

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
    get_auth_result,
    get_auth_result_optional,
    get_current_user,
    get_current_user_optional,
    require_permissions,
    require_roles,
)
from app.auth.permissions import Permission, Role
from app.auth.providers import (
    AuthenticationError,
    AuthResult,
    AuthServiceUnavailableError,
    TokenExpiredError,
    TokenInvalidError,
)


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


# =============================================================================
# Async Authentication Dependency Tests
# =============================================================================


class TestCurrentUserFromAuthResult:
    """Tests for CurrentUser.from_auth_result class method."""

    def test_maps_all_fields_correctly(self) -> None:
        """Should map all AuthResult fields to CurrentUser."""
        auth_result = AuthResult(
            user_id="user-789",
            roles=["admin", "user"],
            permissions=["recipe:read", "recipe:write"],
            token_type="access",
        )

        user = CurrentUser.from_auth_result(auth_result)

        assert user.id == "user-789"
        assert user.roles == ["admin", "user"]
        assert user.permissions == ["recipe:read", "recipe:write"]
        assert user.token_type == "access"

    def test_handles_empty_roles_and_permissions(self) -> None:
        """Should handle AuthResult with empty roles and permissions."""
        auth_result = AuthResult(
            user_id="user-empty",
            roles=[],
            permissions=[],
            token_type="access",
        )

        user = CurrentUser.from_auth_result(auth_result)

        assert user.id == "user-empty"
        assert user.roles == []
        assert user.permissions == []


class TestGetAuthResult:
    """Tests for get_auth_result async dependency."""

    @pytest.fixture
    def mock_request(self) -> MagicMock:
        """Create a mock FastAPI request."""
        return MagicMock()

    @pytest.fixture
    def mock_auth_result(self) -> AuthResult:
        """Create a mock authentication result."""
        return AuthResult(
            user_id="test-user-123",
            roles=["user"],
            permissions=["recipe:read"],
            token_type="access",
        )

    async def test_validates_token_successfully(
        self, mock_request: MagicMock, mock_auth_result: AuthResult
    ) -> None:
        """Should return AuthResult for valid token."""
        mock_provider = MagicMock()
        mock_provider.validate_token = AsyncMock(return_value=mock_auth_result)

        with (
            patch("app.auth.dependencies.get_settings") as mock_settings,
            patch(
                "app.auth.dependencies.get_auth_provider",
                return_value=mock_provider,
            ),
        ):
            mock_settings.return_value.auth_mode_enum.name = "LOCAL_JWT"

            result = await get_auth_result(mock_request, "valid-token")

        assert result == mock_auth_result
        mock_provider.validate_token.assert_called_once()

    async def test_header_mode_ignores_token(
        self, mock_request: MagicMock, mock_auth_result: AuthResult
    ) -> None:
        """Should set token to empty string in header mode."""
        from app.core.config import AuthMode

        mock_provider = MagicMock()
        mock_provider.validate_token = AsyncMock(return_value=mock_auth_result)
        mock_settings = MagicMock()
        mock_settings.auth_mode_enum = AuthMode.HEADER

        with (
            patch(
                "app.auth.dependencies.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "app.auth.dependencies.get_auth_provider",
                return_value=mock_provider,
            ),
        ):
            await get_auth_result(mock_request, "some-token")

        # In header mode, empty string should be passed
        mock_provider.validate_token.assert_called_once_with("", mock_request)

    async def test_raises_401_on_token_expired(self, mock_request: MagicMock) -> None:
        """Should raise 401 when token is expired."""
        mock_provider = MagicMock()
        mock_provider.validate_token = AsyncMock(side_effect=TokenExpiredError())

        with (
            patch("app.auth.dependencies.get_settings") as mock_settings,
            patch(
                "app.auth.dependencies.get_auth_provider",
                return_value=mock_provider,
            ),
        ):
            mock_settings.return_value.auth_mode_enum.name = "LOCAL_JWT"

            with pytest.raises(HTTPException) as exc_info:
                await get_auth_result(mock_request, "expired-token")

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    async def test_raises_401_on_token_invalid(self, mock_request: MagicMock) -> None:
        """Should raise 401 when token is invalid."""
        mock_provider = MagicMock()
        mock_provider.validate_token = AsyncMock(
            side_effect=TokenInvalidError("Malformed token")
        )

        with (
            patch("app.auth.dependencies.get_settings") as mock_settings,
            patch(
                "app.auth.dependencies.get_auth_provider",
                return_value=mock_provider,
            ),
        ):
            mock_settings.return_value.auth_mode_enum.name = "LOCAL_JWT"

            with pytest.raises(HTTPException) as exc_info:
                await get_auth_result(mock_request, "invalid-token")

        assert exc_info.value.status_code == 401
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    async def test_raises_401_on_authentication_error(
        self, mock_request: MagicMock
    ) -> None:
        """Should raise 401 on generic authentication error."""
        mock_provider = MagicMock()
        mock_provider.validate_token = AsyncMock(
            side_effect=AuthenticationError("Auth failed")
        )

        with (
            patch("app.auth.dependencies.get_settings") as mock_settings,
            patch(
                "app.auth.dependencies.get_auth_provider",
                return_value=mock_provider,
            ),
        ):
            mock_settings.return_value.auth_mode_enum.name = "LOCAL_JWT"

            with pytest.raises(HTTPException) as exc_info:
                await get_auth_result(mock_request, "bad-token")

        assert exc_info.value.status_code == 401

    async def test_raises_503_on_service_unavailable(
        self, mock_request: MagicMock
    ) -> None:
        """Should raise 503 when auth service is unavailable."""
        mock_provider = MagicMock()
        mock_provider.validate_token = AsyncMock(
            side_effect=AuthServiceUnavailableError("Service down")
        )

        with (
            patch("app.auth.dependencies.get_settings") as mock_settings,
            patch(
                "app.auth.dependencies.get_auth_provider",
                return_value=mock_provider,
            ),
        ):
            mock_settings.return_value.auth_mode_enum.name = "LOCAL_JWT"

            with pytest.raises(HTTPException) as exc_info:
                await get_auth_result(mock_request, "any-token")

        assert exc_info.value.status_code == 503
        assert "unavailable" in exc_info.value.detail.lower()


class TestGetAuthResultOptional:
    """Tests for get_auth_result_optional async dependency."""

    @pytest.fixture
    def mock_request(self) -> MagicMock:
        """Create a mock FastAPI request."""
        return MagicMock()

    @pytest.fixture
    def mock_auth_result(self) -> AuthResult:
        """Create a mock authentication result."""
        return AuthResult(
            user_id="test-user-456",
            roles=["user"],
            permissions=["recipe:read"],
            token_type="access",
        )

    async def test_returns_auth_result_for_valid_token(
        self, mock_request: MagicMock, mock_auth_result: AuthResult
    ) -> None:
        """Should return AuthResult for valid token."""
        mock_provider = MagicMock()
        mock_provider.validate_token = AsyncMock(return_value=mock_auth_result)

        with (
            patch("app.auth.dependencies.get_settings") as mock_settings,
            patch(
                "app.auth.dependencies.get_auth_provider",
                return_value=mock_provider,
            ),
        ):
            mock_settings.return_value.auth_mode_enum.name = "LOCAL_JWT"

            result = await get_auth_result_optional(mock_request, "valid-token")

        assert result == mock_auth_result

    async def test_returns_none_for_no_token(self, mock_request: MagicMock) -> None:
        """Should return None when no token provided."""
        with patch("app.auth.dependencies.get_settings") as mock_settings:
            mock_settings.return_value.auth_mode_enum.name = "LOCAL_JWT"

            result = await get_auth_result_optional(mock_request, None)

        assert result is None

    async def test_returns_none_on_token_expired(self, mock_request: MagicMock) -> None:
        """Should return None when token is expired (not raise)."""
        mock_provider = MagicMock()
        mock_provider.validate_token = AsyncMock(side_effect=TokenExpiredError())

        with (
            patch("app.auth.dependencies.get_settings") as mock_settings,
            patch(
                "app.auth.dependencies.get_auth_provider",
                return_value=mock_provider,
            ),
        ):
            mock_settings.return_value.auth_mode_enum.name = "LOCAL_JWT"

            result = await get_auth_result_optional(mock_request, "expired-token")

        assert result is None

    async def test_returns_none_on_token_invalid(self, mock_request: MagicMock) -> None:
        """Should return None when token is invalid (not raise)."""
        mock_provider = MagicMock()
        mock_provider.validate_token = AsyncMock(side_effect=TokenInvalidError())

        with (
            patch("app.auth.dependencies.get_settings") as mock_settings,
            patch(
                "app.auth.dependencies.get_auth_provider",
                return_value=mock_provider,
            ),
        ):
            mock_settings.return_value.auth_mode_enum.name = "LOCAL_JWT"

            result = await get_auth_result_optional(mock_request, "invalid-token")

        assert result is None

    async def test_header_mode_returns_none_on_auth_error(
        self, mock_request: MagicMock
    ) -> None:
        """Should return None in header mode when no X-User-ID header."""
        from app.core.config import AuthMode

        mock_provider = MagicMock()
        mock_provider.validate_token = AsyncMock(
            side_effect=AuthenticationError("No user header")
        )
        mock_settings = MagicMock()
        mock_settings.auth_mode_enum = AuthMode.HEADER

        with (
            patch(
                "app.auth.dependencies.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "app.auth.dependencies.get_auth_provider",
                return_value=mock_provider,
            ),
        ):
            result = await get_auth_result_optional(mock_request, None)

        assert result is None

    async def test_header_mode_returns_result_when_valid(
        self, mock_request: MagicMock, mock_auth_result: AuthResult
    ) -> None:
        """Should return AuthResult in header mode when valid."""
        from app.core.config import AuthMode

        mock_provider = MagicMock()
        mock_provider.validate_token = AsyncMock(return_value=mock_auth_result)
        mock_settings = MagicMock()
        mock_settings.auth_mode_enum = AuthMode.HEADER

        with (
            patch(
                "app.auth.dependencies.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "app.auth.dependencies.get_auth_provider",
                return_value=mock_provider,
            ),
        ):
            result = await get_auth_result_optional(mock_request, None)

        assert result == mock_auth_result


class TestGetCurrentUser:
    """Tests for get_current_user async dependency."""

    async def test_creates_current_user_from_auth_result(self) -> None:
        """Should convert AuthResult to CurrentUser."""
        auth_result = AuthResult(
            user_id="user-current-123",
            roles=["admin"],
            permissions=["recipe:read"],
            token_type="access",
        )

        user = await get_current_user(auth_result)

        assert isinstance(user, CurrentUser)
        assert user.id == "user-current-123"
        assert user.roles == ["admin"]
        assert user.permissions == ["recipe:read"]


class TestGetCurrentUserOptional:
    """Tests for get_current_user_optional async dependency."""

    async def test_creates_current_user_when_authenticated(self) -> None:
        """Should return CurrentUser when auth_result is provided."""
        auth_result = AuthResult(
            user_id="user-opt-123",
            roles=["user"],
            permissions=["recipe:read"],
            token_type="access",
        )

        user = await get_current_user_optional(auth_result)

        assert isinstance(user, CurrentUser)
        assert user.id == "user-opt-123"

    async def test_returns_none_when_not_authenticated(self) -> None:
        """Should return None when auth_result is None."""
        user = await get_current_user_optional(None)

        assert user is None
