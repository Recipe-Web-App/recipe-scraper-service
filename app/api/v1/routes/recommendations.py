"""Recommendation-related route handlers.

Provides API endpoints for handling recommendations such as pairings & substitutions.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.params import Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.v1.schemas.common.ingredient import Quantity
from app.api.v1.schemas.common.pagination_params import PaginationParams
from app.api.v1.schemas.response.pairing_suggestions_response import (
    PairingSuggestionsResponse,
)
from app.api.v1.schemas.response.recommended_substitutions_response import (
    RecommendedSubstitutionsResponse,
)
from app.deps.db import get_db
from app.services.recommendations_service import RecommendationsService


@lru_cache(maxsize=1)
def get_recommendations_service() -> RecommendationsService:
    """Dependency provider function to get RecommendationsService instance.

    Uses @lru_cache to ensure only one instance is created and reused.

    Returns:
        RecommendationsService: The service instance.
    """
    return RecommendationsService()


router = APIRouter()


@router.get(
    "/recipe-scraper/ingredients/{ingredient_id}/recommended-substitutions",
    tags=["ingredient", "recommendations"],
    summary="Get substitutions for ingredient",
    description="Returns a list of recommended substitutions for the given ingredient.",
    response_class=JSONResponse,
)
def get_recommended_substitutions(  # noqa: PLR0913
    service: Annotated[RecommendationsService, Depends(get_recommendations_service)],
    db: Annotated[Session, Depends(get_db)],
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
    """Endpoint to return recommended substitutes for an ingredient using AI.

    Args:
        service (RecommendationsService): Service used to process the request.
        db (Session): Database session dependency for ingredient lookup.
        ingredient_id (int): The ID of the ingredient (must be > 0).
        limit (int): Number of items per page (minimum 1).
        offset (int): Number of items to skip (minimum 0).
        count_only (bool): Whether to return only count instead of substitutions.
        quantity_value (float): Quantity value for the ingredient.
        measurement (str): Measurement unit for the quantity.

    Returns:
        RecommendedSubstitutionsResponse: A list of AI-powered recommended
            substitutions for the ingredient.
    """
    # Create pagination params from individual parameters
    pagination = PaginationParams(
        limit=limit,
        offset=offset,
        count_only=count_only,
    )

    if (quantity_value is not None) != (measurement is not None):
        raise HTTPException(
            status_code=400,
            detail="Both quantity_value and measurement must be provided together.",
        )
    if quantity_value is not None and measurement is not None:
        quantity = Quantity(amount=quantity_value, measurement=measurement)
    else:
        quantity = None
    return service.get_recommended_substitutions(
        ingredient_id,
        quantity,
        pagination,
        db,
    )


@router.get(
    "/recipe-scraper/recipes/{recipe_id}/pairing-suggestions",
    tags=["recipe", "recommendations"],
    summary="Recommend pairings for a recipe",
    description="Recommends various recipes to pair with the given recipe.",
    response_class=JSONResponse,
)
def get_pairing_suggestions(
    service: Annotated[RecommendationsService, Depends(get_recommendations_service)],
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
        service (RecommendationsService): Service to use to process the request.
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
