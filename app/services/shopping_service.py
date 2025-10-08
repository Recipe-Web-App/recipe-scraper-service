"""Shopping service module.

Provides functionality to retrieve pricing and shopping information for ingredients and
recipes based on their IDs and specified quantities.

Includes logging for traceability and debugging.
"""

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.v1.schemas.common.ingredient import Quantity
from app.api.v1.schemas.downstream.kroger.ingredient_price import KrogerIngredientPrice
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
from app.exceptions.custom_exceptions import (
    DownstreamAuthenticationError,
    DownstreamDataNotFoundError,
    DownstreamServiceUnavailableError,
    IncompatibleUnitsError,
)
from app.services.downstream.kroger_service import KrogerService

_log = get_logger(__name__)


class ShoppingService:
    """Service to retrieve shopping and pricing information.

    This service provides methods to obtain detailed pricing data based on given
    database identifiers.

    Attributes:
        log (logging.Logger): Logger instance for this service.
        kroger_service (KrogerService): Service for getting real pricing data from
            Kroger API.
    """

    def __init__(self) -> None:
        """Initialize the shopping service with downstream services."""
        self.kroger_service = KrogerService()

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
                if shopping_info.estimated_price is not None:
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
        # If no requested quantity, just request 1 unit
        if not quantity:
            quantity = Quantity(amount=1.0, measurement=IngredientUnitEnum.UNIT)

        # Try to get real pricing from Kroger API
        try:
            kroger_price = self.kroger_service.get_ingredient_price(ingredient.name)
            # Use Kroger pricing data
            estimated_price = self._calculate_price_with_kroger_data(
                kroger_price,
                quantity,
            )
            _log.debug(
                "Found Kroger price for '{}': ${} per {}",
                ingredient.name,
                kroger_price.price,
                kroger_price.unit,
            )
        except DownstreamAuthenticationError as e:
            # Authentication failed - this is a configuration issue
            _log.error(
                "Kroger API authentication failed - check API credentials",
                extra={
                    "error_type": "configuration_error",
                    "service": "shopping_service",
                    "operation": "get_ingredient_shopping_info",
                    "ingredient_name": ingredient.name,
                    "downstream_error": str(e),
                },
            )
            # Re-raise authentication errors to inform users of misconfiguration
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Pricing service authentication failed. "
                    "Please check service configuration."
                ),
            ) from e
        except DownstreamServiceUnavailableError as e:
            # Service temporarily unavailable - log and continue without pricing
            _log.warning(
                "Kroger API temporarily unavailable - pricing unavailable",
                extra={
                    "error_type": "service_unavailable",
                    "service": "shopping_service",
                    "operation": "get_ingredient_shopping_info",
                    "ingredient_name": ingredient.name,
                    "downstream_error": str(e),
                    "fallback_action": "continue_without_pricing",
                },
            )
            estimated_price = None
        except DownstreamDataNotFoundError:
            # No pricing data available for this ingredient - this is normal
            _log.debug(
                "No Kroger price found - pricing unavailable",
                extra={
                    "service": "shopping_service",
                    "operation": "get_ingredient_shopping_info",
                    "ingredient_name": ingredient.name,
                    "result": "no_pricing_data",
                },
            )
            estimated_price = None

        return IngredientShoppingInfoResponse(
            ingredient_name=ingredient.name,
            quantity=quantity,
            estimated_price=(
                round(float(estimated_price), 2)
                if estimated_price is not None
                else None
            ),
        )

    def _calculate_price_with_kroger_data(
        self,
        kroger_price: KrogerIngredientPrice,
        requested_quantity: Quantity,
    ) -> Decimal:
        """Calculate estimated price using Kroger pricing data.

        Args:
            kroger_price: KrogerIngredientPrice object with pricing info
            requested_quantity: Amount of ingredient needed

        Returns:
            Estimated price as Decimal
        """
        # For now, use simple multiplication
        # TODO(jsamuelsen11): Implement proper unit conversion between
        # requested_unit and kroger_price.unit
        base_price = Decimal(str(kroger_price.price))
        estimated_price = base_price * Decimal(requested_quantity.amount)

        _log.debug(
            "Calculated price: ${} * {} = ${}",
            base_price,
            requested_quantity,
            estimated_price,
        )

        return estimated_price
