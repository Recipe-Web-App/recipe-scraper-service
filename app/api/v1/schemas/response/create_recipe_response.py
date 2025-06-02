"""Create recipe response schema.

Defines the Pydantic model for the response returned after creating a new recipe.
"""

from pydantic import BaseModel

from app.api.v1.schemas.common.recipe import Recipe


class CreateRecipeResponse(BaseModel):
    """Response model returned after a recipe is successfully created.

    Attributes:
        recipe (Recipe): The recipe that was created.
    """

    recipe: Recipe
