"""Unit tests for HeaderAuthProvider."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.auth.providers.exceptions import AuthenticationError
from app.auth.providers.header import HeaderAuthProvider


pytestmark = pytest.mark.unit


class TestHeaderAuthProvider:
    """Tests for HeaderAuthProvider."""

    @pytest.fixture
    def provider(self) -> HeaderAuthProvider:
        """Create a HeaderAuthProvider instance with defaults."""
        return HeaderAuthProvider()

    @pytest.fixture
    def mock_request(self) -> MagicMock:
        """Create a mock request with headers."""
        request = MagicMock()
        request.headers = {
            "X-User-ID": "test-user-123",
            "X-User-Roles": "user,premium",
            "X-User-Permissions": "recipe:read,recipe:write",
        }
        return request

    @pytest.mark.asyncio
    async def test_extracts_user_from_headers(
        self, provider: HeaderAuthProvider, mock_request: MagicMock
    ) -> None:
        """Should extract user info from request headers."""
        result = await provider.validate_token("", request=mock_request)

        assert result.user_id == "test-user-123"
        assert "user" in result.roles
        assert "premium" in result.roles
        assert "recipe:read" in result.permissions
        assert "recipe:write" in result.permissions
        assert result.token_type == "header"

    @pytest.mark.asyncio
    async def test_raises_when_no_request(self, provider: HeaderAuthProvider) -> None:
        """Should raise AuthenticationError when request is None."""
        with pytest.raises(AuthenticationError, match="requires request"):
            await provider.validate_token("")

    @pytest.mark.asyncio
    async def test_raises_when_user_id_missing(
        self, provider: HeaderAuthProvider
    ) -> None:
        """Should raise AuthenticationError when X-User-ID header is missing."""
        request = MagicMock()
        request.headers = {}  # No X-User-ID

        with pytest.raises(AuthenticationError, match="Missing required header"):
            await provider.validate_token("", request=request)

    @pytest.mark.asyncio
    async def test_uses_default_roles_when_header_missing(
        self, provider: HeaderAuthProvider
    ) -> None:
        """Should use default roles when X-User-Roles header is missing."""
        request = MagicMock()
        request.headers = {"X-User-ID": "test-user"}

        result = await provider.validate_token("", request=request)

        assert result.user_id == "test-user"
        assert result.roles == ["user"]  # Default role

    @pytest.mark.asyncio
    async def test_custom_header_names(self) -> None:
        """Should use custom header names when configured."""
        provider = HeaderAuthProvider(
            user_id_header="X-Custom-User",
            roles_header="X-Custom-Roles",
            permissions_header="X-Custom-Perms",
        )

        request = MagicMock()
        request.headers = {
            "X-Custom-User": "custom-user-id",
            "X-Custom-Roles": "admin",
            "X-Custom-Perms": "all:access",
        }

        result = await provider.validate_token("", request=request)

        assert result.user_id == "custom-user-id"
        assert result.roles == ["admin"]
        assert result.permissions == ["all:access"]

    @pytest.mark.asyncio
    async def test_custom_default_roles(self) -> None:
        """Should use custom default roles when configured."""
        provider = HeaderAuthProvider(default_roles=["guest", "viewer"])

        request = MagicMock()
        request.headers = {"X-User-ID": "test-user"}

        result = await provider.validate_token("", request=request)

        assert result.roles == ["guest", "viewer"]

    @pytest.mark.asyncio
    async def test_empty_roles_header_uses_defaults(
        self, provider: HeaderAuthProvider
    ) -> None:
        """Should use defaults when roles header is empty."""
        request = MagicMock()
        request.headers = {
            "X-User-ID": "test-user",
            "X-User-Roles": "",  # Empty
        }

        result = await provider.validate_token("", request=request)

        assert result.roles == ["user"]

    @pytest.mark.asyncio
    async def test_parses_whitespace_in_headers(
        self, provider: HeaderAuthProvider
    ) -> None:
        """Should handle whitespace in comma-separated values."""
        request = MagicMock()
        request.headers = {
            "X-User-ID": "test-user",
            "X-User-Roles": " admin , moderator , user ",
        }

        result = await provider.validate_token("", request=request)

        assert result.roles == ["admin", "moderator", "user"]

    @pytest.mark.asyncio
    async def test_provider_name(self, provider: HeaderAuthProvider) -> None:
        """Should return correct provider name."""
        assert provider.provider_name == "header"

    @pytest.mark.asyncio
    async def test_initialize(self, provider: HeaderAuthProvider) -> None:
        """Should initialize without error."""
        await provider.initialize()
        assert provider._initialized is True

    @pytest.mark.asyncio
    async def test_shutdown(self, provider: HeaderAuthProvider) -> None:
        """Should shutdown without error."""
        await provider.initialize()
        await provider.shutdown()
        assert provider._initialized is False

    @pytest.mark.asyncio
    async def test_ignores_token_parameter(
        self, provider: HeaderAuthProvider, mock_request: MagicMock
    ) -> None:
        """Should ignore the token parameter entirely."""
        result1 = await provider.validate_token("some-token", request=mock_request)
        result2 = await provider.validate_token("different-token", request=mock_request)

        assert result1.user_id == result2.user_id

    @pytest.mark.asyncio
    async def test_returns_empty_scopes(
        self, provider: HeaderAuthProvider, mock_request: MagicMock
    ) -> None:
        """Should return empty scopes (not used in header mode)."""
        result = await provider.validate_token("", request=mock_request)

        assert result.scopes == []

    @pytest.mark.asyncio
    async def test_no_expiration_info(
        self, provider: HeaderAuthProvider, mock_request: MagicMock
    ) -> None:
        """Should have no expiration info (headers are per-request)."""
        result = await provider.validate_token("", request=mock_request)

        assert result.expires_at is None
        assert result.issued_at is None
