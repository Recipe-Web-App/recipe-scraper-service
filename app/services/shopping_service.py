"""Shopping service module.

Provides functionality to retrieve pricing and shopping information for ingredients and
recipes based on their IDs and specified quantities.

Includes logging for traceability and debugging.
"""

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.v1.schemas.common.ingredient import Quantity
from app.api.v1.schemas.response.ingredient_shopping_info_response import (
    IngredientShoppingInfoResponse,
)
from app.api.v1.schemas.response.recipe_shopping_info_response import (
    RecipeShoppingInfoResponse,
)
from app.core.logging import get_logger
from app.db.models.ingredient_models.ingredient import Ingredient
from app.db.models.recipe_models.recipe import Recipe
from app.db.models.recipe_models.recipe_ingredient import RecipeIngredient
from app.enums.ingredient_unit_enum import IngredientUnitEnum
from app.exceptions.custom_exceptions import IncompatibleUnitsError

_log = get_logger(__name__)


class ShoppingService:
    """Service to retrieve shopping and pricing information.

    This service provides methods to obtain detailed pricing data based on given
    database identifiers.

    Attributes:
        log (logging.Logger): Logger instance for this service.
    """

    def get_ingredient_shopping_info(
        self,
        ingredient_id: int,
        quantity: Quantity | None,
        db: Session,
    ) -> IngredientShoppingInfoResponse:
        """Fetch shopping information for a given ingredient and quantity.

        Logs the retrieval request and returns a response with ingredient details
        and pricing information.

        Args:
            ingredient_id (int): The unique identifier of the ingredient.
            quantity (Quantity | None): The amount and unit of the ingredient.
            db (Session): Database session for ORM operations.

        Returns:
            IngredientShoppingInfoResponse: Shopping info response schema containing
                ingredient details and pricing values.

        Raises:
            HTTPException: If ingredient is not found or if there's an error processing
                the request.
        """
        if quantity is not None:
            _log.info(
                "Getting shopping info for ingredient ID {} ({} {})",
                ingredient_id,
                quantity.amount,
                quantity.measurement,
            )
        else:
            _log.info(
                "Getting shopping info for ingredient ID {} (default quantity)",
                ingredient_id,
            )

        # Extract the ingredient from the database
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

        _log.debug("Found ingredient: {}", ingredient)

        try:
            # Calculate pricing based on the ingredient and quantity
            shopping_info = self._get_ingredient_shopping_info(ingredient, quantity)
            _log.debug(
                "Successfully calculated shopping info for ingredient '{}'",
                ingredient.name,
            )
            return shopping_info

        except IncompatibleUnitsError as e:
            _log.warning(
                "Incompatible unit conversion requested for '{}': {} to {}",
                ingredient.name,
                e.from_unit,
                e.to_unit,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot convert quantity for '{ingredient.name}' from "
                    f"{e.from_unit} to {e.to_unit}: incompatible units"
                ),
            ) from e
        except (ValueError, TypeError, AttributeError) as e:
            _log.exception(
                "Error calculating shopping info for '{}'",
                ingredient.name,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Error calculating shopping info for '{ingredient.name}': {e}"
                ),
            ) from e

    def get_recipe_shopping_info(
        self,
        recipe_id: int,
        db: Session,
    ) -> RecipeShoppingInfoResponse:
        """Fetch shopping information for all ingredients in a recipe.

        Logs the retrieval request and returns a response with shopping info for all
        ingredients in the recipe.

        Args:
            recipe_id (int): The unique identifier of the recipe.
            db (Session): Database session for ORM operations.

        Returns:
            RecipeShoppingInfoResponse: Shopping info response schema containing
                individual ingredients and total cost.

        Raises:
            HTTPException: If recipe is not found or if there's an error processing
                the request.
        """
        _log.info("Getting shopping info for recipe ID {}", recipe_id)

        # Get recipe and its ingredients in a single query
        query = (
            db.query(Recipe)
            .outerjoin(Recipe.ingredients)
            .outerjoin(RecipeIngredient.ingredient)
            .filter(Recipe.recipe_id == recipe_id)
            .options(
                joinedload(Recipe.ingredients).joinedload(RecipeIngredient.ingredient)
            )
        )

        # Log the SQL query for debugging
        _log.info("Generated SQL: {}", str(query))

        recipe = query.first()

        if not recipe:
            _log.error("Recipe with ID {} not found", recipe_id)
            # Log more debug info about the query results
            raw_recipe = db.query(Recipe).filter(Recipe.recipe_id == recipe_id).first()
            _log.info("Raw recipe query result: {}", raw_recipe)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recipe with ID {recipe_id} not found",
            )

        _log.debug("Found {} ingredients for recipe", len(recipe.ingredients))

        ingredients: dict[int, IngredientShoppingInfoResponse] = {}
        total_cost = Decimal('0.0')

        # Process each ingredient
        for recipe_ingredient in recipe.ingredients:
            ingredient = recipe_ingredient.ingredient
            try:
                # Create quantity object from recipe ingredient data
                quantity = (
                    Quantity(
                        amount=recipe_ingredient.quantity,
                        measurement=recipe_ingredient.unit,
                    )
                    if recipe_ingredient.quantity and recipe_ingredient.unit
                    else None
                )

                # Calculate shopping info for this ingredient
                shopping_info = self._get_ingredient_shopping_info(ingredient, quantity)
                ingredients[ingredient.ingredient_id] = shopping_info
                total_cost += shopping_info.estimated_price

            except (ValueError, TypeError, AttributeError) as e:
                _log.exception(
                    "Error processing ingredient '{}' (ID: {}): {}",
                    ingredient.name,
                    ingredient.ingredient_id,
                    str(e),
                )
                # Continue processing other ingredients even if one fails
                continue

        return RecipeShoppingInfoResponse(
            recipe_id=recipe_id,
            ingredients=ingredients,
            total_estimated_cost=round(total_cost, 2),
        )

    def _get_ingredient_shopping_info(
        self,
        ingredient: Ingredient,
        quantity: Quantity | None,
    ) -> IngredientShoppingInfoResponse:
        """Calculate shopping information for an ingredient.

        Internal helper method to perform the actual shopping info calculation.
        Uses base units for consistent price calculation:
        - Weight items: calculated in grams
        - Volume items: calculated in milliliters
        - Count items: calculated per unit

        Args:
            ingredient (Ingredient): The ingredient model from the database.
            quantity (Quantity | None): The amount and unit to calculate for.

        Returns:
            IngredientShoppingInfoResponse: Shopping info for the ingredient.

        Raises:
            IncompatibleUnitsError: If the requested unit conversion is not possible.
            ValueError: If there's an error in the calculation.
        """
        # Get requested quantity and unit (from input or default)
        if quantity:
            requested_quantity = Decimal(str(quantity.amount))
            requested_unit = quantity.measurement
        else:
            requested_quantity = Decimal("1.0")
            requested_unit = IngredientUnitEnum.UNIT

        """TODO(Jsamuelsen): Replace with actual price calculation using:
        - Ingredient's preferred unit type from database
        - Proper unit conversion
        - Real pricing data
        """
        mock_price = Decimal("2.50")
        estimated_price = mock_price * requested_quantity

        return IngredientShoppingInfoResponse(
            ingredient_name=ingredient.name,
            # Convert Decimal back to float for response
            quantity=float(requested_quantity),
            unit=requested_unit,
            estimated_price=round(float(estimated_price), 2),
        )
