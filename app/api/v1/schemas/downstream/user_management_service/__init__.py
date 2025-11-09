"""User-management-service schemas."""

from app.api.v1.schemas.downstream.user_management_service.get_followed_users_response import (  # noqa: E501
    GetFollowedUsersResponse,
)
from app.api.v1.schemas.downstream.user_management_service.user import User

__all__ = [
    "User",
    "GetFollowedUsersResponse",
]
