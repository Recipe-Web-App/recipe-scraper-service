"""Pydantic schema for recipe creation requests.

This module defines the CreateRecipeRequest model, which is used to validate and
document the request body for API endpoints that accept a single recipe URL for
creating a new recipe entry.

Classes:
    CreateRecipeRequest: Request schema for creating a recipe from a URL.
"""

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema


class CreateRecipeRequest(BaseSchema):
    """Request schema for creating a recipe from a URL.

    This Pydantic model is used to validate and document the request body for
    endpoints that accept a single recipe URL to create a new recipe entry.

    Attributes:
        recipe_url (str):
            The recipe URL to be processed for recipe creation.
            Should point to a valid recipe page.
    """

    recipe_url: str = Field(
        ...,
        alias="recipeUrl",
        description="The recipe URL to create. Should point to a valid recipe page.",
    )
