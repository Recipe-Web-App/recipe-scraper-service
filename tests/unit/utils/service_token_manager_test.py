"""Unit tests for ServiceTokenManager."""

import base64
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException

from app.exceptions.custom_exceptions import DownstreamAuthenticationError
from app.utils.service_token_manager import ServiceTokenManager


@pytest.fixture
def mock_settings() -> Any:
    """Mock settings with OAuth2 credentials."""
    with patch("app.utils.service_token_manager.settings") as mock:
        mock.oauth2_client_id = "test-client-id"
        mock.oauth2_client_secret = "test-client-secret"  # pragma: allowlist secret
        yield mock


@pytest.fixture
def token_manager(mock_settings: Any) -> ServiceTokenManager:
    """Create a ServiceTokenManager instance for testing."""
    return ServiceTokenManager()


@pytest.fixture
def valid_token_response() -> dict[str, Any]:
    """Mock valid token response from auth service."""
    return {
        "access_token": "test-access-token-12345",
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "notification:admin",
    }


class TestServiceTokenManager:
    """Test suite for ServiceTokenManager."""

    @pytest.mark.asyncio
    async def test_get_service_token_success(
        self,
        token_manager: ServiceTokenManager,
        valid_token_response: dict[str, Any],
    ) -> None:
        """Test successful token acquisition."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = valid_token_response

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        token_manager._http_client = mock_client

        # Request token
        token = await token_manager.get_service_token(scope="notification:admin")

        # Verify
        assert token == "test-access-token-12345"
        assert token_manager._access_token == "test-access-token-12345"
        assert token_manager._token_scope == "notification:admin"
        assert token_manager._token_expires_at is not None

        # Verify HTTP call was made correctly
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "grant_type" in call_args.kwargs["data"]
        assert call_args.kwargs["data"]["grant_type"] == "client_credentials"
        assert call_args.kwargs["data"]["scope"] == "notification:admin"

    @pytest.mark.asyncio
    async def test_get_service_token_uses_stored_token(
        self,
        token_manager: ServiceTokenManager,
        valid_token_response: dict[str, Any],
    ) -> None:
        """Test that stored token is reused if still valid."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = valid_token_response

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        token_manager._http_client = mock_client

        # First request - should fetch from auth service
        token1 = await token_manager.get_service_token(scope="notification:admin")

        # Second request with same scope - should use stored token
        token2 = await token_manager.get_service_token(scope="notification:admin")

        # Verify same token returned
        assert token1 == token2

        # Verify HTTP call was only made once
        assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_get_service_token_refreshes_expired_token(
        self,
        token_manager: ServiceTokenManager,
        valid_token_response: dict[str, Any],
    ) -> None:
        """Test that expired token is refreshed."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = valid_token_response

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        token_manager._http_client = mock_client

        # Set an expired token
        token_manager._access_token = "old-token"
        token_manager._token_expires_at = datetime.now(UTC) - timedelta(seconds=10)
        token_manager._token_scope = "notification:admin"

        # Request token - should refresh
        token = await token_manager.get_service_token(scope="notification:admin")

        # Verify new token
        assert token == "test-access-token-12345"
        assert token != "old-token"
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_service_token_different_scope(
        self,
        token_manager: ServiceTokenManager,
        valid_token_response: dict[str, Any],
    ) -> None:
        """Test that different scopes request new tokens."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = valid_token_response

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        token_manager._http_client = mock_client

        # Request token with first scope
        await token_manager.get_service_token(scope="notification:admin")

        # Request token with different scope - should fetch new token
        await token_manager.get_service_token(scope="user:read")

        # Verify HTTP call was made twice
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_get_service_token_no_scope(
        self,
        token_manager: ServiceTokenManager,
        valid_token_response: dict[str, Any],
    ) -> None:
        """Test token request without scope."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = valid_token_response

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        token_manager._http_client = mock_client

        # Request token without scope
        token = await token_manager.get_service_token()

        # Verify
        assert token == "test-access-token-12345"
        assert token_manager._token_scope is None

        # Verify scope was not in request
        call_args = mock_client.post.call_args
        assert "scope" not in call_args.kwargs["data"]

    @pytest.mark.asyncio
    async def test_request_token_401_unauthorized(
        self,
        token_manager: ServiceTokenManager,
    ) -> None:
        """Test handling of 401 Unauthorized error."""
        # Mock HTTP response with 401
        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        token_manager._http_client = mock_client

        # Request token - should raise DownstreamAuthenticationError
        with pytest.raises(DownstreamAuthenticationError) as exc_info:
            await token_manager.get_service_token()

        assert exc_info.value.service_name == "auth-service"
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_request_token_500_server_error(
        self,
        token_manager: ServiceTokenManager,
    ) -> None:
        """Test handling of 500 server error."""
        # Mock HTTP response with 500
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        token_manager._http_client = mock_client

        # Request token - should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await token_manager.get_service_token()

        assert exc_info.value.status_code == 503
        assert "unavailable" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_request_token_connection_error(
        self,
        token_manager: ServiceTokenManager,
    ) -> None:
        """Test handling of connection error."""
        # Mock connection error
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        token_manager._http_client = mock_client

        # Request token - should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await token_manager.get_service_token()

        assert exc_info.value.status_code == 503
        assert "connection error" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_request_token_timeout(
        self,
        token_manager: ServiceTokenManager,
    ) -> None:
        """Test handling of request timeout."""
        # Mock timeout error
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("Request timeout")
        token_manager._http_client = mock_client

        # Request token - should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await token_manager.get_service_token()

        assert exc_info.value.status_code == 503

    def test_build_basic_auth_header(
        self, token_manager: ServiceTokenManager, mock_settings: Any
    ) -> None:
        """Test Basic Auth header construction."""
        header = token_manager._build_basic_auth_header()

        # Verify header format
        assert header.startswith("Basic ")

        # Decode and verify credentials
        encoded_part = header.split(" ")[1]
        decoded = base64.b64decode(encoded_part).decode("utf-8")
        assert decoded == "test-client-id:test-client-secret"

    def test_build_basic_auth_header_special_characters(
        self, token_manager: ServiceTokenManager
    ) -> None:
        """Test Basic Auth header with special characters in credentials."""
        with patch("app.utils.service_token_manager.settings") as mock_settings:
            mock_settings.oauth2_client_id = "client:id@123"
            mock_settings.oauth2_client_secret = (
                "secret!@#$%"  # pragma: allowlist secret
            )

            header = token_manager._build_basic_auth_header()

            # Decode and verify credentials are properly encoded
            encoded_part = header.split(" ")[1]
            decoded = base64.b64decode(encoded_part).decode("utf-8")
            assert decoded == "client:id@123:secret!@#$%"

    def test_build_basic_auth_header_missing_credentials(
        self, token_manager: ServiceTokenManager
    ) -> None:
        """Test error when credentials are not configured."""
        with patch("app.utils.service_token_manager.settings") as mock_settings:
            mock_settings.oauth2_client_id = ""
            mock_settings.oauth2_client_secret = ""

            with pytest.raises(ValueError) as exc_info:
                token_manager._build_basic_auth_header()

            assert "not configured" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_close_http_client(self, token_manager: ServiceTokenManager) -> None:
        """Test closing HTTP client."""
        # Create mock client
        mock_client = AsyncMock()
        token_manager._http_client = mock_client

        # Close
        await token_manager.close()

        # Verify client was closed
        mock_client.aclose.assert_called_once()
        assert token_manager._http_client is None

    @pytest.mark.asyncio
    async def test_http_client_creation(
        self, token_manager: ServiceTokenManager
    ) -> None:
        """Test HTTP client is created on first use."""
        assert token_manager._http_client is None

        client = await token_manager._get_http_client()

        assert client is not None
        assert isinstance(client, httpx.AsyncClient)

        # Verify same client returned on subsequent calls
        client2 = await token_manager._get_http_client()
        assert client2 is client
