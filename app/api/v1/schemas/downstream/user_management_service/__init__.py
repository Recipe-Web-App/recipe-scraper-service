"""User-management-service schemas."""

from app.api.v1.schemas.downstream.user_management_service.get_followed_users_response import (  # noqa: E501
    GetFollowedUsersResponse,
)
from app.api.v1.schemas.downstream.user_management_service.notification_preferences import (  # noqa: E501
    NotificationPreferences,
)
from app.api.v1.schemas.downstream.user_management_service.preference_category_response import (  # noqa: E501
    PreferenceCategoryResponse,
)
from app.api.v1.schemas.downstream.user_management_service.user import User

__all__ = [
    "GetFollowedUsersResponse",
    "NotificationPreferences",
    "PreferenceCategoryResponse",
    "User",
]
