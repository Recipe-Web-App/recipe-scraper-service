"""Recipe creation endpoint.

Provides POST /recipes for scraping a recipe URL and saving to
the Recipe Management Service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import (
    get_ingredient_parser,
    get_recipe_management_client,
    get_scraper_service,
)
from app.auth.dependencies import CurrentUser, RequirePermissions
from app.auth.permissions import Permission
from app.llm.prompts import IngredientUnit as ParsedIngredientUnit  # noqa: TC001
from app.observability.logging import get_logger
from app.parsing.exceptions import IngredientParsingError
from app.parsing.ingredient import IngredientParser  # noqa: TC001
from app.schemas import (
    CreateRecipeRequest,
    CreateRecipeResponse,
    Ingredient,
    Recipe,
    RecipeStep,
)

# These imports are needed at runtime for FastAPI dependency injection type resolution
from app.services.recipe_management import (
    CreateRecipeIngredientRequest,
    CreateRecipeStepRequest,
    IngredientUnit,
    RecipeResponse,
)
from app.services.recipe_management import (
    CreateRecipeRequest as DownstreamRecipeRequest,
)
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


if TYPE_CHECKING:
    from app.llm.prompts import ParsedIngredient
    from app.services.scraping.models import ScrapedRecipe


logger = get_logger(__name__)

router = APIRouter(tags=["Recipes"])


# --- Helper Functions ---


def _map_unit(unit: ParsedIngredientUnit) -> IngredientUnit:
    """Map parsed ingredient unit to downstream service unit.

    Args:
        unit: Unit from LLM parsing.

    Returns:
        Corresponding IngredientUnit for downstream service.
    """
    # Direct mapping since both enums have the same values
    return IngredientUnit(unit.value)


def _build_downstream_request(
    scraped: ScrapedRecipe,
    parsed_ingredients: list[ParsedIngredient],
) -> DownstreamRecipeRequest:
    """Build downstream recipe request from scraped and parsed data.

    Args:
        scraped: Raw scraped recipe data.
        parsed_ingredients: LLM-parsed ingredients.

    Returns:
        Request schema for downstream Recipe Management Service.
    """
    # Build ingredients list (using aliases for Pydantic model construction)
    ingredients = [
        CreateRecipeIngredientRequest.model_validate(
            {
                "ingredientName": ing.name,
                "quantity": ing.quantity,
                "unit": _map_unit(ing.unit),
                "isOptional": ing.is_optional,
                "notes": ing.notes,
            }
        )
        for ing in parsed_ingredients
    ]

    # Build steps list
    steps = [
        CreateRecipeStepRequest.model_validate(
            {
                "stepNumber": idx + 1,
                "instruction": instruction,
            }
        )
        for idx, instruction in enumerate(scraped.instructions)
    ]

    # Parse servings (default to 1 if not available)
    servings = scraped.parse_servings() or 1.0

    return DownstreamRecipeRequest.model_validate(
        {
            "title": scraped.title,
            "description": scraped.description or "",
            "servings": servings,
            "preparationTime": scraped.prep_time,
            "cookingTime": scraped.cook_time,
            "ingredients": ingredients,
            "steps": steps,
        }
    )


def _build_response(
    downstream_response: RecipeResponse,
    scraped: ScrapedRecipe,
    parsed_ingredients: list[ParsedIngredient],
) -> CreateRecipeResponse:
    """Build endpoint response from downstream response and parsed data.

    Args:
        downstream_response: Response from Recipe Management Service.
        scraped: Original scraped recipe data.
        parsed_ingredients: Parsed ingredients.

    Returns:
        CreateRecipeResponse for the client.
    """
    # Build ingredient list for response (using model_validate for aliases)
    ingredients = [
        Ingredient.model_validate(
            {
                "name": ing.name,
                "quantity": {
                    "amount": ing.quantity,
                    "measurement": ing.unit.value,
                },
            }
        )
        for ing in parsed_ingredients
    ]

    # Build steps for response
    steps = [
        RecipeStep.model_validate(
            {
                "stepNumber": idx + 1,
                "instruction": instruction,
            }
        )
        for idx, instruction in enumerate(scraped.instructions)
    ]

    recipe = Recipe.model_validate(
        {
            "recipeId": downstream_response.id,
            "title": downstream_response.title,
            "description": scraped.description,
            "originUrl": scraped.source_url,
            "servings": scraped.parse_servings(),
            "preparationTime": scraped.prep_time,
            "cookingTime": scraped.cook_time,
            "ingredients": ingredients,
            "steps": steps,
        }
    )

    return CreateRecipeResponse(recipe=recipe)


# --- Endpoint ---


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
    downstream_request = _build_downstream_request(scraped, parsed_ingredients)

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

    return _build_response(downstream_response, scraped, parsed_ingredients)
