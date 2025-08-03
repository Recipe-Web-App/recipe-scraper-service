"""Recipe-related route handlers.

Provides API endpoints for handling recipes, such as parsing from the web & providing
popular links.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query
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
from app.utils.validators import validate_pagination_params

__log = get_logger("RecipeScraperRoutes")

# Singleton instance to maintain cache across requests
_service_instance: RecipeScraperService | None = None


def get_recipe_scraper_service() -> RecipeScraperService:
    """Dependency provider function to get RecipeScraperService instance.

    Uses a singleton pattern to maintain cache across requests.

    Returns:     RecipeScraperService: The service instance.
    """
    global _service_instance  # noqa: PLW0603
    if _service_instance is None:
        _service_instance = RecipeScraperService()
    return _service_instance


router = APIRouter()


@router.post(
    "/recipe-scraper/create-recipe",
    tags=["recipe", "recipe-scraper"],
    summary="Create a recipe from a URL",
    description="""
                Scrapes recipe data from a provided URL and stores it in the database.

                This endpoint supports most popular recipe websites and will extract: -
                Recipe title and description - Ingredients list with quantities and
                units - Cooking instructions - Nutritional information (when available)
                - Images and metadata
                """,
    response_class=JSONResponse,
    responses={
        200: {
            "description": "Recipe successfully created",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "title": "Classic Chocolate Chip Cookies",
                        "description": "Soft and chewy chocolate chip cookies",
                        "url": "https://example.com/recipe/chocolate-chip-cookies",
                        "created_at": "2025-01-31T12:00:00Z",
                        "status": "success",
                    }
                }
            },
        },
        400: {
            "description": "Invalid URL or unsupported website",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Unable to scrape recipe from the provided URL",
                        "error_code": "INVALID_RECIPE_URL",
                    }
                }
            },
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "recipe_url"],
                                "msg": "field required",
                                "type": "value_error.missing",
                            }
                        ]
                    }
                }
            },
        },
    },
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "example": {
                        "recipe_url": "https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/"
                    }
                }
            }
        }
    },
)
def create_recipe(
    service: Annotated[RecipeScraperService, Depends(get_recipe_scraper_service)],
    db: Annotated[Session, Depends(get_db)],
    request: CreateRecipeRequest,
    user_id: Annotated[UUID, Header(..., alias="X-User-ID")],
) -> CreateRecipeResponse:
    """Endpoint to create a recipe from a given URL and add it to the database.

    Args:     service (RecipeScraperService): Service for recipe scraping logic.     db
    (Session): Database session dependency.     request (CreateRecipeRequest): Request
    body containing the recipe URL.     user_id (UUID): The unique identifier of the
    user making the request.

    Returns:     CreateRecipeResponse: The created recipe response.
    """
    return service.create_recipe(request.recipe_url, db, user_id)


@router.get(
    "/recipe-scraper/popular-recipes",
    tags=["recipe", "recipe-scraper"],
    summary="Get popular recipes from the internet",
    description="""
                Retrieves a curated list of popular recipe URLs from various cooking
                websites.

                This endpoint aggregates trending and popular recipes from major cooking
                platforms and returns them in a paginated format. Results can be
                filtered and sorted.

                The service maintains a cache of popular recipes that is updated
                periodically to ensure fresh content while maintaining good performance.
                """,
    response_class=JSONResponse,
    responses={
        200: {
            "description": "Popular recipes retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "recipes": [
                            {
                                "url": "https://www.allrecipes.com/recipe/231506/simple-macaroni-and-cheese/",
                                "title": "Simple Macaroni and Cheese",
                                "source": "allrecipes.com",
                                "estimated_prep_time": "15 minutes",
                                "difficulty": "easy",
                            },
                            {
                                "url": "https://www.foodnetwork.com/recipes/alton-brown/baked-macaroni-and-cheese-recipe-1939524",
                                "title": "Baked Macaroni and Cheese",
                                "source": "foodnetwork.com",
                                "estimated_prep_time": "45 minutes",
                                "difficulty": "medium",
                            },
                        ],
                        "total_count": 150,
                        "page_info": {"limit": 50, "offset": 0, "has_next": True},
                    }
                }
            },
        }
    },
)
async def get_popular_recipes(
    service: Annotated[RecipeScraperService, Depends(get_recipe_scraper_service)],
    limit: Annotated[int, Query(ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    count_only: Annotated[bool, Query()] = False,
) -> PopularRecipesResponse:
    """Endpoint to extract popular recipes from the internet.

    Args:     service (RecipeScraperService):         RecipeScraperService dependency
    for processing the recipe.     limit (int): Number of items per page (minimum 1).
    offset (int): Number of items to skip (minimum 0).     count_only (bool): Whether to
    return only count instead of recipes.

    Returns:     PopularRecipesResponse: A list of all gathered recipe data.
    """
    pagination = PaginationParams(
        limit=limit,
        offset=offset,
        count_only=count_only,
    )
    validate_pagination_params(pagination)

    return await service.get_popular_recipes(pagination)
