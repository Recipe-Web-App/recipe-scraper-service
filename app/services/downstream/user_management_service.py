"""User Management Service client for fetching user and follower data.

Provides methods to interact with the user-management-service for retrieving follower
information needed for sending notifications.
"""

import asyncio
from uuid import UUID

import httpx

from app.api.v1.schemas.downstream.user_management_service import (
    GetFollowedUsersResponse,
    NotificationPreferences,
    PreferenceCategoryResponse,
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

    async def get_notification_preferences(
        self,
        user_id: UUID,
    ) -> NotificationPreferences | None:
        """Get notification preferences for a user.

        Uses silent failure pattern: returns None on any error.

        Args:
            user_id: UUID of the user whose preferences to retrieve

        Returns:
            NotificationPreferences if successful, None on error
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f"/api/v1/user-management/users/{user_id}/preferences/notification",
            )
            response.raise_for_status()

            data = PreferenceCategoryResponse(**response.json())
            self._log.debug(
                "Fetched notification preferences for user_id: {}",
                user_id,
            )
            return data.preferences

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                self._log.warning(
                    "User or preferences not found for user_id: {}",
                    user_id,
                )
            else:
                self._log.error(
                    "HTTP error fetching preferences for user_id {}: {} - {}",
                    user_id,
                    e.response.status_code,
                    e.response.text,
                )
            return None

        except httpx.RequestError as e:
            self._log.error(
                "Connection error fetching preferences for user_id {}: {}",
                user_id,
                e,
            )
            return None

        except ValueError as e:
            self._log.error(
                "Invalid response format for preferences user_id {}: {}",
                user_id,
                e,
            )
            return None

        except Exception as e:
            self._log.error(
                "Unexpected error fetching preferences for user_id {}: {}",
                user_id,
                e,
            )
            return None

    async def get_notification_preferences_batch(
        self,
        user_ids: list[UUID],
        max_concurrency: int = 10,
    ) -> dict[UUID, NotificationPreferences | None]:
        """Get notification preferences for multiple users concurrently.

        Uses asyncio.Semaphore to limit concurrent requests and prevent
        overwhelming the downstream service.

        Args:
            user_ids: List of user IDs to fetch preferences for
            max_concurrency: Maximum concurrent requests (default: 10)

        Returns:
            Dict mapping user_id to NotificationPreferences (or None on error)
        """
        if not user_ids:
            return {}

        semaphore = asyncio.Semaphore(max_concurrency)

        async def fetch_with_semaphore(
            uid: UUID,
        ) -> tuple[UUID, NotificationPreferences | None]:
            async with semaphore:
                prefs = await self.get_notification_preferences(uid)
                return uid, prefs

        results = await asyncio.gather(
            *[fetch_with_semaphore(uid) for uid in user_ids],
            return_exceptions=True,
        )

        preferences: dict[UUID, NotificationPreferences | None] = {}
        for result in results:
            if isinstance(result, BaseException):
                self._log.error("Batch preference fetch error: {}", result)
                continue
            uid, prefs = result
            preferences[uid] = prefs

        self._log.info(
            "Batch fetched preferences for {} of {} users",
            len(preferences),
            len(user_ids),
        )
        return preferences
