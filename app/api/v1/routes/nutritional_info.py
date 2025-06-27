"""Nutritional-info-related route handlers.

Contains API endpoints for managing and querying ingredients, including creation,
retrieval, updating, and deletion.
"""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.v1.schemas.common.ingredient import Quantity
from app.api.v1.schemas.response.ingredient_nutritional_info_response import (
    IngredientNutritionalInfoResponse,
)
from app.api.v1.schemas.response.recipe_nutritional_info_response import (
    RecipeNutritionalInfoResponse,
)
from app.deps.db import get_db
from app.enums.ingredient_unit_enum import IngredientUnitEnum
from app.services.nutritional_info_service import NutritionalInfoService

router = APIRouter()


def get_nutritional_info_service() -> NutritionalInfoService:
    """Dependency provider function to instantiate NutritionalInfoService.

    Returns:
        NutritionalInfoService: A new instance of NutritionalInfoService.
    """
    return NutritionalInfoService()


@router.get(
    "/recipe-scraper/recipes/{recipe_id}/nutritional-info",
    tags=["recipe", "nutritional-info"],
    summary="Get nutritional info for a recipe",
    description=(
        "Returns a list of all nutritional info for all ingredients in the recipe."
    ),
    response_class=JSONResponse,
    response_model=RecipeNutritionalInfoResponse,
)
def get_nutritional_info_for_recipe(
    service: Annotated[NutritionalInfoService, Depends(get_nutritional_info_service)],
    db: Annotated[Session, Depends(get_db)],
    recipe_id: Annotated[
        int,
        Path(gt=0, description="The ID of the recipe (must be > 0)"),
    ],
    include_total: Annotated[
        bool,
        Query(
            description="Indicates that a total sum of all nutritional info should "
            "be included in the response.",
        ),
    ] = True,
    include_ingredients: Annotated[
        bool,
        Query(
            description="Indicates that nutritional info for all ingredients should "
            "be included in the response.",
        ),
    ] = False,
) -> RecipeNutritionalInfoResponse | Response:
    """Endpoint to get nutritional information for a recipe.

    Args:
        service (NutritionalInfoService): Injected service for retrieving nutritional
            info.
        db (Session): Injected database session for ORM operations.
        recipe_id (int): The ID of the recipe (must be greater than 0).
        include_total (bool): Whether to include the total nutritional values.
        include_ingredients (bool): Whether to include per-ingredient nutritional info.

    Returns:
        RecipeNutritionalInfoResponse: The aggregated nutritional information for the
            recipe.
    """
    if not (include_total or include_ingredients):
        raise HTTPException(
            status_code=400,
            detail="At least one of 'include_total' or 'include_ingredients' must be "
            "true.",
        )

    response = service.get_recipe_nutritional_info(
        recipe_id,
        include_total,
        include_ingredients,
        db,
    )

    if response.missing_ingredients:
        # Return 206 Partial Content with the response data
        return Response(
            content=json.dumps(response.model_dump(), default=str),
            status_code=206,
            headers={
                "Content-Type": "application/json",
                "X-Partial-Content": "true",
            },
        )

    return response


@router.get(
    "/recipe-scraper/ingredients/{ingredient_id}/nutritional-info",
    tags=["ingredient"],
    summary="Get nutritional info for an ingredient",
    description="Returns all nutritional info for the given ingredient.",
    response_class=JSONResponse,
)
def get_nutritional_info_for_ingredient(
    service: Annotated[NutritionalInfoService, Depends(get_nutritional_info_service)],
    db: Annotated[Session, Depends(get_db)],
    ingredient_id: Annotated[
        int,
        Path(gt=0, description="The ID of the ingredient (must be > 0)"),
    ],
    quantity_value: Annotated[
        float | None,
        Query(gt=0, description="Quantity value for the ingredient"),
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
) -> IngredientNutritionalInfoResponse:
    """Endpoint to get the nutritional information for a given ingredient ID.

    Uses dependency injection to provide the NutritionalInfoService instance,
    creating a stateless and testable route handler.

    Args:
        service (NutritionalInfoService): The service instance (injected).
        db (Session): Injected database session for ORM operations.
        ingredient_id (int): The ID of the ingredient.
        quantity_value (float): The quantity value for the ingredient.
        measurement (str): The measurement unit for the quantity.

    Returns:
        IngredientNutritionalInfoResponse: Nutritional information for the ingredient.
    """
    if (quantity_value is None) != (measurement is None):
        raise HTTPException(
            status_code=400,
            detail=(
                "Both 'quantity_value' and 'measurement' must be provided "
                "together when used."
            ),
        )

    quantity = (
        Quantity(amount=quantity_value, measurement=measurement)
        if quantity_value and measurement
        else None
    )

    return service.get_ingredient_nutritional_info(
        ingredient_id,
        quantity,
        db,
    )
