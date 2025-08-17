"""Shopping-related route handlers.

Contains API endpoints for retrieving shopping & pricing information.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.v1.schemas.common.ingredient import Quantity
from app.api.v1.schemas.response.ingredient_shopping_info_response import (
    IngredientShoppingInfoResponse,
)
from app.api.v1.schemas.response.recipe_shopping_info_response import (
    RecipeShoppingInfoResponse,
)
from app.deps.db import get_db
from app.enums.ingredient_unit_enum import IngredientUnitEnum
from app.services.shopping_service import ShoppingService

router = APIRouter()


def get_shopping_service() -> ShoppingService:
    """Dependency provider function to instantiate ShoppingService.

    Returns: ShoppingService: A new instance of ShoppingService.
    """
    return ShoppingService()


@router.get(
    "/recipe-scraper/ingredients/{ingredient_id}/shopping-info",
    tags=["shopping", "recipe-scraper"],
    summary="Get shopping information for an ingredient",
    description="""
                Retrieves shopping information for a specific ingredient, including
                estimated prices and quantity conversions.

                This endpoint provides:
                - Current estimated price for the ingredient
                - Price per unit
                - Optional quantity conversion if amount and measurement are provided
                """,
    response_class=JSONResponse,
    responses={
        200: {
            "description": "Shopping information retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "ingredient_name": "flour",
                        "quantity": 2.5,
                        "unit": "CUPS",
                        "estimated_price": 1.25,
                    }
                }
            },
        },
        400: {
            "description": "Invalid request parameters",
            "content": {
                "application/json": {
                    "example": {
                        "detail": (
                            "Both 'amount' and 'measurement' must be provided "
                            "together when used."
                        )
                    }
                }
            },
        },
        404: {
            "description": "Ingredient not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Ingredient with ID 123 not found"}
                }
            },
        },
    },
)
async def get_ingredient_shopping_info(
    ingredient_id: int,
    service: Annotated[ShoppingService, Depends(get_shopping_service)],
    db: Annotated[Session, Depends(get_db)],
    amount: Annotated[
        float | None,
        Query(gt=0, description="Quantity amount for the ingredient"),
    ] = None,
    measurement: Annotated[
        IngredientUnitEnum | None,
        Query(
            description=(
                "Measurement unit for the quantity. If not provided, "
                "default serving size will be used."
            ),
        ),
    ] = None,
) -> IngredientShoppingInfoResponse:
    """Get shopping information for a specific ingredient.

    Args:
        ingredient_id (int): The unique identifier of the ingredient.
        service (ShoppingService): Service for shopping information logic.
        db (Session): Database session dependency.
        amount (float, optional): Quantity amount for the ingredient.
        measurement (IngredientUnitEnum, optional): Unit of measurement for the
            quantity.

    Returns:
        IngredientShoppingInfoResponse: The shopping information for the ingredient.
    """
    if (amount is None) != (measurement is None):
        raise HTTPException(
            status_code=400,
            detail=(
                "Both 'amount' and 'measurement' must be provided together when used."
            ),
        )

    quantity = (
        Quantity(amount=amount, measurement=measurement)
        if amount and measurement
        else None
    )
    return service.get_ingredient_shopping_info(ingredient_id, quantity, db)


@router.get(
    "/recipe-scraper/recipes/{recipe_id}/shopping-info",
    tags=["shopping", "recipe-scraper"],
    summary="Get shopping information for a complete recipe",
    description="""
        Retrieves shopping information for all ingredients in a recipe,
            including estimated prices and total cost.

        This endpoint provides:
        - List of all ingredients with their quantities
        - Estimated price for each ingredient
        - Total estimated cost for the complete recipe
        """,
    response_class=JSONResponse,
    responses={
        200: {
            "description": "Shopping information retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "recipe_id": 123,
                        "ingredients": {
                            "flour": {
                                "ingredient_name": "flour",
                                "quantity": 2.5,
                                "unit": "CUPS",
                                "estimated_price": 1.25,
                            },
                            "sugar": {
                                "ingredient_name": "sugar",
                                "quantity": 1.0,
                                "unit": "CUPS",
                                "estimated_price": 0.75,
                            },
                        },
                        "total_estimated_cost": 2.00,
                    }
                }
            },
        },
        404: {
            "description": "Recipe not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Recipe with ID 123 not found"}
                }
            },
        },
    },
)
async def get_recipe_shopping_info(
    recipe_id: int,
    service: Annotated[ShoppingService, Depends(get_shopping_service)],
    db: Annotated[Session, Depends(get_db)],
) -> RecipeShoppingInfoResponse:
    """Get shopping information for all ingredients in a recipe.

    Args:
        recipe_id (int): The unique identifier of the recipe.
        service (ShoppingService): Service for shopping information logic.
        db (Session): Database session dependency.

    Returns:
        RecipeShoppingInfoResponse: The shopping information for the recipe.
    """
    return service.get_recipe_shopping_info(recipe_id, db)
