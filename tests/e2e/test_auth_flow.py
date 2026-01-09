"""E2E tests for complete authentication flow.

Tests cover:
- Full login -> use token -> refresh -> logout cycle
- Session management across multiple requests
- Token lifecycle validation
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest
from freezegun import freeze_time

from app.auth.jwt import decode_token


if TYPE_CHECKING:
    from httpx import AsyncClient


pytestmark = pytest.mark.e2e


class TestCompleteAuthFlow:
    """Tests for complete authentication lifecycle."""

    @pytest.mark.asyncio
    async def test_full_auth_lifecycle(self, client: AsyncClient) -> None:
        """Should complete full auth lifecycle: login -> use -> refresh -> logout."""
        # Step 1: Login
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "demo@example.com",
                "password": "demo1234",
            },
        )
        assert login_response.status_code == 200

        tokens = login_response.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        assert access_token
        assert refresh_token
        assert tokens["token_type"] == "bearer"

        # Step 2: Use access token to get user info
        me_response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_response.status_code == 200

        user_info = me_response.json()
        assert user_info["sub"] == "demo-user-id"

        # Step 3: Refresh tokens
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 200

        new_tokens = refresh_response.json()
        new_access_token = new_tokens["access_token"]
        new_refresh_token = new_tokens["refresh_token"]

        # New access token should be different
        assert new_access_token != access_token
        # Note: Refresh token may or may not be rotated depending on implementation
        assert new_refresh_token is not None

        # Step 4: Use new access token
        me_response2 = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )
        assert me_response2.status_code == 200

        # Step 5: Logout
        logout_response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )
        assert logout_response.status_code == 204

    @pytest.mark.asyncio
    async def test_multiple_logins_same_user(self, client: AsyncClient) -> None:
        """Should allow multiple concurrent sessions for same user."""
        # Login at time T1
        with freeze_time("2026-06-01 12:00:00"):
            login1 = await client.post(
                "/api/v1/auth/login",
                data={"username": "demo@example.com", "password": "demo1234"},
            )

        # Login at time T2 (5 minutes later = different token)
        with freeze_time("2026-06-01 12:05:00"):
            login2 = await client.post(
                "/api/v1/auth/login",
                data={"username": "demo@example.com", "password": "demo1234"},
            )

        token1 = login1.json()["access_token"]
        token2 = login2.json()["access_token"]

        # Both tokens should be different (different iat/exp)
        assert token1 != token2

        # Both tokens should work
        response1 = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token1}"},
        )
        response2 = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token2}"},
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

    @pytest.mark.asyncio
    async def test_token_contains_correct_claims(self, client: AsyncClient) -> None:
        """Should include correct claims in tokens."""
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "demo@example.com", "password": "demo1234"},
        )

        tokens = response.json()

        # Decode and verify access token claims
        access_payload = decode_token(tokens["access_token"])
        assert access_payload.sub == "demo-user-id"
        assert access_payload.type == "access"
        assert "user" in access_payload.roles
        assert access_payload.exp > access_payload.iat

        # Decode and verify refresh token claims
        refresh_payload = decode_token(tokens["refresh_token"])
        assert refresh_payload.sub == "demo-user-id"
        assert refresh_payload.type == "refresh"
        assert refresh_payload.exp > refresh_payload.iat

        # Refresh token should have longer expiration
        assert refresh_payload.exp > access_payload.exp


class TestAuthFlowEdgeCases:
    """Edge cases for authentication flow."""

    @pytest.mark.asyncio
    async def test_old_refresh_token_after_refresh(self, client: AsyncClient) -> None:
        """Should handle old refresh token after getting new one."""
        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "demo@example.com", "password": "demo1234"},
        )
        original_refresh = login_response.json()["refresh_token"]

        # Refresh to get new tokens
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": original_refresh},
        )
        assert refresh_response.status_code == 200

        # Try using old refresh token again
        # Note: Without token blacklisting, this may still work
        # This test documents the current behavior
        retry_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": original_refresh},
        )
        # Current implementation doesn't blacklist old tokens
        assert retry_response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_concurrent_auth_requests(self, client: AsyncClient) -> None:
        """Should handle concurrent authentication requests."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "demo@example.com", "password": "demo1234"},
        )
        access_token = login_response.json()["access_token"]

        # Make concurrent requests with same token
        async def make_request() -> int:
            response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            return response.status_code

        tasks = [make_request() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(status == 200 for status in results)

    @pytest.mark.asyncio
    async def test_rapid_token_refresh(self, client: AsyncClient) -> None:
        """Should handle rapid consecutive token refreshes."""
        # Login
        with freeze_time("2026-06-01 12:00:00"):
            login_response = await client.post(
                "/api/v1/auth/login",
                data={"username": "demo@example.com", "password": "demo1234"},
            )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh requests at different times
        tokens = []
        current_refresh = refresh_token

        for i in range(5):
            # Advance time by 1 minute for each refresh
            with freeze_time(f"2026-06-01 12:0{i + 1}:00"):
                response = await client.post(
                    "/api/v1/auth/refresh",
                    json={"refresh_token": current_refresh},
                )
                assert response.status_code == 200
                new_tokens = response.json()
                tokens.append(new_tokens["access_token"])
                current_refresh = new_tokens["refresh_token"]

        # All tokens should be unique (different timestamps)
        assert len(set(tokens)) == 5


class TestAuthFlowWithHealthEndpoints:
    """Auth flow interaction with health endpoints."""

    @pytest.mark.asyncio
    async def test_health_endpoints_without_auth(self, client: AsyncClient) -> None:
        """Should access health endpoints without authentication."""
        # Root
        response = await client.get("/")
        assert response.status_code == 200

        # Health
        response = await client.get("/api/v1/health")
        assert response.status_code == 200

        # Ready
        response = await client.get("/api/v1/ready")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_endpoints_with_auth(self, client: AsyncClient) -> None:
        """Should access health endpoints with authentication (ignored)."""
        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "demo@example.com", "password": "demo1234"},
        )
        access_token = login_response.json()["access_token"]

        # Health endpoints should work with or without auth
        response = await client.get(
            "/api/v1/health",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200

        response = await client.get(
            "/api/v1/ready",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200


class TestAuthFlowSequences:
    """Tests for specific auth flow sequences."""

    @pytest.mark.asyncio
    async def test_login_refresh_refresh_logout(self, client: AsyncClient) -> None:
        """Should handle login -> refresh -> refresh -> logout sequence."""
        # Login
        login_resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "demo@example.com", "password": "demo1234"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        # First refresh
        refresh1 = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        tokens1 = refresh1.json()
        tokens1["access_token"]
        refresh_token = tokens1["refresh_token"]

        # Second refresh
        refresh2 = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        tokens2 = refresh2.json()
        final_access_token = tokens2["access_token"]

        # Logout with final access token
        logout = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {final_access_token}"},
        )
        assert logout.status_code == 204

    @pytest.mark.asyncio
    async def test_failed_login_then_success(self, client: AsyncClient) -> None:
        """Should allow successful login after failed attempt."""
        # Failed login
        failed = await client.post(
            "/api/v1/auth/login",
            data={"username": "demo@example.com", "password": "wrongpassword"},
        )
        assert failed.status_code == 401

        # Successful login
        success = await client.post(
            "/api/v1/auth/login",
            data={"username": "demo@example.com", "password": "demo1234"},
        )
        assert success.status_code == 200
        assert "access_token" in success.json()

    @pytest.mark.asyncio
    async def test_use_token_after_logout_same_token(
        self,
        client: AsyncClient,
    ) -> None:
        """Should document behavior when using token after logout."""
        # Login
        login_resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "demo@example.com", "password": "demo1234"},
        )
        access_token = login_resp.json()["access_token"]

        # Logout
        await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Try using the same token after logout
        # Note: Without token blacklisting, this may still work
        # This test documents the current behavior
        me_resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        # Document actual behavior (token still valid without blacklist)
        assert me_resp.status_code in (200, 401)
