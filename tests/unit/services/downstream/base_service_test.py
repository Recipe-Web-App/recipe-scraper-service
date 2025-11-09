"""Unit tests for BaseServiceWithOAuth2."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.downstream.base_service import BaseServiceWithOAuth2
from app.utils.service_token_manager import ServiceTokenManager


@pytest.fixture
def mock_token_manager() -> AsyncMock:
    """Mock ServiceTokenManager for testing."""
    mock = AsyncMock(spec=ServiceTokenManager)
    mock.get_service_token = AsyncMock(return_value="test-token-12345")
    return mock


@pytest.fixture
def base_service(mock_token_manager: AsyncMock) -> BaseServiceWithOAuth2:
    """Create a BaseServiceWithOAuth2 instance for testing."""
    return BaseServiceWithOAuth2(
        token_manager=mock_token_manager,
        base_url="http://test-service:8000",
        scope="test:read",
    )


class TestBaseServiceWithOAuth2:
    """Test suite for BaseServiceWithOAuth2."""

    def test_init(
        self,
        base_service: BaseServiceWithOAuth2,
        mock_token_manager: AsyncMock,
    ) -> None:
        """Test service initialization."""
        assert base_service.token_manager is mock_token_manager
        assert base_service.base_url == "http://test-service:8000"
        assert base_service.scope == "test:read"
        assert base_service._client is None

    @pytest.mark.asyncio
    async def test_get_client_lazy_initialization(
        self, base_service: BaseServiceWithOAuth2
    ) -> None:
        """Test that HTTP client is lazily initialized on first access."""
        # Client should not exist initially
        assert base_service._client is None

        # Get client should create it
        client = await base_service._get_client()

        assert client is not None
        assert isinstance(client, httpx.AsyncClient)
        assert base_service._client is client

    @pytest.mark.asyncio
    async def test_get_client_reuses_instance(
        self, base_service: BaseServiceWithOAuth2
    ) -> None:
        """Test that subsequent calls reuse the same client instance."""
        client1 = await base_service._get_client()
        client2 = await base_service._get_client()

        assert client1 is client2

    @pytest.mark.asyncio
    async def test_get_client_configuration(
        self, base_service: BaseServiceWithOAuth2
    ) -> None:
        """Test that HTTP client is configured correctly."""
        client = await base_service._get_client()

        # Verify base URL (httpx adds trailing slash)
        assert str(client.base_url) in [
            "http://test-service:8000",
            "http://test-service:8000/",
        ]

        # Verify timeout
        assert client.timeout.read == 10.0

        # Verify event hooks are registered
        assert "request" in client.event_hooks
        assert len(client.event_hooks["request"]) == 1
        assert client.event_hooks["request"][0] == base_service._add_auth_token

    @pytest.mark.asyncio
    async def test_add_auth_token(
        self,
        base_service: BaseServiceWithOAuth2,
        mock_token_manager: AsyncMock,
    ) -> None:
        """Test that auth token is added to request headers."""
        # Create a mock request
        mock_request = MagicMock(spec=httpx.Request)
        mock_request.headers = {}
        mock_request.url = "http://test-service:8000/api/v1/test"

        # Call the auth hook
        await base_service._add_auth_token(mock_request)

        # Verify token was requested with correct scope
        mock_token_manager.get_service_token.assert_called_once_with(scope="test:read")

        # Verify Authorization header was set
        assert mock_request.headers["Authorization"] == "Bearer test-token-12345"

    @pytest.mark.asyncio
    async def test_add_auth_token_different_scopes(
        self, mock_token_manager: AsyncMock
    ) -> None:
        """Test that different service instances use different scopes."""
        service1 = BaseServiceWithOAuth2(
            token_manager=mock_token_manager,
            base_url="http://service1:8000",
            scope="service1:admin",
        )

        service2 = BaseServiceWithOAuth2(
            token_manager=mock_token_manager,
            base_url="http://service2:8000",
            scope="service2:read",
        )

        mock_request = MagicMock(spec=httpx.Request)
        mock_request.headers = {}
        mock_request.url = "http://test:8000/test"

        # Service 1 should request with its scope
        await service1._add_auth_token(mock_request)
        mock_token_manager.get_service_token.assert_called_with(scope="service1:admin")

        # Service 2 should request with its scope
        mock_token_manager.get_service_token.reset_mock()
        await service2._add_auth_token(mock_request)
        mock_token_manager.get_service_token.assert_called_with(scope="service2:read")

    @pytest.mark.asyncio
    async def test_close_client(self, base_service: BaseServiceWithOAuth2) -> None:
        """Test that close() properly closes the HTTP client."""
        # Create client
        client = await base_service._get_client()
        assert base_service._client is not None

        # Mock the aclose method
        with patch.object(client, "aclose", new_callable=AsyncMock) as mock_aclose:
            # Close the service
            await base_service.close()

            # Verify aclose was called
            mock_aclose.assert_called_once()

        # Verify client is set to None
        assert base_service._client is None

    @pytest.mark.asyncio
    async def test_close_when_no_client(
        self, base_service: BaseServiceWithOAuth2
    ) -> None:
        """Test that close() works even when client was never created."""
        # Client should not exist
        assert base_service._client is None

        # Close should not raise an error
        await base_service.close()

        # Client should still be None
        assert base_service._client is None

    @pytest.mark.asyncio
    async def test_auth_token_injected_via_event_hook(
        self,
        base_service: BaseServiceWithOAuth2,
        mock_token_manager: AsyncMock,
    ) -> None:
        """Test that event hook is properly registered and adds auth token."""
        # Get client (this sets up event hooks)
        client = await base_service._get_client()

        # Verify event hook is registered
        assert "request" in client.event_hooks
        assert base_service._add_auth_token in client.event_hooks["request"]

        # Create a mock request and manually trigger the event hook
        mock_request = MagicMock(spec=httpx.Request)
        mock_request.headers = {}
        mock_request.url = "http://test-service:8000/api/v1/test"

        # Trigger the event hook manually
        await base_service._add_auth_token(mock_request)

        # Verify token was added
        mock_token_manager.get_service_token.assert_called_with(scope="test:read")
        assert mock_request.headers["Authorization"] == "Bearer test-token-12345"
