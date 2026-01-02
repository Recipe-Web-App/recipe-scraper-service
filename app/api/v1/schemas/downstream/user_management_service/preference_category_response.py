"""PreferenceCategoryResponse schema from user-management-service."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.api.v1.schemas.downstream.user_management_service.notification_preferences import (  # noqa: E501
    NotificationPreferences,
)


class PreferenceCategoryResponse(BaseSchema):
    """Response schema for a specific preference category.

    Wraps the category-specific preferences with user metadata. Used when fetching
    individual preference categories like 'notification'.
    """

    user_id: UUID = Field(
        ...,
        description="Unique user identifier",
    )
    category: str = Field(
        ...,
        description="Preference category name (e.g., 'notification')",
    )
    preferences: NotificationPreferences = Field(
        ...,
        description="Category-specific preferences object",
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp for this category",
    )
