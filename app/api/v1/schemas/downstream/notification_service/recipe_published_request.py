"""RecipePublishedRequest schema for notification-service."""

from uuid import UUID

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema


class RecipePublishedRequest(BaseSchema):
    """Request schema for sending recipe published notifications.

    Used to notify followers when a new recipe is published.
    """

    recipient_ids: list[UUID] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of recipient user IDs (1-100 per batch)",
    )
    recipe_id: int = Field(
        ...,
        gt=0,
        description="ID of the published recipe",
    )
