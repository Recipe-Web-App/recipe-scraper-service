"""Common Recipe schema.

Defines the base data model for a recipe including its list of ingredients.
"""

from pydantic import BaseModel, Field

from app.schemas.common.ingredient import Ingredient


class Recipe(BaseModel):
    """Represents a recipe composed of a list of ingredients.

    Attributes:
        ingredients (list[Ingredient]): A list of ingredients used in the recipe.
    """

    ingredients: list[Ingredient] = Field(
        ...,
        description="A list of ingredients used in the recipe.",
    )
