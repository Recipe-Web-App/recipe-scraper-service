"""Ingredient endpoints.

Provides:
- GET /ingredients/{ingredientId}/nutritional-info for fetching nutrition data
- GET /ingredients/{ingredientId}/allergens for fetching allergen data
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import (
    get_allergen_service,
    get_nutrition_service,
    get_shopping_service,
)
from app.auth.dependencies import CurrentUser, RequirePermissions
from app.auth.permissions import Permission
from app.observability.logging import get_logger
from app.schemas.allergen import IngredientAllergenResponse
from app.schemas.enums import IngredientUnit
from app.schemas.ingredient import Quantity
from app.schemas.nutrition import IngredientNutritionalInfoResponse
from app.schemas.shopping import IngredientShoppingInfoResponse
from app.services.allergen.service import AllergenService  # noqa: TC001
from app.services.nutrition.exceptions import ConversionError
from app.services.nutrition.service import NutritionService  # noqa: TC001
from app.services.shopping.exceptions import IngredientNotFoundError
from app.services.shopping.service import ShoppingService  # noqa: TC001


logger = get_logger(__name__)

router = APIRouter(tags=["Ingredients"])


@router.get(
    "/ingredients/{ingredient_id}/nutritional-info",
    response_model=IngredientNutritionalInfoResponse,
    summary="Get nutritional information for an ingredient",
    description=(
        "Retrieves comprehensive nutritional data for an ingredient including "
        "macronutrients, vitamins, and minerals. Optionally specify amount and "
        "measurement to scale the nutritional values. If not specified, returns "
        "values for 100 grams."
    ),
    responses={
        400: {
            "description": "Invalid parameters (amount/measurement must be provided together)",
            "content": {
                "application/json": {
                    "example": {
                        "error": "INVALID_QUANTITY_PARAMS",
                        "message": (
                            "Both 'amount' and 'measurement' must be provided "
                            "together, or neither"
                        ),
                    }
                }
            },
        },
        404: {
            "description": "Ingredient not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": "INGREDIENT_NOT_FOUND",
                        "message": "No nutritional data found for ingredient: xyz",
                    }
                }
            },
        },
        422: {
            "description": "Invalid measurement unit or conversion failed",
            "content": {
                "application/json": {
                    "example": {
                        "error": "CONVERSION_ERROR",
                        "message": "Unable to convert quantity: Cannot convert PIECE to grams",
                    }
                }
            },
        },
        503: {
            "description": "Nutrition service unavailable",
        },
    },
)
async def get_ingredient_nutritional_info(
    ingredient_id: str,
    user: Annotated[CurrentUser, Depends(RequirePermissions(Permission.RECIPE_READ))],
    nutrition_service: Annotated[NutritionService, Depends(get_nutrition_service)],
    amount: Annotated[
        float | None,
        Query(
            gt=0,
            description="Quantity amount (must be provided with measurement)",
        ),
    ] = None,
    measurement: Annotated[
        IngredientUnit | None,
        Query(
            description="Unit of measurement (must be provided with amount)",
        ),
    ] = None,
) -> IngredientNutritionalInfoResponse:
    """Get nutritional information for an ingredient.

    This endpoint retrieves nutritional data from the USDA FoodData Central
    database. If amount and measurement are provided, the nutritional values
    are scaled accordingly. Defaults to 100 grams if no quantity is specified.

    Args:
        ingredient_id: The ingredient name/identifier.
        user: Authenticated user with RECIPE_READ permission.
        nutrition_service: Service for fetching nutritional data.
        amount: Optional quantity amount for scaling.
        measurement: Optional unit of measurement for scaling.

    Returns:
        Nutritional information for the ingredient.

    Raises:
        HTTPException: 400 if only one of amount/measurement provided.
        HTTPException: 404 if ingredient not found.
        HTTPException: 422 if unit conversion fails.
    """
    # Validate that amount and measurement are provided together
    if (amount is None) != (measurement is None):
        logger.warning(
            "Invalid quantity parameters",
            ingredient_id=ingredient_id,
            amount=amount,
            measurement=measurement,
            user_id=user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_QUANTITY_PARAMS",
                "message": (
                    "Both 'amount' and 'measurement' must be provided together, "
                    "or neither"
                ),
            },
        )

    # Build quantity - default to 100g if not specified
    if amount is not None and measurement is not None:
        quantity = Quantity(amount=amount, measurement=measurement)
    else:
        quantity = Quantity(amount=100.0, measurement=IngredientUnit.G)

    logger.info(
        "Fetching nutritional info",
        ingredient_id=ingredient_id,
        quantity_amount=quantity.amount,
        quantity_measurement=quantity.measurement,
        user_id=user.id,
    )

    # Get nutrition data from service
    try:
        result = await nutrition_service.get_ingredient_nutrition(
            name=ingredient_id,
            quantity=quantity,
        )
    except ConversionError as e:
        logger.warning(
            "Unit conversion failed",
            ingredient_id=ingredient_id,
            measurement=str(measurement),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "CONVERSION_ERROR",
                "message": f"Unable to convert quantity: {e}",
            },
        ) from None

    if result is None:
        logger.info(
            "Ingredient not found",
            ingredient_id=ingredient_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "INGREDIENT_NOT_FOUND",
                "message": f"No nutritional data found for ingredient: {ingredient_id}",
            },
        )

    logger.debug(
        "Returning nutritional info",
        ingredient_id=ingredient_id,
        has_macros=result.macro_nutrients is not None,
        has_vitamins=result.vitamins is not None,
        has_minerals=result.minerals is not None,
    )

    return result


@router.get(
    "/ingredients/{ingredient_id}/allergens",
    response_model=IngredientAllergenResponse,
    summary="Get allergen information for an ingredient",
    description=(
        "Retrieves allergen data for an ingredient using a tiered lookup: "
        "database → Open Food Facts → LLM inference. Returns known allergens "
        "and their presence type (contains, may contain, traces)."
    ),
    responses={
        404: {
            "description": "Ingredient not found or no allergen data available",
            "content": {
                "application/json": {
                    "example": {
                        "error": "INGREDIENT_NOT_FOUND",
                        "message": "No allergen data found for ingredient: xyz",
                    }
                }
            },
        },
        503: {
            "description": "Allergen service unavailable",
        },
    },
)
async def get_ingredient_allergens(
    ingredient_id: str,
    user: Annotated[CurrentUser, Depends(RequirePermissions(Permission.RECIPE_READ))],
    allergen_service: Annotated[AllergenService, Depends(get_allergen_service)],
) -> IngredientAllergenResponse:
    """Get allergen information for an ingredient.

    This endpoint retrieves allergen data using a tiered lookup strategy:
    1. Database (cached allergen profiles)
    2. Open Food Facts API
    3. LLM inference (for complex/uncommon ingredients)

    Args:
        ingredient_id: The ingredient name/identifier.
        user: Authenticated user with RECIPE_READ permission.
        allergen_service: Service for fetching allergen data.

    Returns:
        Allergen information for the ingredient.

    Raises:
        HTTPException: 404 if ingredient not found or no allergen data.
    """
    logger.info(
        "Fetching allergen info",
        ingredient_id=ingredient_id,
        user_id=user.id,
    )

    result = await allergen_service.get_ingredient_allergens(name=ingredient_id)

    if result is None:
        logger.info(
            "Ingredient allergen data not found",
            ingredient_id=ingredient_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "INGREDIENT_NOT_FOUND",
                "message": f"No allergen data found for ingredient: {ingredient_id}",
            },
        )

    # data_source may be string (due to use_enum_values=True) or enum
    data_source = result.data_source
    data_source_str = (
        (data_source if isinstance(data_source, str) else data_source.value)
        if data_source
        else None
    )

    logger.debug(
        "Returning allergen info",
        ingredient_id=ingredient_id,
        allergen_count=len(result.allergens),
        data_source=data_source_str,
    )

    return result


@router.get(
    "/ingredients/{ingredient_id}/shopping-info",
    response_model=IngredientShoppingInfoResponse,
    summary="Get shopping information for an ingredient",
    description=(
        "Retrieves shopping information for a specific ingredient, including "
        "estimated prices, availability, and quantity conversions for grocery shopping. "
        "Uses a two-tier pricing lookup: direct ingredient pricing, then food group averages."
    ),
    responses={
        400: {
            "description": "Invalid parameters (amount/measurement must be provided together)",
            "content": {
                "application/json": {
                    "example": {
                        "error": "INVALID_QUANTITY_PARAMS",
                        "message": (
                            "Both 'amount' and 'measurement' must be provided "
                            "together, or neither"
                        ),
                    }
                }
            },
        },
        404: {
            "description": "Ingredient not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": "INGREDIENT_NOT_FOUND",
                        "message": "Ingredient not found: 12345",
                    }
                }
            },
        },
        422: {
            "description": "Invalid measurement unit or conversion failed",
            "content": {
                "application/json": {
                    "example": {
                        "error": "CONVERSION_ERROR",
                        "message": "Unable to convert quantity: Cannot convert PIECE to grams",
                    }
                }
            },
        },
        503: {
            "description": "Shopping service unavailable",
        },
    },
)
async def get_ingredient_shopping_info(
    ingredient_id: int,
    user: Annotated[CurrentUser, Depends(RequirePermissions(Permission.RECIPE_READ))],
    shopping_service: Annotated[ShoppingService, Depends(get_shopping_service)],
    amount: Annotated[
        float | None,
        Query(
            gt=0,
            description="Quantity amount (must be provided with measurement)",
        ),
    ] = None,
    measurement: Annotated[
        IngredientUnit | None,
        Query(
            description="Unit of measurement (must be provided with amount)",
        ),
    ] = None,
) -> IngredientShoppingInfoResponse:
    """Get shopping information for an ingredient.

    This endpoint retrieves pricing data using a two-tier lookup strategy:
    1. Direct ingredient pricing from ingredient_pricing table
    2. Food group average pricing from food_group_pricing table (fallback)

    If amount and measurement are provided, the price is calculated for that
    quantity. Otherwise, returns price information for 100 grams.

    Args:
        ingredient_id: The ingredient database ID.
        user: Authenticated user with RECIPE_READ permission.
        shopping_service: Service for fetching shopping data.
        amount: Optional quantity amount for price calculation.
        measurement: Optional unit of measurement for price calculation.

    Returns:
        Shopping information for the ingredient.

    Raises:
        HTTPException: 400 if only one of amount/measurement provided.
        HTTPException: 404 if ingredient not found.
        HTTPException: 422 if unit conversion fails.
    """
    # Validate that amount and measurement are provided together
    if (amount is None) != (measurement is None):
        logger.warning(
            "Invalid quantity parameters for shopping info",
            ingredient_id=ingredient_id,
            amount=amount,
            measurement=measurement,
            user_id=user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_QUANTITY_PARAMS",
                "message": (
                    "Both 'amount' and 'measurement' must be provided together, "
                    "or neither"
                ),
            },
        )

    # Build quantity - default to 100g if not specified
    quantity: Quantity | None = None
    if amount is not None and measurement is not None:
        quantity = Quantity(amount=amount, measurement=measurement)

    logger.info(
        "Fetching shopping info",
        ingredient_id=ingredient_id,
        quantity_amount=quantity.amount if quantity else None,
        quantity_measurement=str(quantity.measurement) if quantity else None,
        user_id=user.id,
    )

    # Get shopping data from service
    try:
        result = await shopping_service.get_ingredient_shopping_info(
            ingredient_id=ingredient_id,
            quantity=quantity,
        )
    except IngredientNotFoundError:
        logger.info(
            "Ingredient not found for shopping info",
            ingredient_id=ingredient_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "INGREDIENT_NOT_FOUND",
                "message": f"Ingredient not found: {ingredient_id}",
            },
        ) from None
    except ConversionError as e:
        logger.warning(
            "Unit conversion failed for shopping info",
            ingredient_id=ingredient_id,
            measurement=str(measurement) if measurement else None,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "CONVERSION_ERROR",
                "message": f"Unable to convert quantity: {e}",
            },
        ) from None

    logger.debug(
        "Returning shopping info",
        ingredient_id=ingredient_id,
        ingredient_name=result.ingredient_name,
        has_price=result.estimated_price is not None,
        data_source=result.data_source,
    )

    return result
