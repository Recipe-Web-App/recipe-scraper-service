"""Recipe endpoints.

Provides:
- POST /recipes for scraping a recipe URL and saving to the Recipe Management Service
- GET /recipes/popular for fetching popular recipes from aggregated sources
- GET /recipes/{recipeId}/nutritional-info for fetching nutritional data for a recipe
"""

from __future__ import annotations

from typing import Annotated, Any

import orjson
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from starlette.responses import JSONResponse, Response

from app.api.dependencies import (
    get_allergen_service,
    get_ingredient_parser,
    get_nutrition_service,
    get_pairings_service,
    get_recipe_management_client,
    get_redis_cache_client,
    get_scraper_service,
    get_shopping_service,
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
from app.schemas.allergen import RecipeAllergenResponse
from app.schemas.enums import IngredientUnit
from app.schemas.ingredient import Ingredient, Quantity, WebRecipe
from app.schemas.nutrition import (
    IngredientNutritionalInfoResponse,
    RecipeNutritionalInfoResponse,
)
from app.schemas.recipe import PopularRecipesData
from app.schemas.recommendations import PairingSuggestionsResponse
from app.schemas.shopping import RecipeShoppingInfoResponse
from app.services.allergen.service import AllergenService  # noqa: TC001
from app.services.nutrition.service import NutritionService  # noqa: TC001
from app.services.pairings.exceptions import LLMGenerationError as PairingsLLMError
from app.services.pairings.service import PairingsService, RecipeContext
from app.services.recipe_management.client import RecipeManagementClient  # noqa: TC001
from app.services.recipe_management.exceptions import (
    RecipeManagementError,
    RecipeManagementNotFoundError,
    RecipeManagementUnavailableError,
    RecipeManagementValidationError,
)
from app.services.recipe_management.schemas import (
    IngredientUnit as RecipeIngredientUnit,  # noqa: TC001
)
from app.services.scraping.exceptions import (
    RecipeNotFoundError,
    ScrapingError,
    ScrapingFetchError,
    ScrapingTimeoutError,
)
from app.services.scraping.service import RecipeScraperService  # noqa: TC001
from app.services.shopping.service import ShoppingService  # noqa: TC001
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


@router.get(
    "/recipes/{recipeId}/nutritional-info",
    response_model=RecipeNutritionalInfoResponse,
    summary="Get nutritional info for a recipe",
    description=(
        "Returns comprehensive nutritional information for all ingredients "
        "in the recipe, with options to include total aggregated values and "
        "per-ingredient breakdowns."
    ),
    responses={
        200: {
            "description": "Nutritional information retrieved successfully",
        },
        206: {
            "description": "Partial content - some ingredient nutritional data unavailable",
            "headers": {
                "X-Partial-Content": {
                    "description": "Comma-separated list of missing ingredient IDs",
                    "schema": {"type": "string"},
                }
            },
        },
        400: {
            "description": "Invalid request parameters",
            "content": {
                "application/json": {
                    "example": {
                        "error": "BAD_REQUEST",
                        "message": (
                            "At least one of 'includeTotal' or 'includeIngredients' "
                            "must be true."
                        ),
                    }
                }
            },
        },
        404: {
            "description": "Resource not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": "NOT_FOUND",
                        "message": "Recipe with identifier '123' not found",
                    }
                }
            },
        },
        422: {"description": "Request validation error"},
    },
)
async def get_recipe_nutritional_info(
    recipe_id: Annotated[int, Path(alias="recipeId", ge=1)],
    user: Annotated[CurrentUser, Depends(RequirePermissions(Permission.RECIPE_READ))],
    recipe_client: Annotated[
        RecipeManagementClient, Depends(get_recipe_management_client)
    ],
    nutrition_service: Annotated[NutritionService, Depends(get_nutrition_service)],
    request: Request,
    include_total: Annotated[
        bool,
        Query(
            alias="includeTotal",
            description="Include aggregated nutritional totals",
        ),
    ] = True,
    include_ingredients: Annotated[
        bool,
        Query(
            alias="includeIngredients",
            description="Include per-ingredient nutritional breakdown",
        ),
    ] = False,
) -> Response:
    """Get nutritional information for a recipe.

    This endpoint fetches recipe details from the Recipe Management Service,
    then calculates nutritional information for all ingredients using the
    NutritionService. Supports filtering for totals only or per-ingredient
    breakdown.

    Args:
        recipe_id: ID of the recipe.
        user: Authenticated user with RECIPE_READ permission.
        recipe_client: Client for Recipe Management Service.
        nutrition_service: Service for nutritional calculations.
        request: The incoming HTTP request.
        include_total: Whether to include aggregated totals (default True).
        include_ingredients: Whether to include per-ingredient data (default False).

    Returns:
        RecipeNutritionalInfoResponse with nutritional data.
        Returns 206 with X-Partial-Content header if some ingredients missing.

    Raises:
        HTTPException: 400 if both flags are false.
        HTTPException: 404 if recipe not found.
        HTTPException: 503 if downstream service unavailable.
    """
    # Validate query parameters
    if not include_total and not include_ingredients:
        logger.warning(
            "Invalid query params: both flags false",
            recipe_id=recipe_id,
            user_id=user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "BAD_REQUEST",
                "message": (
                    "At least one of 'includeTotal' or 'includeIngredients' must be true."
                ),
            },
        )

    # Extract auth token for downstream call
    auth_header = request.headers.get("Authorization", "")
    auth_token = auth_header.replace("Bearer ", "") if auth_header else ""

    logger.info(
        "Fetching nutritional info for recipe",
        recipe_id=recipe_id,
        include_total=include_total,
        include_ingredients=include_ingredients,
        user_id=user.id,
    )

    # Step 1: Fetch recipe from Recipe Management Service
    try:
        recipe = await recipe_client.get_recipe(recipe_id, auth_token)
    except RecipeManagementNotFoundError:
        logger.info("Recipe not found", recipe_id=recipe_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "NOT_FOUND",
                "message": f"Recipe with identifier '{recipe_id}' not found",
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

    # Step 2: Handle empty recipe (no ingredients)
    if not recipe.ingredients:
        logger.info("Recipe has no ingredients", recipe_id=recipe_id)
        response_data = RecipeNutritionalInfoResponse(
            ingredients=None,
            missing_ingredients=None,
            total=IngredientNutritionalInfoResponse(
                quantity=Quantity(amount=0, measurement=IngredientUnit.G),
                macro_nutrients=None,
                vitamins=None,
                minerals=None,
            )
            if include_total
            else None,
        )
        return JSONResponse(
            content=orjson.loads(
                orjson.dumps(response_data.model_dump(by_alias=True, exclude_none=True))
            ),
            status_code=status.HTTP_200_OK,
        )

    # Step 3: Transform recipe ingredients to Ingredient schema for NutritionService
    ingredients: list[Ingredient] = [
        Ingredient(
            ingredient_id=ing.ingredient_id or ing.id,
            name=ing.ingredient_name,
            quantity=Quantity(
                amount=ing.quantity,
                measurement=_map_ingredient_unit(ing.unit),
            ),
        )
        for ing in recipe.ingredients
    ]

    # Step 4: Get nutritional data from NutritionService
    nutrition_result = await nutrition_service.get_recipe_nutrition(ingredients)

    # Step 5: Apply include flags to filter response
    response_data = RecipeNutritionalInfoResponse(
        ingredients=nutrition_result.ingredients if include_ingredients else None,
        missing_ingredients=nutrition_result.missing_ingredients,
        total=nutrition_result.total if include_total else None,
    )

    # Step 6: Determine status code and headers
    response_content = orjson.loads(
        orjson.dumps(response_data.model_dump(by_alias=True, exclude_none=True))
    )

    if nutrition_result.missing_ingredients:
        # Some ingredients missing - return 206 Partial Content
        missing_ids = ",".join(
            str(ing_id) for ing_id in nutrition_result.missing_ingredients
        )
        logger.info(
            "Returning partial nutritional info",
            recipe_id=recipe_id,
            missing_count=len(nutrition_result.missing_ingredients),
            missing_ids=missing_ids,
        )
        return JSONResponse(
            content=response_content,
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            headers={"X-Partial-Content": missing_ids},
        )

    logger.info(
        "Returning complete nutritional info",
        recipe_id=recipe_id,
        ingredient_count=len(recipe.ingredients),
    )
    return JSONResponse(
        content=response_content,
        status_code=status.HTTP_200_OK,
    )


def _map_ingredient_unit(unit: RecipeIngredientUnit) -> IngredientUnit:
    """Map Recipe Management unit to schema IngredientUnit.

    The Recipe Management Service uses its own IngredientUnit enum,
    which needs to be mapped to the schema's IngredientUnit.

    Args:
        unit: Unit from Recipe Management Service.

    Returns:
        Corresponding schema IngredientUnit.
    """
    # Both enums use the same values, so direct mapping works
    return IngredientUnit(unit.value)


@router.get(
    "/recipes/{recipeId}/allergens",
    response_model=RecipeAllergenResponse,
    summary="Get allergen information for a recipe",
    description=(
        "Returns allergen information for all ingredients in a recipe. "
        "Aggregates contains and may-contain allergens across all ingredients. "
        "Optionally includes per-ingredient allergen breakdown."
    ),
    responses={
        200: {
            "description": "Allergen information retrieved successfully",
        },
        206: {
            "description": "Partial content - some ingredient allergen data unavailable",
            "headers": {
                "X-Partial-Content": {
                    "description": "Comma-separated list of missing ingredient IDs",
                    "schema": {"type": "string"},
                }
            },
        },
        404: {
            "description": "Recipe not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": "NOT_FOUND",
                        "message": "Recipe with identifier '123' not found",
                    }
                }
            },
        },
        503: {
            "description": "Service unavailable",
        },
    },
)
async def get_recipe_allergens(
    recipe_id: Annotated[int, Path(alias="recipeId", ge=1)],
    user: Annotated[CurrentUser, Depends(RequirePermissions(Permission.RECIPE_READ))],
    recipe_client: Annotated[
        RecipeManagementClient, Depends(get_recipe_management_client)
    ],
    allergen_service: Annotated[AllergenService, Depends(get_allergen_service)],
    request: Request,
    include_ingredient_details: Annotated[
        bool,
        Query(
            alias="includeIngredientDetails",
            description="Include per-ingredient allergen breakdown",
        ),
    ] = False,
) -> Response:
    """Get allergen information for a recipe.

    This endpoint fetches recipe details from the Recipe Management Service,
    then retrieves allergen information for all ingredients using the
    AllergenService. Returns aggregated contains/may-contain lists.

    Args:
        recipe_id: ID of the recipe.
        user: Authenticated user with RECIPE_READ permission.
        recipe_client: Client for Recipe Management Service.
        allergen_service: Service for allergen lookups.
        request: The incoming HTTP request.
        include_ingredient_details: Whether to include per-ingredient breakdown.

    Returns:
        RecipeAllergenResponse with aggregated allergen data.
        Returns 206 with X-Partial-Content header if some ingredients missing.

    Raises:
        HTTPException: 404 if recipe not found.
        HTTPException: 503 if downstream service unavailable.
    """
    # Extract auth token for downstream call
    auth_header = request.headers.get("Authorization", "")
    auth_token = auth_header.replace("Bearer ", "") if auth_header else ""

    logger.info(
        "Fetching allergen info for recipe",
        recipe_id=recipe_id,
        include_ingredient_details=include_ingredient_details,
        user_id=user.id,
    )

    # Step 1: Fetch recipe from Recipe Management Service
    try:
        recipe = await recipe_client.get_recipe(recipe_id, auth_token)
    except RecipeManagementNotFoundError:
        logger.info("Recipe not found", recipe_id=recipe_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "NOT_FOUND",
                "message": f"Recipe with identifier '{recipe_id}' not found",
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

    # Step 2: Handle empty recipe (no ingredients)
    if not recipe.ingredients:
        logger.info("Recipe has no ingredients", recipe_id=recipe_id)
        response_data = RecipeAllergenResponse()
        return JSONResponse(
            content=orjson.loads(
                orjson.dumps(response_data.model_dump(by_alias=True, exclude_none=True))
            ),
            status_code=status.HTTP_200_OK,
        )

    # Step 3: Transform recipe ingredients to Ingredient schema
    ingredients: list[Ingredient] = [
        Ingredient(
            ingredient_id=ing.ingredient_id or ing.id,
            name=ing.ingredient_name,
        )
        for ing in recipe.ingredients
    ]

    # Step 4: Get allergen data from AllergenService
    allergen_result = await allergen_service.get_recipe_allergens(
        ingredients,
        include_details=include_ingredient_details,
    )

    # Step 5: Build response and determine status code
    response_content = orjson.loads(
        orjson.dumps(allergen_result.model_dump(by_alias=True, exclude_none=True))
    )

    if allergen_result.missing_ingredients:
        # Some ingredients missing - return 206 Partial Content
        missing_ids = ",".join(
            str(ing_id) for ing_id in allergen_result.missing_ingredients
        )
        logger.info(
            "Returning partial allergen info",
            recipe_id=recipe_id,
            missing_count=len(allergen_result.missing_ingredients),
            missing_ids=missing_ids,
        )
        return JSONResponse(
            content=response_content,
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            headers={"X-Partial-Content": missing_ids},
        )

    logger.info(
        "Returning complete allergen info",
        recipe_id=recipe_id,
        ingredient_count=len(recipe.ingredients),
        contains_count=len(allergen_result.contains),
        may_contain_count=len(allergen_result.may_contain),
    )
    return JSONResponse(
        content=response_content,
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/recipes/{recipeId}/shopping-info",
    response_model=RecipeShoppingInfoResponse,
    summary="Get shopping information for a recipe",
    description=(
        "Retrieves comprehensive shopping information for all ingredients "
        "in a recipe, including individual ingredient prices and total estimated "
        "cost for grocery shopping."
    ),
    responses={
        200: {
            "description": "Shopping information retrieved successfully",
        },
        206: {
            "description": "Partial content - some ingredient prices unavailable",
            "headers": {
                "X-Partial-Content": {
                    "description": "Comma-separated list of ingredient IDs with missing prices",
                    "schema": {"type": "string"},
                }
            },
        },
        404: {
            "description": "Resource not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": "NOT_FOUND",
                        "message": "Recipe with identifier '123' not found",
                    }
                }
            },
        },
    },
)
async def get_recipe_shopping_info(
    recipe_id: Annotated[int, Path(alias="recipeId", ge=1)],
    user: Annotated[CurrentUser, Depends(RequirePermissions(Permission.RECIPE_READ))],
    recipe_client: Annotated[
        RecipeManagementClient, Depends(get_recipe_management_client)
    ],
    shopping_service: Annotated[ShoppingService, Depends(get_shopping_service)],
    request: Request,
) -> Response:
    """Get shopping information for a recipe.

    This endpoint fetches recipe details from the Recipe Management Service,
    then calculates pricing information for all ingredients using the
    ShoppingService. Returns per-ingredient breakdown and total estimated cost.

    Args:
        recipe_id: ID of the recipe.
        user: Authenticated user with RECIPE_READ permission.
        recipe_client: Client for Recipe Management Service.
        shopping_service: Service for shopping/pricing calculations.
        request: The incoming HTTP request.

    Returns:
        RecipeShoppingInfoResponse with pricing data.
        Returns 206 with X-Partial-Content header if some ingredients missing prices.

    Raises:
        HTTPException: 404 if recipe not found.
        HTTPException: 503 if downstream service unavailable.
    """
    # Extract auth token for downstream call
    auth_header = request.headers.get("Authorization", "")
    auth_token = auth_header.replace("Bearer ", "") if auth_header else ""

    logger.info(
        "Fetching shopping info for recipe",
        recipe_id=recipe_id,
        user_id=user.id,
    )

    # Step 1: Fetch recipe from Recipe Management Service
    try:
        recipe = await recipe_client.get_recipe(recipe_id, auth_token)
    except RecipeManagementNotFoundError:
        logger.info("Recipe not found", recipe_id=recipe_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "NOT_FOUND",
                "message": f"Recipe with identifier '{recipe_id}' not found",
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

    # Step 2: Handle empty recipe (no ingredients)
    if not recipe.ingredients:
        logger.info("Recipe has no ingredients", recipe_id=recipe_id)
        response_data = RecipeShoppingInfoResponse(
            recipe_id=recipe_id,
            ingredients={},
            total_estimated_cost="0.00",
        )
        return JSONResponse(
            content=orjson.loads(
                orjson.dumps(response_data.model_dump(by_alias=True, exclude_none=True))
            ),
            status_code=status.HTTP_200_OK,
        )

    # Step 3: Transform recipe ingredients to Ingredient schema
    ingredients: list[Ingredient] = [
        Ingredient(
            ingredient_id=ing.ingredient_id or ing.id,
            name=ing.ingredient_name,
            quantity=Quantity(
                amount=ing.quantity,
                measurement=_map_ingredient_unit(ing.unit),
            ),
        )
        for ing in recipe.ingredients
    ]

    # Step 4: Get shopping data from ShoppingService
    shopping_result = await shopping_service.get_recipe_shopping_info(
        recipe_id=recipe_id,
        ingredients=ingredients,
    )

    # Step 5: Build response and determine status code
    response_content = orjson.loads(
        orjson.dumps(shopping_result.model_dump(by_alias=True, exclude_none=True))
    )

    if shopping_result.missing_ingredients:
        # Some ingredients missing prices - return 206 Partial Content
        missing_ids = ",".join(
            str(ing_id) for ing_id in shopping_result.missing_ingredients
        )
        logger.info(
            "Returning partial shopping info",
            recipe_id=recipe_id,
            missing_count=len(shopping_result.missing_ingredients),
            missing_ids=missing_ids,
        )
        return JSONResponse(
            content=response_content,
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            headers={"X-Partial-Content": missing_ids},
        )

    logger.info(
        "Returning complete shopping info",
        recipe_id=recipe_id,
        ingredient_count=len(recipe.ingredients),
        total_cost=shopping_result.total_estimated_cost,
    )
    return JSONResponse(
        content=response_content,
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/recipes/{recipeId}/pairings",
    response_model=PairingSuggestionsResponse,
    summary="Get recipe pairing suggestions",
    description=(
        "Returns AI-powered recipe pairing suggestions based on flavor profiles, "
        "cuisine types, and ingredient compatibility. Suggests complementary dishes "
        "including sides, appetizers, desserts, and beverages."
    ),
    responses={
        200: {
            "description": "Pairing suggestions retrieved successfully",
        },
        404: {
            "description": "Recipe not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": "NOT_FOUND",
                        "message": "Recipe with identifier '123' not found",
                    }
                }
            },
        },
        503: {
            "description": "Service unavailable (LLM unavailable)",
            "content": {
                "application/json": {
                    "example": {
                        "error": "LLM_UNAVAILABLE",
                        "message": "Pairings service temporarily unavailable",
                    }
                }
            },
        },
    },
)
async def get_recipe_pairings(
    recipe_id: Annotated[int, Path(alias="recipeId", ge=1)],
    user: Annotated[CurrentUser, Depends(RequirePermissions(Permission.RECIPE_READ))],
    recipe_client: Annotated[
        RecipeManagementClient, Depends(get_recipe_management_client)
    ],
    pairings_service: Annotated[PairingsService, Depends(get_pairings_service)],
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    count_only: Annotated[bool, Query(alias="countOnly")] = False,
) -> PairingSuggestionsResponse:
    """Get pairing suggestions for a recipe.

    This endpoint fetches recipe details from the Recipe Management Service,
    then generates AI-powered pairing suggestions based on flavor profiles,
    cuisine types, and ingredient compatibility.

    Args:
        recipe_id: ID of the recipe.
        user: Authenticated user with RECIPE_READ permission.
        recipe_client: Client for Recipe Management Service.
        pairings_service: Service for generating pairing suggestions.
        request: The incoming HTTP request.
        limit: Maximum number of pairings to return (1-100).
        offset: Starting index for pagination.
        count_only: If True, return only count without pairing data.

    Returns:
        PairingSuggestionsResponse with pairing recommendations.

    Raises:
        HTTPException: 404 if recipe not found.
        HTTPException: 503 if pairings service unavailable.
    """
    # Extract auth token for downstream call
    auth_header = request.headers.get("Authorization", "")
    auth_token = auth_header.replace("Bearer ", "") if auth_header else ""

    logger.info(
        "Fetching pairing suggestions for recipe",
        recipe_id=recipe_id,
        limit=limit,
        offset=offset,
        count_only=count_only,
        user_id=user.id,
    )

    # Step 1: Fetch recipe from Recipe Management Service
    try:
        recipe = await recipe_client.get_recipe(recipe_id, auth_token)
    except RecipeManagementNotFoundError:
        logger.info("Recipe not found", recipe_id=recipe_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "NOT_FOUND",
                "message": f"Recipe with identifier '{recipe_id}' not found",
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

    # Step 2: Build recipe context for pairings service
    context = RecipeContext(
        recipe_id=recipe_id,
        title=recipe.title,
        description=recipe.description,
        ingredients=[ing.ingredient_name for ing in recipe.ingredients],
    )

    # Step 3: Get pairings from service
    try:
        result = await pairings_service.get_pairings(
            context=context,
            limit=limit,
            offset=offset,
        )
    except PairingsLLMError:
        logger.warning("LLM unavailable for pairing generation", recipe_id=recipe_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "LLM_UNAVAILABLE",
                "message": "Pairings service temporarily unavailable",
            },
        ) from None

    # Handle None result (service not initialized)
    if result is None:
        logger.warning("Pairings service returned None", recipe_id=recipe_id)
        return PairingSuggestionsResponse(
            recipe_id=recipe_id,
            pairing_suggestions=[],
            limit=limit,
            offset=offset,
            count=0,
        )

    # Step 4: Apply countOnly filter
    if count_only:
        result.pairing_suggestions = []

    logger.info(
        "Returning pairing suggestions",
        recipe_id=recipe_id,
        count=result.count,
        returned_count=len(result.pairing_suggestions),
    )

    return result
