"""Recipe-related route handlers.

Provides API endpoints for handling recipes, such as parsing from the web & providing
popular links.
"""

from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.params import Depends
from fastapi.responses import JSONResponse

from app.api.v1.schemas.common.pagination_params import PaginationParams
from app.api.v1.schemas.response.recommended_recipes_reponse import (
    PopularRecipesResponse,
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
    "/recipe-scraper/create-recipe",
    tags=["recipe", "recipe-scraper"],
    summary="Create recipe from URL",
    description="Creates a recipe from the given URL and adds it to the database.",
    response_class=JSONResponse,
)
def create_recipe(
    service: Annotated[RecipeScraperService, Depends(get_recipe_scraper_service)],
    url: Annotated[str, Query(..., description="URL to extract a recipe from.")],
) -> JSONResponse:
    """Endpoint to extract a recipe from a given URL.

    Args:
        service (RecipeScraperService): RecipeScraperService dependency for processing
            the recipe.
        url (str): URL pointing to the recipe for creation.

    Returns:
        JSONResponse: Response containing the created recipe data.
    """
    # TODO(jsamuelsen): Change return type back to CreateRecipeResponse after testing.
    return service.create_recipe(url)


@router.get(
    "/recipe-scraper/popular-recipes",
    tags=["recipe", "recipe-scraper"],
    summary="Get popular recipes from internet",
    description="Returns a list of URLs pointing to popular recipes from around the \
      internet.",
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
