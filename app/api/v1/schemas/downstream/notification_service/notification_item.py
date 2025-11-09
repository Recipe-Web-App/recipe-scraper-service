"""NotificationItem schema for notification-service."""

from uuid import UUID

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema


class NotificationItem(BaseSchema):
    """Individual notification item in batch response.

    Represents a single queued notification with its ID and recipient.
    """

    notification_id: UUID = Field(
        ...,
        description="Unique notification ID for tracking delivery status",
    )
    recipient_id: UUID = Field(
        ...,
        description="User ID of the notification recipient",
    )
