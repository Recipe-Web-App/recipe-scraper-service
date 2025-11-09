"""BatchNotificationResponse schema for notification-service."""

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.api.v1.schemas.downstream.notification_service.notification_item import (
    NotificationItem,
)


class BatchNotificationResponse(BaseSchema):
    """Response schema for batch notification requests.

    Returned when notifications are successfully queued for async processing.
    """

    notifications: list[NotificationItem] = Field(
        ...,
        description="List of queued notifications with their IDs",
    )
    queued_count: int = Field(
        ...,
        ge=0,
        description="Total number of notifications queued",
    )
    message: str = Field(
        ...,
        description="Success message",
    )
