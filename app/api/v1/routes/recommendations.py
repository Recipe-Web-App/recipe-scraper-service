"""Recommendation-related route handlers.

Provides API endpoints for handling recommendations such as pairings & substitutions.
"""

from typing import Annotated

from fastapi import APIRouter, Path, Query
from fastapi.params import Depends
from fastapi.responses import JSONResponse

from app.api.v1.schemas.common.ingredient import Quantity
from app.api.v1.schemas.common.pagination_params import PaginationParams
from app.api.v1.schemas.response.pairing_suggestions_response import (
    PairingSuggestionsResponse,
)
from app.api.v1.schemas.response.recommended_substitutions_response import (
    RecommendedSubstitutionsResponse,
)
from app.services.recipe_scraper_service import RecipeScraperService


def get_recipe_scraper_service() -> RecipeScraperService:
    """Dependency provider function to instantiate RecipeScraperService.

    Returns:
        RecipeScraperService: A new instance of RecipeScraperService.
    """
    return RecipeScraperService()


router = APIRouter()


@router.get(
    "/recipe-scraper/ingredients/{ingredient_id}/recommended-substitutions",
    tags=["ingredient", "recommendations"],
    summary="Get substitutions for ingredient",
    description="Returns a list of recommended substitutions for the given ingredient.",
    response_class=JSONResponse,
)
def get_recommended_substitutions(  # noqa: PLR0913
    service: Annotated[RecipeScraperService, Depends(get_recipe_scraper_service)],
    ingredient_id: Annotated[
        int,
        Path(
            gt=0,
            description="The ID of the ingredient (must be > 0)",
        ),
    ],
    limit: Annotated[int, Query(ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    count_only: Annotated[bool, Query()] = False,
    quantity_value: Annotated[
        float | None,
        Query(
            gt=0,
            description="Quantity value for the ingredient",
        ),
    ] = None,
    measurement: Annotated[
        str | None,
        Query(
            min_length=1,
            description="Measurement unit for the quantity",
        ),
    ] = None,
) -> RecommendedSubstitutionsResponse:
    """Endpoint to return recommended substitutes for an ingredient from the internet.

    Args:
        service (RecipeScraperService): RecipeScraperService dependency for processing
            the recipe.
        ingredient_id (int): The ID of the ingredient (must be > 0).
        limit (int): Number of items per page (minimum 1).
        offset (int): Number of items to skip (minimum 0).
        count_only (bool): Whether to return only count instead of substitutions.
        quantity_value (float): Quantity value for the ingredient.
        measurement (str): Measurement unit for the quantity.

    Returns:
        RecommendedSubstitutionsResponse: A list of recommended substitutions for the
            ingredient.
    """
    # Create pagination params from individual parameters
    pagination = PaginationParams(
        limit=limit,
        offset=offset,
        count_only=count_only,
    )

    quantity = Quantity(quantity_value=quantity_value, measurement=measurement)
    return service.get_recommended_substitutions(
        ingredient_id,
        quantity,
        pagination,
    )


@router.get(
    "/recipe-scraper/recipes/{recipe_id}/pairing-suggestions",
    tags=["recipe", "recommendations"],
    summary="Recommend pairings for a recipe",
    description="Recommends various recipes to pair with the given recipe.",
    response_class=JSONResponse,
)
def get_pairing_suggestions(
    service: Annotated[RecipeScraperService, Depends(get_recipe_scraper_service)],
    recipe_id: Annotated[
        int,
        Path(gt=0, description="The ID of the ingredient (must be > 0)"),
    ],
    limit: Annotated[int, Query(ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    count_only: Annotated[bool, Query()] = False,
) -> PairingSuggestionsResponse:
    """Endpoint to take a recipe and return a list of suggested pairings.

    Args:
        service (RecipeScraperService): Service to use for processing the request.
        recipe_id (int): The ID of the ingredient.
        limit (int): Number of items per page (minimum 1).
        offset (int): Number of items to skip (minimum 0).
        count_only (bool): Whether to return only count instead of pairing suggestions.

    Returns:
        PairingSuggestionsResponse: The list of generated pairing suggestions.
    """
    # Create pagination params from individual parameters
    pagination = PaginationParams(
        limit=limit,
        offset=offset,
        count_only=count_only,
    )

    return service.get_pairing_suggestions(
        recipe_id,
        pagination,
    )
