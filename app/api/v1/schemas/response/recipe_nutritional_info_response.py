"""Recipe nutritional information response schema.

Defines the Pydantic model representing nutritional information for recipes in API
responses, including a list of ingredient nutritional info objects.
"""

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.api.v1.schemas.response.ingredient_nutritional_info_response import (
    IngredientNutritionalInfoResponse,
)


class RecipeNutritionalInfoResponse(BaseSchema):
    """Response schema representing nutritional information for a recipe.

    Attributes:     ingredients (dict[int, IngredientNutritionalInfoResponse]): A list
    of         nutritional information responses for each ingredient included in the
    recipe.     total (NutritionalInfo | None): The total sum of all nutritional info.
    """

    ingredients: dict[int, IngredientNutritionalInfoResponse] | None = Field(
        None,
        description="A list of nutritional information for each ingredient in the \
          recipe.",
    )
    missing_ingredients: list[int] | None = Field(
        None,
        description="A list of ingredient IDs for which nutritional information could "
        "not be retrieved.",
    )
    total: IngredientNutritionalInfoResponse | None = Field(
        None,
        description="The total aggregated nutritional information for the recipe.",
    )
