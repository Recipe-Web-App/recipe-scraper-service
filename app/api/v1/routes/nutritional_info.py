"""Nutritional-info-related route handlers.

Contains API endpoints for managing and querying ingredients, including creation,
retrieval, updating, and deletion.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse

from app.api.v1.schemas.common.ingredient import Quantity
from app.api.v1.schemas.response.ingredient_nutritional_info_response import (
    IngredientNutritionalInfoResponse,
)
from app.api.v1.schemas.response.recipe_nutritional_info_response import (
    RecipeNutritionalInfoResponse,
)
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
)
def get_nutritional_info_for_recipe(
    service: Annotated[NutritionalInfoService, Depends(get_nutritional_info_service)],
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
) -> RecipeNutritionalInfoResponse:
    """Endpoint to get nutritional information for a recipe.

    Args:
        service (NutritionalInfoService): Injected service for retrieving nutritional
          info.
        recipe_id (int): The ID of the recipe (must be greater than 0).
        include_total (bool): Whether to include the total nutritional values.
        include_ingredients (bool): Whether to include per-ingredient nutritional info.

    Returns:
        RecipeNutritionalInfoResponse: The aggregated nutritional information for the
          recipe.
    """
    return service.get_recipe_nutritional_info(
        recipe_id,
        include_total,
        include_ingredients,
    )


@router.get(
    "/recipe-scraper/ingredients/{ingredient_id}/nutritional-info",
    tags=["ingredient"],
    summary="Get nutritional info for an ingredient",
    description="Returns all nutritional info for the given ingredient.",
    response_class=JSONResponse,
)
def get_nutritional_info_for_ingredient(
    service: Annotated[NutritionalInfoService, Depends(get_nutritional_info_service)],
    ingredient_id: Annotated[
        int,
        Path(gt=0, description="The ID of the ingredient (must be > 0)"),
    ],
    quantity_value: Annotated[
        float,
        Query(gt=0, description="Quantity value for the ingredient"),
    ],
    measurement: Annotated[
        str,
        Query(min_length=1, description="Measurement unit for the quantity"),
    ],
) -> IngredientNutritionalInfoResponse:
    """Endpoint to get the nutritional information for a given ingredient ID.

    Uses dependency injection to provide the NutritionalInfoService instance,
    creating a stateless and testable route handler.

    Args:
        ingredient_id (int): The ID of the ingredient.
        quantity_value (float): The quantity value for the ingredient.
        measurement (str): The measurement unit for the quantity.
        service (NutritionalInfoService): The service instance (injected).

    Returns:
        IngredientNutritionalInfoResponse: Nutritional information for the ingredient.
    """
    quantity = Quantity(quantity_value=quantity_value, measurement=measurement)
    return service.get_ingredient_nutritional_info(ingredient_id, quantity)
