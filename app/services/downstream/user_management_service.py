"""User Management Service client for fetching user and follower data.

Provides methods to interact with the user-management-service for retrieving follower
information needed for sending notifications.
"""

from uuid import UUID

import httpx

from app.api.v1.schemas.downstream.user_management_service import (
    GetFollowedUsersResponse,
)
from app.core.config.service_urls import ServiceURLs
from app.services.downstream.base_service import BaseServiceWithOAuth2
from app.utils.service_token_manager import ServiceTokenManager


class UserManagementService(BaseServiceWithOAuth2):
    """Client for user-management-service API.

    Provides methods to fetch user and follower data with silent failure pattern
    (returns empty lists on errors instead of raising exceptions).
    """

    def __init__(self, token_manager: ServiceTokenManager) -> None:
        """Initialize the user management service client.

        Args:
            token_manager: ServiceTokenManager instance for OAuth2 authentication
        """
        super().__init__(
            token_manager=token_manager,
            base_url=ServiceURLs.user_management_service_url(),
            scope="user:read",
        )

    async def get_follower_ids(self, user_id: UUID) -> list[UUID]:
        """Get list of follower user IDs for a given user.

        Fetches the first page of followers (up to 100). Uses silent failure pattern:
        returns empty list on any error (user not found, service unavailable, etc.).

        Args:
            user_id: UUID of the user whose followers to retrieve

        Returns:
            List of follower user IDs, or empty list if user not found or on error
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f"/api/v1/user-management/users/{user_id}/followers",
                params={"limit": 100},  # Max per page, first page only
            )
            response.raise_for_status()

            # Parse response
            data = GetFollowedUsersResponse(**response.json())

            # Extract user IDs from follower list
            if data.followed_users is None:
                self._log.warning(
                    "No followed_users in response for user_id: {}",
                    user_id,
                )
                return []

            follower_ids = [user.user_id for user in data.followed_users]
            self._log.info(
                "Fetched {} follower IDs for user_id: {}",
                len(follower_ids),
                user_id,
            )
            return follower_ids

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                self._log.warning(
                    "User not found in user-management-service: {}",
                    user_id,
                )
            else:
                self._log.error(
                    "HTTP error fetching followers for user_id {}: {} - {}",
                    user_id,
                    e.response.status_code,
                    e.response.text,
                )
            return []

        except httpx.RequestError as e:
            self._log.error(
                "Connection error fetching followers for user_id {}: {}",
                user_id,
                e,
            )
            return []

        except ValueError as e:
            # Catches UUID parsing errors and pydantic validation errors
            self._log.error(
                "Invalid response format from user-management-service "
                "for user_id {}: {}",
                user_id,
                e,
            )
            return []

        except Exception as e:
            self._log.error(
                "Unexpected error fetching followers for user_id {}: {}",
                user_id,
                e,
            )
            return []
