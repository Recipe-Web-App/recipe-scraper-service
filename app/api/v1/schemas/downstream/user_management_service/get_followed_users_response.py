"""GetFollowedUsersResponse schema from user-management-service."""

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.api.v1.schemas.downstream.user_management_service.user import User


class GetFollowedUsersResponse(BaseSchema):
    """Response schema for getting followed users (followers/following).

    Contains a list of users and pagination metadata. When count_only=true is requested,
    followed_users, limit, and offset will be null.
    """

    total_count: int = Field(
        ...,
        ge=0,
        description="Total number of followers/following",
    )
    followed_users: list[User] | None = Field(
        default=None,
        description="List of followed users (null when count_only=true)",
    )
    limit: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="Number of results per page (null when count_only=true)",
    )
    offset: int | None = Field(
        default=None,
        ge=0,
        description="Offset for pagination (null when count_only=true)",
    )
