"""Notification Service client for sending recipe notifications.

Provides methods to interact with the notification-service for sending notifications to
followers when recipes are published.
"""

from uuid import UUID

import httpx

from app.api.v1.schemas.downstream.notification_service import (
    BatchNotificationResponse,
    RecipePublishedRequest,
)
from app.core.config.service_urls import ServiceURLs
from app.services.downstream.base_service import BaseServiceWithOAuth2
from app.utils.service_token_manager import ServiceTokenManager


class NotificationService(BaseServiceWithOAuth2):
    """Client for notification-service API.

    Provides methods to send recipe-related notifications with silent failure pattern
    (returns bool instead of raising exceptions).
    """

    def __init__(self, token_manager: ServiceTokenManager) -> None:
        """Initialize the notification service client.

        Args:
            token_manager: ServiceTokenManager instance for OAuth2 authentication
        """
        super().__init__(
            token_manager=token_manager,
            base_url=ServiceURLs.notification_service_url(),
            scope="notification:admin",
        )

    async def send_recipe_published_notification(
        self,
        recipe_id: int,
        follower_ids: list[UUID],
    ) -> bool:
        """Send recipe published notifications to followers.

        Automatically handles batching for large follower lists (max 100 per request).
        Uses silent failure pattern: returns True on success, False on any error.

        Args:
            recipe_id: ID of the published recipe
            follower_ids: List of follower user IDs to notify

        Returns:
            True if all notifications queued successfully, False on any error
        """
        if not follower_ids:
            self._log.debug(
                "No followers to notify for recipe_id: {}",
                recipe_id,
            )
            return True  # Success - nothing to do

        try:
            total_batches = (len(follower_ids) + 99) // 100

            # Process in batches of 100 (API limit)
            for i in range(0, len(follower_ids), 100):
                batch = follower_ids[i : i + 100]
                batch_num = i // 100 + 1

                # Prepare request
                request_data = RecipePublishedRequest(
                    recipient_ids=batch,
                    recipe_id=recipe_id,
                )

                # Send notification request
                client = await self._get_client()
                response = await client.post(
                    "/api/v1/notification/notifications/recipe-published",
                    json=request_data.model_dump(mode="json"),
                )
                response.raise_for_status()

                # Parse response
                result = BatchNotificationResponse(**response.json())
                self._log.info(
                    "Queued {} notifications for recipe_id {} " "(batch {}/{})",
                    result.queued_count,
                    recipe_id,
                    batch_num,
                    total_batches,
                )

            self._log.info(
                "Successfully queued all notifications for recipe_id {} "
                "({} followers across {} batches)",
                recipe_id,
                len(follower_ids),
                total_batches,
            )
            return True

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                self._log.warning(
                    "Rate limit exceeded sending notifications for recipe_id {}: {}",
                    recipe_id,
                    e.response.text,
                )
            elif e.response.status_code in (401, 403):
                self._log.error(
                    "Authentication error sending notifications "
                    "for recipe_id {}: {} - {}",
                    recipe_id,
                    e.response.status_code,
                    e.response.text,
                )
            else:
                self._log.error(
                    "HTTP error {} sending notifications for recipe_id {}: {}",
                    e.response.status_code,
                    recipe_id,
                    e.response.text,
                )
            return False

        except httpx.RequestError as e:
            self._log.error(
                "Connection error sending notifications for recipe_id {}: {}",
                recipe_id,
                e,
            )
            return False

        except ValueError as e:
            # Catches pydantic validation errors
            self._log.error(
                "Invalid response from notification-service " "for recipe_id {}: {}",
                recipe_id,
                e,
            )
            return False

        except Exception as e:
            self._log.error(
                "Unexpected error sending notifications for recipe_id {}: {}",
                recipe_id,
                e,
            )
            return False
