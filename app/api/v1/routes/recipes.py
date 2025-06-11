"""Recipe-related route handlers.

Provides API endpoints for handling recipes, such as parsing from the web & providing
popular links.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header
from fastapi.params import Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.v1.schemas.common.pagination_params import PaginationParams
from app.api.v1.schemas.request.create_recipe_request import CreateRecipeRequest
from app.api.v1.schemas.response.create_recipe_response import CreateRecipeResponse
from app.api.v1.schemas.response.recommended_recipes_response import (
    PopularRecipesResponse,
)
from app.core.logging import get_logger
from app.deps.db import get_db
from app.services.recipe_scraper_service import RecipeScraperService

__log = get_logger("RecipeScraperRoutes")


def get_recipe_scraper_service() -> RecipeScraperService:
    """Dependency provider function to instantiate RecipeScraperService.

    Returns:
        RecipeScraperService: A new instance of RecipeScraperService.
    """
    return RecipeScraperService()


router = APIRouter()


@router.post(
    "/recipe-scraper/create-recipe",
    tags=["recipe", "recipe-scraper"],
    summary="Create a recipe from a URL",
    description="Creates a recipe from the given URL and adds it to the database.",
    response_class=JSONResponse,
)
def create_recipe(
    service: Annotated[RecipeScraperService, Depends(get_recipe_scraper_service)],
    db: Annotated[Session, Depends(get_db)],
    request: CreateRecipeRequest,
    user_id: Annotated[UUID, Header(..., alias="X-User-ID")],
) -> CreateRecipeResponse:
    """Endpoint to create a recipe from a given URL and add it to the database.

    Args:
        service (RecipeScraperService): Service for recipe scraping logic.
        db (Session): Database session dependency.
        request (CreateRecipeRequest): Request body containing the recipe URL.
        user_id (UUID): The unique identifier of the user making the request.

    Returns:
        CreateRecipeResponse: The created recipe response.
    """
    return service.create_recipe(request.recipe_url, db, user_id=user_id)


@router.get(
    "/recipe-scraper/popular-recipes",
    tags=["recipe", "recipe-scraper"],
    summary="Get popular recipes from internet",
    description=(
        "Returns a list of URLs pointing to popular recipes from around the internet."
    ),
    response_class=JSONResponse,
)
def get_popular_recipes(
    service: Annotated[RecipeScraperService, Depends(get_recipe_scraper_service)],
    pagination: Annotated[PaginationParams, Depends()],
) -> PopularRecipesResponse:
    """Endpoint to extract popular recipes from the internet.

    Args:
        service (RecipeScraperService):
            RecipeScraperService dependency for processing the recipe.
        pagination (PaginationParams): Pagination parameters for response control.

    Returns:
        PopularRecipesResponse: A list of all gathered recipe data.
    """
    return service.get_popular_recipes(pagination)
