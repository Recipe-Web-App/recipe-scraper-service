"""Unit tests for admin endpoints.

Tests cover:
- Cache clear endpoint function
- Error handling
- Success scenarios with mocked Redis
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.admin import clear_cache_endpoint
from app.auth.dependencies import CurrentUser


pytestmark = pytest.mark.unit


class TestClearCacheEndpoint:
    """Tests for clear cache endpoint function."""

    @pytest.fixture
    def admin_user(self) -> CurrentUser:
        """Create an admin user for testing."""
        return CurrentUser(
            id="admin-user-123",
            roles=["admin"],
            permissions=["admin:system"],
            token_type="access",
        )

    @pytest.fixture
    def service_user(self) -> CurrentUser:
        """Create a service user for testing."""
        return CurrentUser(
            id="service-account-789",
            roles=["service"],
            permissions=["admin:system"],
            token_type="access",
        )

    @pytest.mark.asyncio
    async def test_clears_cache_successfully(self, admin_user: CurrentUser) -> None:
        """Should clear cache and return success message."""
        with patch(
            "app.api.v1.endpoints.admin.clear_cache",
            new_callable=AsyncMock,
        ) as mock_clear:
            result = await clear_cache_endpoint(admin_user)

            mock_clear.assert_called_once()
            assert result.message == "Cache cleared successfully"

    @pytest.mark.asyncio
    async def test_clears_cache_with_service_role(
        self,
        service_user: CurrentUser,
    ) -> None:
        """Should clear cache for service accounts."""
        with patch(
            "app.api.v1.endpoints.admin.clear_cache",
            new_callable=AsyncMock,
        ) as mock_clear:
            result = await clear_cache_endpoint(service_user)

            mock_clear.assert_called_once()
            assert result.message == "Cache cleared successfully"

    @pytest.mark.asyncio
    async def test_handles_redis_not_initialized(
        self,
        admin_user: CurrentUser,
    ) -> None:
        """Should return 503 when Redis is not initialized."""
        with patch(
            "app.api.v1.endpoints.admin.clear_cache",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Redis not initialized"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await clear_cache_endpoint(admin_user)

            assert exc_info.value.status_code == 503
            assert exc_info.value.detail["error"] == "SERVICE_UNAVAILABLE"
            assert "not available" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_handles_redis_connection_error(
        self,
        admin_user: CurrentUser,
    ) -> None:
        """Should return 503 when Redis connection fails."""
        with patch(
            "app.api.v1.endpoints.admin.clear_cache",
            new_callable=AsyncMock,
            side_effect=Exception("Connection refused"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await clear_cache_endpoint(admin_user)

            assert exc_info.value.status_code == 503
            assert exc_info.value.detail["error"] == "SERVICE_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_logs_user_info_on_request(
        self,
        admin_user: CurrentUser,
    ) -> None:
        """Should log user info when clearing cache."""
        with (
            patch(
                "app.api.v1.endpoints.admin.clear_cache",
                new_callable=AsyncMock,
            ),
            patch("app.api.v1.endpoints.admin.logger") as mock_logger,
        ):
            await clear_cache_endpoint(admin_user)

            # Verify logging calls
            assert mock_logger.info.call_count >= 2
            call_args_list = [str(call) for call in mock_logger.info.call_args_list]
            assert any("Cache clear requested" in call for call in call_args_list)
            assert any("Cache cleared successfully" in call for call in call_args_list)
