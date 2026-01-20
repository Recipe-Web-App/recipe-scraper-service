"""Recipe creation endpoint.

Provides POST /recipes for scraping a recipe URL and saving to
the Recipe Management Service.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import (
    get_ingredient_parser,
    get_recipe_management_client,
    get_scraper_service,
)
from app.auth.dependencies import CurrentUser, RequirePermissions
from app.auth.permissions import Permission
from app.mappers import build_downstream_recipe_request, build_recipe_response
from app.observability.logging import get_logger
from app.parsing.exceptions import IngredientParsingError
from app.parsing.ingredient import IngredientParser  # noqa: TC001
from app.schemas import CreateRecipeRequest, CreateRecipeResponse
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
