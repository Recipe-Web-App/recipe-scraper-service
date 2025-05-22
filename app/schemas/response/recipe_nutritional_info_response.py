"""Recipe nutritional information response schema.

Defines the Pydantic model representing nutritional information for recipes in API
responses, including a list of ingredient nutritional info objects.
"""

from pydantic import BaseModel, Field

from app.schemas.common.nutritional_info import NutritionalInfo
from app.schemas.response.ingredient_nutritional_info_response import (
    IngredientNutritionalInfoResponse,
)


class RecipeNutritionalInfoResponse(BaseModel):
    """Response schema representing nutritional information for a recipe.

    Attributes:
        ingredients (list[IngredientNutritionalInfoResponse]): A list of nutritional
            information responses for each ingredient included in the recipe.
        total (NutritionalInfo | None): The total sum of all nutritional info.
    """

    ingredients: list[IngredientNutritionalInfoResponse] | None = Field(
        None,
        description="A list of nutritional information for each ingredient in the \
          recipe.",
    )
    total: NutritionalInfo | None = Field(
        None,
        description="The total aggregated nutritional information for the recipe.",
    )
