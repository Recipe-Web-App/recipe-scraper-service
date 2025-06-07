"""Recipe-related route handlers.

Provides API endpoints for handling recipes, such as parsing from the web & providing
popular links.
"""

from typing import Annotated

from fastapi import APIRouter
from fastapi.params import Depends
from fastapi.responses import JSONResponse

from app.api.v1.schemas.common.pagination_params import PaginationParams
from app.api.v1.schemas.request.create_recipe_request import CreateRecipeRequest
from app.api.v1.schemas.response.recommended_recipes_response import (
    PopularRecipesResponse,
)
from app.core.logging import get_logger
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
    request: CreateRecipeRequest,
) -> JSONResponse:
    """Endpoint to extract a recipe from a given URL.

    Args:
        service (RecipeScraperService): RecipeScraperService dependency for processing
            the recipe.
        request (CreateRecipeRequest): Request body containing the recipe URL.

    Returns:
        JSONResponse: Response containing the created recipe data or error details.
    """
    return service.create_recipe(request.recipe_url)


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
