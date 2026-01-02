"""NotificationPreferences schema from user-management-service."""

from datetime import datetime

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema


class NotificationPreferences(BaseSchema):
    """Notification preferences settings for a user.

    These preferences control what types of notifications the user receives. All fields
    are optional as the API may return partial preference data.
    """

    email_notifications: bool | None = Field(
        default=None,
        description="Enable email notifications",
    )
    push_notifications: bool | None = Field(
        default=None,
        description="Enable push notifications",
    )
    sms_notifications: bool | None = Field(
        default=None,
        description="Enable SMS notifications",
    )
    marketing_emails: bool | None = Field(
        default=None,
        description="Enable marketing emails",
    )
    security_alerts: bool | None = Field(
        default=None,
        description="Enable security alerts",
    )
    activity_summaries: bool | None = Field(
        default=None,
        description="Enable activity summaries",
    )
    recipe_recommendations: bool | None = Field(
        default=None,
        description="Enable recipe recommendations and new recipe notifications",
    )
    social_interactions: bool | None = Field(
        default=None,
        description="Enable social interaction notifications",
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Last update timestamp for preferences",
    )
