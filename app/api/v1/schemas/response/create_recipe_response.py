"""Create recipe response schema.

Defines the Pydantic model for the response returned after creating a new recipe.
"""

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.api.v1.schemas.common.recipe import Recipe


class CreateRecipeResponse(BaseSchema):
    """Response model returned after a recipe is successfully created.

    Attributes:     recipe (Recipe): The recipe that was created.
    """

    recipe: Recipe = Field(
        ...,
        description="The recipe that was created.",
    )
