"""Recipe endpoints.

Provides:
- POST /recipes for scraping a recipe URL and saving to the Recipe Management Service
- GET /recipes/popular for fetching popular recipes from aggregated sources
"""

from __future__ import annotations

from typing import Annotated, Any

import orjson
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from starlette.responses import JSONResponse

from app.api.dependencies import (
    get_ingredient_parser,
    get_recipe_management_client,
    get_redis_cache_client,
    get_scraper_service,
)
from app.auth.dependencies import CurrentUser, RequirePermissions
from app.auth.permissions import Permission
from app.core.config import get_settings
from app.mappers import build_downstream_recipe_request, build_recipe_response
from app.observability.logging import get_logger
from app.parsing.exceptions import IngredientParsingError
from app.parsing.ingredient import IngredientParser  # noqa: TC001
from app.schemas import (
    CreateRecipeRequest,
    CreateRecipeResponse,
    PopularRecipesResponse,
)
from app.schemas.ingredient import WebRecipe
from app.schemas.recipe import PopularRecipesData
from app.services.recipe_management.client import RecipeManagementClient  # noqa: TC001
from app.services.recipe_management.exceptions import (
    RecipeManagementError,
    RecipeManagementUnavailableError,
    RecipeManagementValidationError,
)
from app.services.scraping.exceptions import (
    RecipeNotFoundError,
    ScrapingError,
    ScrapingFetchError,
    ScrapingTimeoutError,
)
from app.services.scraping.service import RecipeScraperService  # noqa: TC001
from app.workers.jobs import enqueue_popular_recipes_refresh


logger = get_logger(__name__)

router = APIRouter(tags=["Recipes"])


@router.post(
    "/recipes",
    response_model=CreateRecipeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a recipe from a URL",
    description=(
        "Scrapes recipe data from a provided URL and stores it in the database. "
        "Supports most popular recipe websites via recipe-scrapers library and "
        "JSON-LD structured data as a fallback."
    ),
    responses={
        400: {
            "description": "Invalid URL or unsupported website",
            "content": {
                "application/json": {
                    "example": {
                        "error": "INVALID_RECIPE_URL",
                        "message": "Unable to scrape recipe from the provided URL",
                    }
                }
            },
        },
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        422: {"description": "Request validation error"},
        503: {"description": "Service unavailable"},
    },
)
async def create_recipe(
    request_body: CreateRecipeRequest,
    user: Annotated[CurrentUser, Depends(RequirePermissions(Permission.RECIPE_CREATE))],
    scraper_service: Annotated[RecipeScraperService, Depends(get_scraper_service)],
    recipe_client: Annotated[
        RecipeManagementClient, Depends(get_recipe_management_client)
    ],
    parser: Annotated[IngredientParser, Depends(get_ingredient_parser)],
    request: Request,
) -> CreateRecipeResponse:
    """Create a recipe by scraping a URL.

    This endpoint:
    1. Scrapes recipe data from the provided URL
    2. Normalizes ingredients using LLM
    3. Saves the recipe to the Recipe Management Service
    4. Returns the created recipe

    Args:
        request_body: Request containing the recipe URL.
        user: Authenticated user with RECIPE_CREATE permission.
        scraper_service: Service for scraping recipes.
        recipe_client: Client for downstream Recipe Management Service.
        parser: Service for parsing ingredients.
        request: The incoming HTTP request.

    Returns:
        Created recipe response.

    Raises:
        HTTPException: Various status codes depending on the error.
    """
    url = str(request_body.recipe_url)

    logger.info(
        "Creating recipe from URL",
        url=url,
        user_id=user.id,
    )

    # Step 1: Scrape the recipe
    try:
        scraped = await scraper_service.scrape(url)
    except RecipeNotFoundError:
        logger.warning("No recipe found at URL", url=url)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "RECIPE_NOT_FOUND",
                "message": "No recipe data found at the provided URL",
            },
        ) from None
    except ScrapingTimeoutError:
        logger.warning("Scraping timed out", url=url)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "error": "SCRAPING_TIMEOUT",
                "message": "Timed out while fetching the recipe URL",
            },
        ) from None
    except ScrapingFetchError as e:
        logger.warning("Failed to fetch URL", url=url, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_RECIPE_URL",
                "message": f"Unable to fetch the recipe URL: {e}",
            },
        ) from None
    except ScrapingError as e:
        logger.warning("Scraping failed", url=url, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "SCRAPING_ERROR",
                "message": f"Failed to scrape recipe: {e}",
            },
        ) from None

    # Step 2: Parse ingredients with LLM
    try:
        parsed_ingredients = await parser.parse_batch(scraped.ingredients)
    except IngredientParsingError as e:
        logger.warning("Ingredient parsing failed", url=url, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INGREDIENT_PARSING_ERROR",
                "message": "Failed to parse recipe ingredients",
            },
        ) from None

    # Step 3: Build downstream request and send to Recipe Management Service
    downstream_request = build_downstream_recipe_request(scraped, parsed_ingredients)

    # Extract auth token from request for forwarding
    auth_header = request.headers.get("Authorization", "")
    auth_token = auth_header.replace("Bearer ", "") if auth_header else ""

    try:
        downstream_response = await recipe_client.create_recipe(
            downstream_request,
            auth_token,
        )
    except RecipeManagementValidationError as e:
        logger.warning("Downstream validation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "VALIDATION_ERROR",
                "message": str(e),
            },
        ) from None
    except RecipeManagementUnavailableError:
        logger.warning("Recipe Management Service unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "SERVICE_UNAVAILABLE",
                "message": "Recipe Management Service is not available",
            },
        ) from None
    except RecipeManagementError as e:
        logger.exception("Recipe Management Service error")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "DOWNSTREAM_ERROR",
                "message": f"Recipe Management Service error: {e}",
            },
        ) from None

    # Step 4: Build and return response
    logger.info(
        "Recipe created successfully",
        recipe_id=downstream_response.id,
        title=downstream_response.title,
        url=url,
        user_id=user.id,
    )

    return build_recipe_response(downstream_response, scraped, parsed_ingredients)


