"""Ingredient nutritional information response schema.

Defines the Pydantic model representing nutritional info related to ingredients in
responses.
"""

from app.schemas.common.ingredient import Ingredient
from app.schemas.common.nutritional_info import NutritionalInfo


class IngredientNutritionalInfoResponse(NutritionalInfo):
    """Response schema containing overall nutritional information for an ingredient.

    Attributes:
        ingredient (Ingredient): Basic information about the ingredient.
    """

    ingredient: Ingredient
