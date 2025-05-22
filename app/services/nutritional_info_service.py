"""Nutritional info service module.

Provides functionality to retrieve detailed nutritional information for ingredients
based on their ID and specified quantity.

Includes logging for traceability and debugging.
"""

from app.core.logging import get_logger
from app.schemas.common.ingredient import Quantity
from app.schemas.common.nutritional_info import NutritionalInfo
from app.schemas.response.ingredient_nutritional_info_response import (
    IngredientNutritionalInfoResponse,
)
from app.schemas.response.recipe_nutritional_info_response import (
    RecipeNutritionalInfoResponse,
)


class NutritionalInfoService:
    """Service to retrieve nutritional information for ingredients.

    This service provides methods to obtain detailed nutritional data
    based on given database identifiers.

    Attributes:
        log (logging.Logger): Logger instance for this service.
    """

    def __init__(self) -> None:
        """Initialize the NutritionalInfoService with a logger."""
        self.__log = get_logger("NutritionalInfoService")

    def get_recipe_nutritional_info(
        self,
        recipe_id: int,
        include_total: bool,
        include_ingredients: bool,
    ) -> RecipeNutritionalInfoResponse:
        """Fetch nutritional information for a given ingredient and allergies.

        Logs the retrieval request and returns a response with nutritional info for all
            ingredients in the recipe.

        Args:
            recipe_id (int): The unique identifier of the recipe.
            include_total (bool): Indicates that a total of all nutritional info should
                be included in the response.
            include_ingredients (bool): Indicates that nutritional info for all
                ingredients should be included in the response.

        Returns:
            RecipeNutritionalInfoResponse: Nutrional info response schema containing
                individual ingredients and/or an overall total.
        """
        self.__log.info(
            "Getting nutritional info for recipe ID %s (includeTotal=%s | \
              includeIngredients=%s)",
            recipe_id,
            include_total,
            include_ingredients,
        )

        ingredients = [
            IngredientNutritionalInfoResponse(
                ingredient={
                    "ingredient_id": 1,
                    "name": "Almond",
                    "quantity": {
                        "quantity_value": 100.0,
                        "measurement": "gram",
                    },
                },
                macronutrients={
                    "calories": 579.0,
                    "protein_g": 21.15,
                    "fat_g": 49.93,
                    "saturated_fat_g": 3.73,
                    "monounsaturated_fat_g": 31.55,
                    "polyunsaturated_fat_g": 12.33,
                    "trans_fat_g": 0.0,
                    "cholesterol_mg": 0.0,
                    "carbs_g": 21.55,
                    "fiber_g": 12.5,
                    "sugar_g": 4.35,
                },
                vitamins={
                    "vitamin_a_mcg": 1.0,
                    "vitamin_c_mg": 0.0,
                    "vitamin_d_mcg": None,
                    "vitamin_k_mcg": 0.0,
                    "vitamin_b6_mg": 0.14,
                    "vitamin_b12_mcg": None,
                },
                minerals={
                    "calcium_mg": 269.0,
                    "iron_mg": 3.71,
                    "magnesium_mg": 270.0,
                    "potassium_mg": 733.0,
                    "sodium_mg": 1.0,
                    "zinc_mg": 3.12,
                },
                allergies=["tree nuts"],
            ),
            IngredientNutritionalInfoResponse(
                ingredient={
                    "ingredient_id": 2,
                    "name": "Oats",
                    "quantity": {
                        "quantity_value": 100.0,
                        "measurement": "gram",
                    },
                },
                macronutrients={
                    "calories": 389.0,
                    "protein_g": 16.89,
                    "fat_g": 6.9,
                    "saturated_fat_g": 1.22,
                    "monounsaturated_fat_g": 2.18,
                    "polyunsaturated_fat_g": 2.54,
                    "trans_fat_g": 0.0,
                    "cholesterol_mg": 0.0,
                    "carbs_g": 66.27,
                    "fiber_g": 10.6,
                    "sugar_g": 0.99,
                },
                vitamins={
                    "vitamin_a_mcg": 0.0,
                    "vitamin_c_mg": 0.0,
                    "vitamin_d_mcg": None,
                    "vitamin_k_mcg": 2.0,
                    "vitamin_b6_mg": 0.12,
                    "vitamin_b12_mcg": None,
                },
                minerals={
                    "calcium_mg": 54.0,
                    "iron_mg": 4.72,
                    "magnesium_mg": 177.0,
                    "potassium_mg": 429.0,
                    "sodium_mg": 2.0,
                    "zinc_mg": 3.97,
                },
                allergies=["gluten"],
            ),
        ]

        response = RecipeNutritionalInfoResponse()
        if include_ingredients:
            response.ingredients = ingredients
        if include_total:
            response.total = NutritionalInfo()
            for ingredient in ingredients:
                response.total += ingredient

        return response

    def get_ingredient_nutritional_info(
        self,
        ingredient_id: int,
        quantity: Quantity,
    ) -> IngredientNutritionalInfoResponse:
        """Fetch nutritional information for a given ingredient and quantity.

        Logs the retrieval request and returns a response with
        ingredient details, macro-nutrients, vitamins, minerals, and allergies.

        Args:
            ingredient_id (int): The unique identifier of the ingredient.
            quantity (Quantity): The amount and unit of the ingredient.

        Returns:
            IngredientNutritionalInfoResponse: Nutritional info response schema
                containing ingredient details and nutritional values.
        """
        self.__log.info(
            "Getting nutritional info for ingredient ID %s (%s %s)",
            ingredient_id,
            quantity.quantity_value,
            quantity.measurement,
        )

        return IngredientNutritionalInfoResponse(
            ingredient={
                "ingredient_id": 123,
                "name": "Almond",
                "quantity": {
                    "quantity_value": 100.0,
                    "measurement": "gram",
                },
            },
            macronutrients={
                "calories": 579.0,
                "protein_g": 21.15,
                "fat_g": 49.93,
                "saturated_fat_g": 3.73,
                "monounsaturated_fat_g": 31.55,
                "polyunsaturated_fat_g": 12.33,
                "trans_fat_g": 0.0,
                "cholesterol_mg": 0.0,
                "carbs_g": 21.55,
                "fiber_g": 12.5,
                "sugar_g": 4.35,
            },
            vitamins={
                "vitamin_a_mcg": 1.0,
                "vitamin_c_mg": 0.0,
                "vitamin_d_mcg": None,
                "vitamin_k_mcg": 0.0,
                "vitamin_b6_mg": 0.14,
                "vitamin_b12_mcg": None,
            },
            minerals={
                "calcium_mg": 269.0,
                "iron_mg": 3.71,
                "magnesium_mg": 270.0,
                "potassium_mg": 733.0,
                "sodium_mg": 1.0,
                "zinc_mg": 3.12,
            },
            allergies=["tree nuts"],
        )
