"""User schema from user-management-service."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema


class User(BaseSchema):
    """User model from user-management-service.

    Represents a user account with profile information and metadata.
    """

    user_id: UUID = Field(
        ...,
        description="Unique user identifier",
    )
    username: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Username (1-50 characters)",
    )
    email: str | None = Field(
        default=None,
        description="Email address (nullable, depends on privacy settings)",
    )
    full_name: str | None = Field(
        default=None,
        max_length=100,
        description="Full name (max 100 characters, nullable)",
    )
    bio: str | None = Field(
        default=None,
        max_length=500,
        description="User biography (max 500 characters, nullable)",
    )
    is_active: bool = Field(
        ...,
        description="Whether the user account is active",
    )
    created_at: datetime = Field(
        ...,
        description="Account creation timestamp",
    )
    updated_at: datetime = Field(
        ...,
        description="Last account update timestamp",
    )
