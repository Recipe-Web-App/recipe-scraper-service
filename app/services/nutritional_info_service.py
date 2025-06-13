"""Nutritional info service module.

Provides functionality to retrieve detailed nutritional information for ingredients
based on their ID and specified quantity.

Includes logging for traceability and debugging.
"""

from app.api.v1.schemas.common.ingredient import Quantity
from app.api.v1.schemas.response.ingredient_nutritional_info_response import (
    IngredientNutritionalInfoResponse,
)
from app.api.v1.schemas.response.recipe_nutritional_info_response import (
    RecipeNutritionalInfoResponse,
)
from app.core.logging import get_logger


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
            RecipeNutritionalInfoResponse: Nutritional info response schema containing
                individual ingredients and/or an overall total.
        """
        self.__log.info(
            "Getting nutritional info for recipe ID {} (includeTotal={} | "
            "includeIngredients={})",
            recipe_id,
            include_total,
            include_ingredients,
        )

        ingredients: dict[int, IngredientNutritionalInfoResponse] = {}

        response = RecipeNutritionalInfoResponse()
        if include_ingredients:
            response.ingredients = ingredients
        if include_total:
            response.total = (
                IngredientNutritionalInfoResponse.calculate_total_nutritional_info(
                    list(ingredients.values()),
                )
            )

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
            "Getting nutritional info for ingredient ID {} ({} {})",
            ingredient_id,
            quantity.quantity_value,
            quantity.measurement,
        )

        return IngredientNutritionalInfoResponse()
