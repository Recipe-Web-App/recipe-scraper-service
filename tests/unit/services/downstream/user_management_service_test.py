"""Unit tests for UserManagementService."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import httpx
import pytest

from app.services.downstream.user_management_service import UserManagementService
from app.utils.service_token_manager import ServiceTokenManager


@pytest.fixture
def mock_token_manager() -> AsyncMock:
    """Mock ServiceTokenManager for testing."""
    mock = AsyncMock(spec=ServiceTokenManager)
    mock.get_service_token = AsyncMock(return_value="test-token-12345")
    return mock


@pytest.fixture
def user_management_service(
    mock_token_manager: AsyncMock,
) -> UserManagementService:
    """Create a UserManagementService instance for testing."""
    return UserManagementService(token_manager=mock_token_manager)


@pytest.fixture
def sample_user_data() -> dict[str, str | bool]:
    """Sample user data matching the API schema."""
    return {
        "userId": str(uuid4()),
        "username": "testuser",
        "email": "test@example.com",
        "fullName": "Test User",
        "bio": "A test user",
        "isActive": True,
        "createdAt": datetime.now(UTC).isoformat(),
        "updatedAt": datetime.now(UTC).isoformat(),
    }


@pytest.fixture
def followers_response(
    sample_user_data: dict[str, str | bool],
) -> dict[str, int | list[dict[str, str | bool]]]:
    """Sample GetFollowedUsersResponse from API."""
    follower1 = sample_user_data.copy()
    follower1["userId"] = str(uuid4())
    follower1["username"] = "follower1"

    follower2 = sample_user_data.copy()
    follower2["userId"] = str(uuid4())
    follower2["username"] = "follower2"

    return {
        "totalCount": 2,
        "followedUsers": [follower1, follower2],
        "limit": 100,
        "offset": 0,
    }


class TestUserManagementService:
    """Test suite for UserManagementService."""

    def test_init(
        self,
        user_management_service: UserManagementService,
        mock_token_manager: AsyncMock,
    ) -> None:
        """Test service initialization."""
        assert user_management_service.token_manager is mock_token_manager
        assert user_management_service.base_url == "http://sous-chef-proxy.local"
        assert user_management_service.scope == "user:read"

    @pytest.mark.asyncio
    async def test_get_follower_ids_success(
        self,
        user_management_service: UserManagementService,
        followers_response: dict[str, int | list[dict[str, str | bool]]],
    ) -> None:
        """Test successful retrieval of follower IDs."""
        user_id = uuid4()

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = followers_response

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        user_management_service._client = mock_client

        # Call method
        follower_ids = await user_management_service.get_follower_ids(user_id)

        # Verify
        assert len(follower_ids) == 2
        assert all(isinstance(fid, UUID) for fid in follower_ids)

        # Verify correct endpoint was called
        mock_client.get.assert_called_once_with(
            f"/api/v1/user-management/users/{user_id}/followers",
            params={"limit": 100},
        )

    @pytest.mark.asyncio
    async def test_get_follower_ids_empty_list(
        self,
        user_management_service: UserManagementService,
    ) -> None:
        """Test retrieval when user has no followers."""
        user_id = uuid4()

        # Mock empty response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "totalCount": 0,
            "followedUsers": [],
            "limit": 100,
            "offset": 0,
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        user_management_service._client = mock_client

        # Call method
        follower_ids = await user_management_service.get_follower_ids(user_id)

        # Verify empty list returned
        assert follower_ids == []

    @pytest.mark.asyncio
    async def test_get_follower_ids_user_not_found(
        self,
        user_management_service: UserManagementService,
    ) -> None:
        """Test silent failure when user not found (404)."""
        user_id = uuid4()

        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "User not found"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found",
            request=MagicMock(),
            response=mock_response,
        )
        user_management_service._client = mock_client

        # Call method - should return empty list, not raise
        follower_ids = await user_management_service.get_follower_ids(user_id)

        # Verify empty list returned (silent failure)
        assert follower_ids == []

    @pytest.mark.asyncio
    async def test_get_follower_ids_server_error(
        self,
        user_management_service: UserManagementService,
    ) -> None:
        """Test silent failure on 5xx server errors."""
        user_id = uuid4()

        # Mock 500 response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=mock_response,
        )
        user_management_service._client = mock_client

        # Call method - should return empty list
        follower_ids = await user_management_service.get_follower_ids(user_id)

        # Verify empty list returned
        assert follower_ids == []

    @pytest.mark.asyncio
    async def test_get_follower_ids_connection_error(
        self,
        user_management_service: UserManagementService,
    ) -> None:
        """Test silent failure on connection errors."""
        user_id = uuid4()

        # Mock connection error
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        user_management_service._client = mock_client

        # Call method - should return empty list
        follower_ids = await user_management_service.get_follower_ids(user_id)

        # Verify empty list returned
        assert follower_ids == []

    @pytest.mark.asyncio
    async def test_get_follower_ids_timeout_error(
        self,
        user_management_service: UserManagementService,
    ) -> None:
        """Test silent failure on timeout errors."""
        user_id = uuid4()

        # Mock timeout error
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.TimeoutException("Request timeout")
        )
        user_management_service._client = mock_client

        # Call method - should return empty list
        follower_ids = await user_management_service.get_follower_ids(user_id)

        # Verify empty list returned
        assert follower_ids == []

    @pytest.mark.asyncio
    async def test_get_follower_ids_invalid_response_format(
        self,
        user_management_service: UserManagementService,
    ) -> None:
        """Test silent failure when response format is invalid."""
        user_id = uuid4()

        # Mock invalid response (missing required fields)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "invalidField": "invalid"
            # Missing totalCount, followedUsers, etc.
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        user_management_service._client = mock_client

        # Call method - should return empty list (pydantic validation error)
        follower_ids = await user_management_service.get_follower_ids(user_id)

        # Verify empty list returned
        assert follower_ids == []

    @pytest.mark.asyncio
    async def test_get_follower_ids_invalid_uuid_in_response(
        self,
        user_management_service: UserManagementService,
    ) -> None:
        """Test silent failure when response contains invalid UUID."""
        user_id = uuid4()

        # Mock response with invalid UUID
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "totalCount": 1,
            "followedUsers": [
                {
                    "userId": "not-a-valid-uuid",  # Invalid UUID
                    "username": "testuser",
                    "email": "test@example.com",
                    "fullName": "Test User",
                    "bio": "A test user",
                    "isActive": True,
                    "createdAt": datetime.now(UTC).isoformat(),
                    "updatedAt": datetime.now(UTC).isoformat(),
                }
            ],
            "limit": 100,
            "offset": 0,
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        user_management_service._client = mock_client

        # Call method - should return empty list (UUID parsing error)
        follower_ids = await user_management_service.get_follower_ids(user_id)

        # Verify empty list returned
        assert follower_ids == []

    @pytest.mark.asyncio
    async def test_get_follower_ids_null_followed_users(
        self,
        user_management_service: UserManagementService,
    ) -> None:
        """Test handling of null followedUsers (count_only mode)."""
        user_id = uuid4()

        # Mock count_only response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "totalCount": 5,
            "followedUsers": None,  # Null when count_only=true
            "limit": None,
            "offset": None,
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        user_management_service._client = mock_client

        # Call method - should return empty list
        follower_ids = await user_management_service.get_follower_ids(user_id)

        # Verify empty list returned
        assert follower_ids == []

    @pytest.mark.asyncio
    async def test_get_follower_ids_large_follower_list(
        self,
        user_management_service: UserManagementService,
        sample_user_data: dict[str, str | bool],
    ) -> None:
        """Test retrieval with max follower count (100)."""
        user_id = uuid4()

        # Create 100 followers
        followers = []
        for i in range(100):
            follower = sample_user_data.copy()
            follower["userId"] = str(uuid4())
            follower["username"] = f"follower{i}"
            followers.append(follower)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "totalCount": 150,  # More exist, but we only fetch first page
            "followedUsers": followers,
            "limit": 100,
            "offset": 0,
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        user_management_service._client = mock_client

        # Call method
        follower_ids = await user_management_service.get_follower_ids(user_id)

        # Verify we got 100 follower IDs
        assert len(follower_ids) == 100
        assert all(isinstance(fid, UUID) for fid in follower_ids)


class TestGetNotificationPreferences:
    """Test suite for get_notification_preferences method."""

    @pytest.mark.asyncio
    async def test_get_notification_preferences_success(
        self,
        user_management_service: UserManagementService,
    ) -> None:
        """Test successful retrieval of notification preferences."""
        user_id = uuid4()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "userId": str(user_id),
            "category": "notification",
            "preferences": {
                "emailNotifications": True,
                "pushNotifications": True,
                "smsNotifications": False,
                "marketingEmails": False,
                "securityAlerts": True,
                "activitySummaries": True,
                "recipeRecommendations": True,
                "socialInteractions": False,
                "updatedAt": datetime.now(UTC).isoformat(),
            },
            "updatedAt": datetime.now(UTC).isoformat(),
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        user_management_service._client = mock_client

        prefs = await user_management_service.get_notification_preferences(user_id)

        assert prefs is not None
        assert prefs.recipe_recommendations is True
        assert prefs.social_interactions is False
        assert prefs.email_notifications is True

        mock_client.get.assert_called_once_with(
            f"/api/v1/user-management/users/{user_id}/preferences/notification",
        )

    @pytest.mark.asyncio
    async def test_get_notification_preferences_recipe_recommendations_false(
        self,
        user_management_service: UserManagementService,
    ) -> None:
        """Test retrieval when user has opted out of recipe recommendations."""
        user_id = uuid4()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "userId": str(user_id),
            "category": "notification",
            "preferences": {
                "recipeRecommendations": False,
            },
            "updatedAt": datetime.now(UTC).isoformat(),
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        user_management_service._client = mock_client

        prefs = await user_management_service.get_notification_preferences(user_id)

        assert prefs is not None
        assert prefs.recipe_recommendations is False

    @pytest.mark.asyncio
    async def test_get_notification_preferences_user_not_found(
        self,
        user_management_service: UserManagementService,
    ) -> None:
        """Test silent failure when user not found (404)."""
        user_id = uuid4()

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "User not found"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found",
            request=MagicMock(),
            response=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        user_management_service._client = mock_client

        prefs = await user_management_service.get_notification_preferences(user_id)

        assert prefs is None

    @pytest.mark.asyncio
    async def test_get_notification_preferences_server_error(
        self,
        user_management_service: UserManagementService,
    ) -> None:
        """Test silent failure on 5xx server errors."""
        user_id = uuid4()

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        user_management_service._client = mock_client

        prefs = await user_management_service.get_notification_preferences(user_id)

        assert prefs is None

    @pytest.mark.asyncio
    async def test_get_notification_preferences_connection_error(
        self,
        user_management_service: UserManagementService,
    ) -> None:
        """Test silent failure on connection errors."""
        user_id = uuid4()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        user_management_service._client = mock_client

        prefs = await user_management_service.get_notification_preferences(user_id)

        assert prefs is None

    @pytest.mark.asyncio
    async def test_get_notification_preferences_timeout(
        self,
        user_management_service: UserManagementService,
    ) -> None:
        """Test silent failure on timeout errors."""
        user_id = uuid4()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.TimeoutException("Request timeout")
        )
        user_management_service._client = mock_client

        prefs = await user_management_service.get_notification_preferences(user_id)

        assert prefs is None

    @pytest.mark.asyncio
    async def test_get_notification_preferences_invalid_response(
        self,
        user_management_service: UserManagementService,
    ) -> None:
        """Test silent failure when response format is invalid."""
        user_id = uuid4()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"invalidField": "invalid"}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        user_management_service._client = mock_client

        prefs = await user_management_service.get_notification_preferences(user_id)

        assert prefs is None


class TestGetNotificationPreferencesBatch:
    """Test suite for get_notification_preferences_batch method."""

    @pytest.mark.asyncio
    async def test_batch_empty_list(
        self,
        user_management_service: UserManagementService,
    ) -> None:
        """Test batch fetch with empty user list."""
        result = await user_management_service.get_notification_preferences_batch([])

        assert result == {}

    @pytest.mark.asyncio
    async def test_batch_single_user(
        self,
        user_management_service: UserManagementService,
    ) -> None:
        """Test batch fetch with single user."""
        user_id = uuid4()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "userId": str(user_id),
            "category": "notification",
            "preferences": {
                "recipeRecommendations": True,
            },
            "updatedAt": datetime.now(UTC).isoformat(),
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        user_management_service._client = mock_client

        result = await user_management_service.get_notification_preferences_batch(
            [user_id]
        )

        assert len(result) == 1
        assert user_id in result
        prefs = result[user_id]
        assert prefs is not None
        assert prefs.recipe_recommendations is True

    @pytest.mark.asyncio
    async def test_batch_multiple_users_all_success(
        self,
        user_management_service: UserManagementService,
    ) -> None:
        """Test batch fetch with multiple users, all successful."""
        user_ids = [uuid4(), uuid4(), uuid4()]

        def create_response(uid: UUID, opted_in: bool) -> MagicMock:
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {
                "userId": str(uid),
                "category": "notification",
                "preferences": {
                    "recipeRecommendations": opted_in,
                },
                "updatedAt": datetime.now(UTC).isoformat(),
            }
            return response

        responses = [
            create_response(user_ids[0], True),
            create_response(user_ids[1], False),
            create_response(user_ids[2], True),
        ]

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=responses)
        user_management_service._client = mock_client

        result = await user_management_service.get_notification_preferences_batch(
            user_ids
        )

        assert len(result) == 3
        prefs0 = result[user_ids[0]]
        prefs1 = result[user_ids[1]]
        prefs2 = result[user_ids[2]]
        assert prefs0 is not None and prefs0.recipe_recommendations is True
        assert prefs1 is not None and prefs1.recipe_recommendations is False
        assert prefs2 is not None and prefs2.recipe_recommendations is True

    @pytest.mark.asyncio
    async def test_batch_mixed_success_and_failures(
        self,
        user_management_service: UserManagementService,
    ) -> None:
        """Test batch fetch where some users succeed and some fail."""
        user_ids = [uuid4(), uuid4(), uuid4()]

        # First succeeds, second 404, third succeeds
        success_response1 = MagicMock()
        success_response1.status_code = 200
        success_response1.json.return_value = {
            "userId": str(user_ids[0]),
            "category": "notification",
            "preferences": {
                "recipeRecommendations": True,
            },
            "updatedAt": datetime.now(UTC).isoformat(),
        }

        error_response = MagicMock()
        error_response.status_code = 404
        error_response.text = "User not found"
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found",
            request=MagicMock(),
            response=error_response,
        )

        success_response2 = MagicMock()
        success_response2.status_code = 200
        success_response2.json.return_value = {
            "userId": str(user_ids[2]),
            "category": "notification",
            "preferences": {
                "recipeRecommendations": False,
            },
            "updatedAt": datetime.now(UTC).isoformat(),
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=[success_response1, error_response, success_response2]
        )
        user_management_service._client = mock_client

        result = await user_management_service.get_notification_preferences_batch(
            user_ids
        )

        assert len(result) == 3
        prefs0 = result[user_ids[0]]
        prefs2 = result[user_ids[2]]
        assert prefs0 is not None and prefs0.recipe_recommendations is True
        assert result[user_ids[1]] is None  # Failed to fetch
        assert prefs2 is not None and prefs2.recipe_recommendations is False
