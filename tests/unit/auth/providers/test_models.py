"""Unit tests for auth provider models.

Tests cover:
- AuthResult model creation and immutability
- IntrospectionResponse properties (scopes, audience_list)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.auth.providers.models import AuthResult, IntrospectionResponse


pytestmark = pytest.mark.unit


# =============================================================================
# AuthResult Tests
# =============================================================================


class TestAuthResult:
    """Tests for AuthResult model."""

    def test_create_with_required_fields(self) -> None:
        """Should create AuthResult with only required fields."""
        result = AuthResult(user_id="user-123")

        assert result.user_id == "user-123"
        assert result.roles == []
        assert result.permissions == []
        assert result.scopes == []
        assert result.token_type == "access"

    def test_create_with_all_fields(self) -> None:
        """Should create AuthResult with all fields."""
        result = AuthResult(
            user_id="user-123",
            roles=["admin", "user"],
            permissions=["read", "write"],
            scopes=["openid", "profile"],
            token_type="bearer",
            issuer="https://auth.example.com",
            audience=["api"],
            expires_at=1234567890,
            issued_at=1234567800,
            raw_claims={"custom": "value"},
        )

        assert result.user_id == "user-123"
        assert result.roles == ["admin", "user"]
        assert result.permissions == ["read", "write"]
        assert result.issuer == "https://auth.example.com"
        assert result.audience == ["api"]
        assert result.expires_at == 1234567890
        assert result.raw_claims == {"custom": "value"}

    def test_is_immutable(self) -> None:
        """Should be frozen/immutable after creation."""
        result = AuthResult(user_id="user-123")

        with pytest.raises(ValidationError, match="frozen"):
            result.user_id = "different-user"


# =============================================================================
# IntrospectionResponse Tests
# =============================================================================


class TestIntrospectionResponse:
    """Tests for IntrospectionResponse model."""

    def test_create_active_token(self) -> None:
        """Should create response for active token."""
        response = IntrospectionResponse(
            active=True,
            sub="user-123",
            scope="openid profile email",
            client_id="my-client",
            token_type="Bearer",
            exp=1234567890,
            iat=1234567800,
            iss="https://auth.example.com",
        )

        assert response.active is True
        assert response.sub == "user-123"
        assert response.scope == "openid profile email"

    def test_create_inactive_token(self) -> None:
        """Should create response for inactive token."""
        response = IntrospectionResponse(active=False)

        assert response.active is False
        assert response.sub is None
        assert response.scope is None


class TestIntrospectionResponseScopes:
    """Tests for IntrospectionResponse.scopes property."""

    def test_scopes_empty_when_scope_none(self) -> None:
        """Should return empty list when scope is None."""
        response = IntrospectionResponse(active=True, scope=None)

        assert response.scopes == []

    def test_scopes_empty_when_scope_empty_string(self) -> None:
        """Should return empty list when scope is empty string."""
        response = IntrospectionResponse(active=True, scope="")

        assert response.scopes == []

    def test_scopes_single_scope(self) -> None:
        """Should parse single scope."""
        response = IntrospectionResponse(active=True, scope="openid")

        assert response.scopes == ["openid"]

    def test_scopes_multiple_scopes(self) -> None:
        """Should parse multiple space-separated scopes."""
        response = IntrospectionResponse(active=True, scope="openid profile email")

        assert response.scopes == ["openid", "profile", "email"]

    def test_scopes_with_extra_spaces(self) -> None:
        """Should handle multiple spaces between scopes."""
        response = IntrospectionResponse(active=True, scope="openid  profile   email")

        # split() without args handles multiple spaces
        assert "openid" in response.scopes
        assert "profile" in response.scopes
        assert "email" in response.scopes


class TestIntrospectionResponseAudienceList:
    """Tests for IntrospectionResponse.audience_list property."""

    def test_audience_list_empty_when_aud_none(self) -> None:
        """Should return empty list when aud is None."""
        response = IntrospectionResponse(active=True, aud=None)

        assert response.audience_list == []

    def test_audience_list_empty_when_aud_empty_list(self) -> None:
        """Should return empty list when aud is empty list."""
        response = IntrospectionResponse(active=True, aud=[])

        assert response.audience_list == []

    def test_audience_list_from_string(self) -> None:
        """Should wrap single string in list."""
        response = IntrospectionResponse(active=True, aud="https://api.example.com")

        assert response.audience_list == ["https://api.example.com"]

    def test_audience_list_from_list(self) -> None:
        """Should return list as-is."""
        response = IntrospectionResponse(
            active=True,
            aud=["https://api1.example.com", "https://api2.example.com"],
        )

        assert response.audience_list == [
            "https://api1.example.com",
            "https://api2.example.com",
        ]

    def test_audience_list_single_item_list(self) -> None:
        """Should return single-item list as-is."""
        response = IntrospectionResponse(
            active=True,
            aud=["https://api.example.com"],
        )

        assert response.audience_list == ["https://api.example.com"]
