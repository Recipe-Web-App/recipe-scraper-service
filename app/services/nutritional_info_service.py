"""Nutritional info service module.

Provides functionality to retrieve detailed nutritional information for ingredients
based on their ID and specified quantity.

Includes logging for traceability and debugging.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.schemas.common.ingredient import Quantity
from app.api.v1.schemas.response.ingredient_nutritional_info_response import (
    IngredientNutritionalInfoResponse,
)
from app.api.v1.schemas.response.recipe_nutritional_info_response import (
    RecipeNutritionalInfoResponse,
)
from app.core.logging import get_logger
from app.db.models.ingredient_models.ingredient import Ingredient
from app.db.models.nutritional_info_models.nutritional_info import NutritionalInfo
from app.db.models.recipe_models.recipe import Recipe
from app.exceptions.custom_exceptions import IncompatibleUnitsError

_log = get_logger(__name__)


class NutritionalInfoService:
    """Service to retrieve nutritional information for ingredients.

    This service provides methods to obtain detailed nutritional data
    based on given database identifiers.

    Attributes:
        log (logging.Logger): Logger instance for this service.
    """

    def get_recipe_nutritional_info(
        self,
        recipe_id: int,
        include_total: bool,
        include_ingredients: bool,
        db: Session,
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
            db (Session): Database session for ORM operations.

        Returns:
            RecipeNutritionalInfoResponse: Nutritional info response schema containing
                individual ingredients and/or an overall total.
        """
        _log.info(
            "Getting nutritional info for recipe ID {} (includeTotal={} | "
            "includeIngredients={})",
            recipe_id,
            include_total,
            include_ingredients,
        )

        # Extract the recipe ingredients from the database
        recipe = db.query(Recipe).filter(Recipe.recipe_id == recipe_id).first()
        if not recipe:
            _log.error("Recipe with ID {} not found", recipe_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recipe with ID {recipe_id} not found",
            )

        _log.debug("Recipe read from database: {}", recipe)

        ingredients: dict[int, IngredientNutritionalInfoResponse] = {}
        missing_ingredients: list[int] = []

        # Process each ingredient in the recipe
        for recipe_ingredient in recipe.ingredients:
            ingredient_name = recipe_ingredient.ingredient.name

            # Create quantity object from recipe ingredient data
            quantity: Quantity | None
            if (
                recipe_ingredient.quantity is not None
                and recipe_ingredient.unit is not None
            ):
                quantity = Quantity(
                    amount=recipe_ingredient.quantity,
                    measurement=recipe_ingredient.unit,
                )
            else:
                quantity = None

            try:
                nutritional_info = self.get_ingredient_nutritional_info(
                    recipe_ingredient.ingredient_id,
                    quantity,
                    db,
                )
                ingredients[recipe_ingredient.ingredient_id] = nutritional_info
            except HTTPException as e:
                _log.error(
                    "Error retrieving nutritional info for ingredient '%s' "
                    "(ID: %s): %s",
                    ingredient_name,
                    recipe_ingredient.ingredient_id,
                    e.detail,
                )
                missing_ingredients.append(recipe_ingredient.ingredient_id)
            except (ValueError, TypeError, AttributeError) as e:
                _log.exception(
                    "Unexpected error processing ingredient '{}' (ID: {}): %s",
                    ingredient_name,
                    recipe_ingredient.ingredient_id,
                    str(e),
                )
                missing_ingredients.append(recipe_ingredient.ingredient_id)

        if missing_ingredients:
            _log.warning(
                "Missing nutritional info for {} ingredients: {}",
                len(missing_ingredients),
                missing_ingredients,
            )

        # Build response based on request parameters
        response = RecipeNutritionalInfoResponse()
        if include_ingredients:
            response.ingredients = ingredients
        if missing_ingredients:
            response.missing_ingredients = missing_ingredients
        if include_total:
            response.total = (
                IngredientNutritionalInfoResponse.calculate_total_nutritional_info(
                    list(ingredients.values()),
                )
            )

        _log.debug("Nutritional info response constructed: {}", response)

        return response

    def get_ingredient_nutritional_info(
        self,
        ingredient_id: int,
        quantity: Quantity | None,
        db: Session,
    ) -> IngredientNutritionalInfoResponse:
        """Fetch nutritional information for a given ingredient and quantity.

        Logs the retrieval request and returns a response with
        ingredient details, macro-nutrients, vitamins, minerals, and allergies.

        Args:
            ingredient_id (int): The unique identifier of the ingredient.
            quantity (Quantity | None): The amount and unit of the ingredient.
            db (Session): Database session for ORM operations.

        Returns:
            IngredientNutritionalInfoResponse: Nutritional info response schema
                containing ingredient details and nutritional values.
        """
        if quantity is not None:
            _log.info(
                "Getting nutritional info for ingredient ID {} ({} {})",
                ingredient_id,
                quantity.amount,
                quantity.measurement,
            )
        else:
            _log.info(
                "Getting nutritional info for ingredient ID {} (default quantity)",
                ingredient_id,
            )

        # Extract the ingredient name from the database
        ingredient = (
            db.query(Ingredient)
            .filter(Ingredient.ingredient_id == ingredient_id)
            .first()
        )
        if not ingredient:
            _log.error("Ingredient with ID {} not found", ingredient_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ingredient with ID {ingredient_id} not found",
            )

        ingredient_name = ingredient.name
        _log.debug("Found ingredient: {}", ingredient)

        # Search for nutritional info by ingredient name (fuzzy matching)
        nutritional_info = (
            db.query(NutritionalInfo)
            .filter(
                NutritionalInfo.product_name.ilike(f"%{ingredient_name}%"),
            )
            .first()
        )

        if not nutritional_info:
            # Try fallback search by generic name
            nutritional_info = (
                db.query(NutritionalInfo)
                .filter(
                    NutritionalInfo.generic_name.ilike(f"%{ingredient_name}%"),
                )
                .first()
            )

        if not nutritional_info:
            _log.warning(
                "No nutritional info found for ingredient: '{}'",
                ingredient_name,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Nutritional information for ingredient '{ingredient_name}' "
                    "not found"
                ),
            )

        _log.debug(
            "Found nutritional info for ingredient ID {}: {}",
            ingredient_id,
            nutritional_info,
        )

        # Convert database model to schema model and adjust quantity, reporting errors
        try:
            response = IngredientNutritionalInfoResponse.from_db_model(
                nutritional_info,
            )
            _log.debug(
                "Successfully converted nutritional info for '{}'",
                ingredient_name,
            )
        except (ValueError, TypeError, AttributeError) as e:
            _log.exception(
                "Error converting nutritional info for '{}'",
                ingredient_name,
                e,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Error converting nutritional info for '{ingredient_name}': {e}"
                ),
            ) from e

        if quantity:
            try:
                response.adjust_quantity(quantity)
                _log.debug(
                    "Adjusted nutritional info for '{}' to quantity {} {}: {}",
                    ingredient_name,
                    quantity.amount,
                    quantity.measurement,
                    response,
                )
            except IncompatibleUnitsError as e:
                _log.warning(
                    "Incompatible unit conversion requested for '{}': {} to {}",
                    ingredient_name,
                    e.from_unit,
                    e.to_unit,
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Cannot convert nutritional info for '{ingredient_name}' "
                        f"from {e.from_unit} to {e.to_unit}: incompatible units"
                    ),
                ) from e
            except (ValueError, TypeError, AttributeError) as e:
                _log.exception(
                    "Error adjusting nutritional info for '{}' to quantity {} {}",
                    ingredient_name,
                    quantity.amount,
                    quantity.measurement,
                    e,
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=(
                        f"Error adjusting nutritional info to requested quantity for "
                        f"'{ingredient_name}': {e}"
                    ),
                ) from e

        return response
