"""Unit tests for NotificationService."""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import httpx
import pytest

from app.services.downstream.notification_service import NotificationService
from app.utils.service_token_manager import ServiceTokenManager


@pytest.fixture
def mock_token_manager() -> AsyncMock:
    """Mock ServiceTokenManager for testing."""
    mock = AsyncMock(spec=ServiceTokenManager)
    mock.get_service_token = AsyncMock(return_value="test-token-12345")
    return mock


@pytest.fixture
def notification_service(mock_token_manager: AsyncMock) -> NotificationService:
    """Create a NotificationService instance for testing."""
    return NotificationService(token_manager=mock_token_manager)


@pytest.fixture
def notification_response() -> dict[str, int | str | list[dict[str, str]]]:
    """Sample BatchNotificationResponse from API."""
    return {
        "notifications": [
            {
                "notification_id": str(uuid4()),
                "recipient_id": str(uuid4()),
            },
            {
                "notification_id": str(uuid4()),
                "recipient_id": str(uuid4()),
            },
        ],
        "queued_count": 2,
        "message": "Notifications queued successfully",
    }


class TestNotificationService:
    """Test suite for NotificationService."""

    def test_init(
        self,
        notification_service: NotificationService,
        mock_token_manager: AsyncMock,
    ) -> None:
        """Test service initialization."""
        assert notification_service.token_manager is mock_token_manager
        assert notification_service.base_url == "http://notification-service:8000"
        assert notification_service.scope == "notification:admin"

    @pytest.mark.asyncio
    async def test_send_recipe_published_notification_success(
        self,
        notification_service: NotificationService,
        notification_response: dict[str, int | str | list[dict[str, str]]],
    ) -> None:
        """Test successful notification send."""
        recipe_id = 123
        follower_ids = [uuid4(), uuid4()]

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.json.return_value = notification_response

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        notification_service._client = mock_client

        # Call method
        result = await notification_service.send_recipe_published_notification(
            recipe_id, follower_ids
        )

        # Verify
        assert result is True
        mock_client.post.assert_called_once()

        # Verify request payload
        call_args = mock_client.post.call_args
        assert (
            call_args.args[0] == "/api/v1/notification/notifications/recipe-published"
        )
        assert "json" in call_args.kwargs
        payload = call_args.kwargs["json"]
        assert payload["recipe_id"] == recipe_id
        assert len(payload["recipient_ids"]) == 2

    @pytest.mark.asyncio
    async def test_send_recipe_published_notification_empty_followers(
        self,
        notification_service: NotificationService,
    ) -> None:
        """Test notification send with empty follower list."""
        recipe_id = 123
        follower_ids: list[UUID] = []

        # Call method - should return True without making API call
        result = await notification_service.send_recipe_published_notification(
            recipe_id, follower_ids
        )

        # Verify
        assert result is True
        # No HTTP client should have been created
        assert notification_service._client is None

    @pytest.mark.asyncio
    async def test_send_recipe_published_notification_single_follower(
        self,
        notification_service: NotificationService,
    ) -> None:
        """Test notification send with single follower."""
        recipe_id = 456
        follower_ids = [uuid4()]

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "notifications": [
                {
                    "notification_id": str(uuid4()),
                    "recipient_id": str(follower_ids[0]),
                }
            ],
            "queued_count": 1,
            "message": "Notification queued successfully",
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        notification_service._client = mock_client

        # Call method
        result = await notification_service.send_recipe_published_notification(
            recipe_id, follower_ids
        )

        # Verify
        assert result is True
        assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_send_recipe_published_notification_batching(
        self,
        notification_service: NotificationService,
    ) -> None:
        """Test batching with 150 followers (should split into 2 batches)."""
        recipe_id = 789
        follower_ids = [uuid4() for _ in range(150)]

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "notifications": [
                {"notification_id": str(uuid4()), "recipient_id": str(uuid4())}
                for _ in range(100)
            ],
            "queued_count": 100,
            "message": "Notifications queued successfully",
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        notification_service._client = mock_client

        # Call method
        result = await notification_service.send_recipe_published_notification(
            recipe_id, follower_ids
        )

        # Verify
        assert result is True
        # Should make 2 API calls (100 + 50)
        assert mock_client.post.call_count == 2

        # Verify first batch had 100 recipients
        first_call = mock_client.post.call_args_list[0]
        first_payload = first_call.kwargs["json"]
        assert len(first_payload["recipient_ids"]) == 100

        # Verify second batch had 50 recipients
        second_call = mock_client.post.call_args_list[1]
        second_payload = second_call.kwargs["json"]
        assert len(second_payload["recipient_ids"]) == 50

    @pytest.mark.asyncio
    async def test_send_recipe_published_notification_400_error(
        self,
        notification_service: NotificationService,
    ) -> None:
        """Test handling of 400 bad request error."""
        recipe_id = 123
        follower_ids = [uuid4()]

        # Mock 400 response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad request",
            request=MagicMock(),
            response=mock_response,
        )
        notification_service._client = mock_client

        # Call method - should return False
        result = await notification_service.send_recipe_published_notification(
            recipe_id, follower_ids
        )

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_send_recipe_published_notification_401_error(
        self,
        notification_service: NotificationService,
    ) -> None:
        """Test handling of 401 unauthorized error."""
        recipe_id = 123
        follower_ids = [uuid4()]

        # Mock 401 response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized",
            request=MagicMock(),
            response=mock_response,
        )
        notification_service._client = mock_client

        # Call method - should return False
        result = await notification_service.send_recipe_published_notification(
            recipe_id, follower_ids
        )

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_send_recipe_published_notification_429_rate_limit(
        self,
        notification_service: NotificationService,
    ) -> None:
        """Test handling of 429 rate limit error."""
        recipe_id = 123
        follower_ids = [uuid4()]

        # Mock 429 response
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate limit",
            request=MagicMock(),
            response=mock_response,
        )
        notification_service._client = mock_client

        # Call method - should return False
        result = await notification_service.send_recipe_published_notification(
            recipe_id, follower_ids
        )

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_send_recipe_published_notification_500_error(
        self,
        notification_service: NotificationService,
    ) -> None:
        """Test handling of 500 server error."""
        recipe_id = 123
        follower_ids = [uuid4()]

        # Mock 500 response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=mock_response,
        )
        notification_service._client = mock_client

        # Call method - should return False
        result = await notification_service.send_recipe_published_notification(
            recipe_id, follower_ids
        )

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_send_recipe_published_notification_connection_error(
        self,
        notification_service: NotificationService,
    ) -> None:
        """Test handling of connection error."""
        recipe_id = 123
        follower_ids = [uuid4()]

        # Mock connection error
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        notification_service._client = mock_client

        # Call method - should return False
        result = await notification_service.send_recipe_published_notification(
            recipe_id, follower_ids
        )

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_send_recipe_published_notification_timeout_error(
        self,
        notification_service: NotificationService,
    ) -> None:
        """Test handling of timeout error."""
        recipe_id = 123
        follower_ids = [uuid4()]

        # Mock timeout error
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.TimeoutException("Request timeout")
        )
        notification_service._client = mock_client

        # Call method - should return False
        result = await notification_service.send_recipe_published_notification(
            recipe_id, follower_ids
        )

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_send_recipe_published_notification_invalid_response(
        self,
        notification_service: NotificationService,
    ) -> None:
        """Test handling of invalid response format."""
        recipe_id = 123
        follower_ids = [uuid4()]

        # Mock invalid response
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "invalid_field": "invalid"
            # Missing required fields
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        notification_service._client = mock_client

        # Call method - should return False (pydantic validation error)
        result = await notification_service.send_recipe_published_notification(
            recipe_id, follower_ids
        )

        # Verify
        assert result is False