@router.get(
    "/recipes/popular",
    response_model=PopularRecipesResponse,
    summary="Get popular recipes from the internet",
    description=(
        "Returns a paginated list of popular recipes aggregated from multiple "
        "curated sources. Recipes are ranked by a normalized popularity score "
        "based on ratings, reviews, and engagement metrics. Results are cached "
        "and refreshed periodically by a background worker."
    ),
    responses={
        503: {
            "description": "Popular recipes cache is being refreshed",
            "headers": {
                "Retry-After": {
                    "description": "Suggested wait time in seconds before retrying",
                    "schema": {"type": "integer"},
                }
            },
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Popular recipes are being refreshed. Please retry shortly."
                    }
                }
            },
        },
    },
)
async def get_popular_recipes(
    cache_client: Annotated[Any, Depends(get_redis_cache_client)],
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Maximum number of recipes to return",
        ),
    ] = 50,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description="Starting index for pagination",
        ),
    ] = 0,
    count_only: Annotated[
        bool,
        Query(
            alias="countOnly",
            description="If true, returns only the count without recipe data",
        ),
    ] = False,
) -> PopularRecipesResponse | JSONResponse:
    """Get popular recipes from cache.

    This endpoint returns cached popular recipes. If the cache is empty,
    it returns 503 and triggers a background refresh job.

    The cache is proactively refreshed by a cron job before it expires,
    so cache misses should be rare (only on cold start or cache failure).

    Args:
        cache_client: Redis cache client.
        limit: Maximum number of recipes to return (1-100).
        offset: Starting index for pagination.
        count_only: If True, return only count without recipe data.

    Returns:
        Paginated list of popular recipes, or 503 if cache is cold.
    """
    settings = get_settings()
    config = settings.scraping.popular_recipes
    cache_key = f"popular:{config.cache_key}"

    logger.debug(
        "Fetching popular recipes from cache",
        limit=limit,
        offset=offset,
        count_only=count_only,
    )

    # Try to get from cache
    if cache_client:
        try:
            cached_bytes = await cache_client.get(cache_key)
            if cached_bytes:
                data = PopularRecipesData.model_validate(orjson.loads(cached_bytes))
                recipes = data.recipes

                # Apply pagination
                paginated_recipes = recipes[offset : offset + limit]

                # Convert PopularRecipe to WebRecipe for response
                web_recipes = (
                    []
                    if count_only
                    else [
                        WebRecipe(recipe_name=r.recipe_name, url=r.url)
                        for r in paginated_recipes
                    ]
                )

                logger.debug(
                    "Returning cached popular recipes",
                    total_count=data.total_count,
                    returned_count=len(web_recipes),
                )

                return PopularRecipesResponse(
                    recipes=web_recipes,
                    limit=limit,
                    offset=offset,
                    count=data.total_count,
                )
        except Exception:
            logger.exception("Error reading popular recipes from cache")

    # Cache miss - enqueue background refresh and return 503
    logger.info("Popular recipes cache miss, enqueueing refresh job")
    await enqueue_popular_recipes_refresh()

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": "Popular recipes are being refreshed. Please retry shortly."
        },
        headers={"Retry-After": "60"},
    )
