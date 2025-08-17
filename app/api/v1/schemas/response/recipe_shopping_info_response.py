"""Response schema representing shopping information for a recipe."""

from decimal import Decimal

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.api.v1.schemas.response.ingredient_shopping_info_response import (
    IngredientShoppingInfoResponse,
)


class RecipeShoppingInfoResponse(BaseSchema):
    """Response schema representing shopping information for a recipe.

    Attributes:
        recipe_id (int): The unique identifier of the recipe.
        ingredients (dict[str, IngredientShoppingInfoResponse]): A dictionary mapping
            ingredient names to their shopping information.
        total_estimated_cost (Decimal): The total estimated cost with 2 decimal places
            for ingredients with available pricing.
    """

    recipe_id: int = Field(..., description="The unique identifier of the recipe", gt=0)
    ingredients: dict[int, IngredientShoppingInfoResponse] = Field(
        ...,
        description="Dictionary mapping ingredient IDs to their shopping information",
    )
    total_estimated_cost: Decimal = Field(
        ...,
        description="The total estimated cost for all ingredients",
        ge=0,
        decimal_places=2,
    )
