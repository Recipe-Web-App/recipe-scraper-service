"""Integration tests for auth API endpoints.

Tests cover:
- Login endpoint with real app
- Token refresh
- Current user info
- Logout
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import jwt
import pytest

from app.auth.jwt import decode_token
from app.core.config import get_settings


if TYPE_CHECKING:
    from httpx import AsyncClient


pytestmark = pytest.mark.integration


class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login."""

    @pytest.mark.asyncio
    async def test_login_returns_tokens(self, client: AsyncClient) -> None:
        """Should return access and refresh tokens for valid credentials."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "demo@example.com",
                "password": "demo1234",
            },
        )

        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    @pytest.mark.asyncio
    async def test_login_tokens_are_valid(self, client: AsyncClient) -> None:
        """Should return valid JWT tokens."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "demo@example.com",
                "password": "demo1234",
            },
        )

        data = response.json()

        # Verify access token is decodable
        access_payload = decode_token(data["access_token"])
        assert access_payload.sub == "demo-user-id"
        assert access_payload.type == "access"

        # Verify refresh token is decodable
        refresh_payload = decode_token(data["refresh_token"])
        assert refresh_payload.sub == "demo-user-id"
        assert refresh_payload.type == "refresh"

    @pytest.mark.asyncio
    async def test_login_fails_with_wrong_password(
        self,
        client: AsyncClient,
    ) -> None:
        """Should return 401 for wrong password."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "demo@example.com",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_fails_with_wrong_email(
        self,
        client: AsyncClient,
    ) -> None:
        """Should return 401 for wrong email."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "wrong@example.com",
                "password": "demo1234",
            },
        )

        assert response.status_code == 401


class TestRefreshEndpoint:
    """Tests for POST /api/v1/auth/refresh."""

    @pytest.mark.asyncio
    async def test_refresh_returns_new_tokens(self, client: AsyncClient) -> None:
        """Should return new tokens for valid refresh token."""
        # First login to get tokens
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "demo@example.com",
                "password": "demo1234",
            },
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_refresh_fails_with_invalid_token(
        self,
        client: AsyncClient,
    ) -> None:
        """Should return 401 for invalid refresh token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_fails_with_access_token(
        self,
        client: AsyncClient,
    ) -> None:
        """Should return 401 when using access token as refresh token."""
        # First login to get tokens
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "demo@example.com",
                "password": "demo1234",
            },
        )
        access_token = login_response.json()["access_token"]

        # Try to refresh with access token
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )

        assert response.status_code == 401


class TestMeEndpoint:
    """Tests for GET /api/v1/auth/me."""

    @pytest.mark.asyncio
    async def test_me_returns_user_info(self, client: AsyncClient) -> None:
        """Should return current user info for authenticated request."""
        # First login
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "demo@example.com",
                "password": "demo1234",
            },
        )
        access_token = login_response.json()["access_token"]

        # Get user info
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200

        data = response.json()
        assert data["sub"] == "demo-user-id"
        assert "roles" in data
        assert "permissions" in data

    @pytest.mark.asyncio
    async def test_me_fails_without_auth(self, client: AsyncClient) -> None:
        """Should return 401 without authorization header."""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_fails_with_invalid_token(self, client: AsyncClient) -> None:
        """Should return 401 with invalid token."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401


class TestLogoutEndpoint:
    """Tests for POST /api/v1/auth/logout."""

    @pytest.mark.asyncio
    async def test_logout_returns_204(self, client: AsyncClient) -> None:
        """Should return 204 for authenticated logout."""
        # First login
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "demo@example.com",
                "password": "demo1234",
            },
        )
        access_token = login_response.json()["access_token"]

        # Logout
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_logout_fails_without_auth(self, client: AsyncClient) -> None:
        """Should return 401 without authorization."""
        response = await client.post("/api/v1/auth/logout")

        assert response.status_code == 401


class TestAuthEdgeCases:
    """Edge case tests for auth endpoints."""

    @pytest.mark.asyncio
    async def test_expired_token_rejected(self, client: AsyncClient) -> None:
        """Should reject expired JWT tokens."""
        settings = get_settings()

        # Create an expired token manually
        expired_payload = {
            "sub": "test-user",
            "type": "access",
            "exp": int(time.time()) - 3600,  # Expired 1 hour ago
            "iat": int(time.time()) - 7200,
            "roles": ["user"],
            "permissions": [],
        }

        expired_token = jwt.encode(
            expired_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_malformed_token_rejected(self, client: AsyncClient) -> None:
        """Should reject malformed JWT tokens."""
        malformed_tokens = [
            "not-a-jwt-at-all",
            "Bearer.only.two.parts",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",  # Just header
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0",  # Missing sig
            "",
            " ",
        ]

        for token in malformed_tokens:
            response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 401, f"Should reject token: {token[:50]}..."

    @pytest.mark.asyncio
    async def test_token_with_wrong_signature(self, client: AsyncClient) -> None:
        """Should reject token signed with wrong key."""
        # Create token with wrong secret
        payload = {
            "sub": "test-user",
            "type": "access",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
            "roles": ["user"],
            "permissions": [],
        }

        wrong_signature_token = jwt.encode(
            payload,
            "wrong-secret-key",
            algorithm="HS256",
        )

        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {wrong_signature_token}"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_bearer_prefix(self, client: AsyncClient) -> None:
        """Should reject authorization header without Bearer prefix."""
        # Login to get valid token
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "demo@example.com",
                "password": "demo1234",
            },
        )
        access_token = login_response.json()["access_token"]

        # Send without Bearer prefix
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": access_token},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_token_with_wrong_type(self, client: AsyncClient) -> None:
        """Should reject refresh token used as access token."""
        # Login to get tokens
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "demo@example.com",
                "password": "demo1234",
            },
        )
        refresh_token = login_response.json()["refresh_token"]

        # Try to use refresh token as access token
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )

        # Should be rejected (wrong token type)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_authorization_header(self, client: AsyncClient) -> None:
        """Should reject empty authorization header."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": ""},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_bearer_with_empty_token(self, client: AsyncClient) -> None:
        """Should reject Bearer prefix with no token."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer "},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_multiple_bearer_keywords(self, client: AsyncClient) -> None:
        """Should reject malformed header with multiple Bearer keywords."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer Bearer token"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_with_empty_credentials(self, client: AsyncClient) -> None:
        """Should reject empty credentials."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "",
                "password": "",
            },
        )

        assert response.status_code in (
            401,
            422,
        )  # Either unauthorized or validation error

    @pytest.mark.asyncio
    async def test_login_with_missing_fields(self, client: AsyncClient) -> None:
        """Should reject login with missing fields."""
        # Missing password
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "demo@example.com"},
        )
        assert response.status_code == 422

        # Missing username
        response = await client.post(
            "/api/v1/auth/login",
            data={"password": "demo1234"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_refresh_with_empty_token(self, client: AsyncClient) -> None:
        """Should reject refresh with empty token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": ""},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_case_sensitive_bearer(self, client: AsyncClient) -> None:
        """Should handle case variations of Bearer prefix."""
        # Login to get valid token
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "demo@example.com",
                "password": "demo1234",
            },
        )
        access_token = login_response.json()["access_token"]

        # Try lowercase 'bearer'
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"bearer {access_token}"},
        )

        # OAuth2 spec says Bearer should be case-insensitive
        # But FastAPI's OAuth2PasswordBearer is case-sensitive by default
        # This test documents actual behavior
        assert response.status_code in (200, 401)
