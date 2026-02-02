"""FastAPI dependencies for service access.

This module provides reusable dependencies for accessing application services
in FastAPI route handlers. Services are initialized during application startup
and stored in app.state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, status

from app.cache.redis import get_cache_client
from app.core.events.lifespan import get_llm_client
from app.parsing.ingredient import IngredientParser


if TYPE_CHECKING:
    from redis.asyncio import Redis

    from app.services.allergen.service import AllergenService
    from app.services.nutrition.service import NutritionService
    from app.services.popular.service import PopularRecipesService
    from app.services.recipe_management.client import RecipeManagementClient
    from app.services.scraping.service import RecipeScraperService
    from app.services.shopping.service import ShoppingService


async def get_scraper_service(request: Request) -> RecipeScraperService:
    """Get the recipe scraper service from app state.

    Args:
        request: The incoming request.

    Returns:
        Initialized RecipeScraperService.

    Raises:
        HTTPException: 503 if service is not initialized.
    """
    service: RecipeScraperService | None = getattr(
        request.app.state, "scraper_service", None
    )
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recipe scraper service not available",
        )
    return service


async def get_recipe_management_client(request: Request) -> RecipeManagementClient:
    """Get the recipe management client from app state.

    Args:
        request: The incoming request.

    Returns:
        Initialized RecipeManagementClient.

    Raises:
        HTTPException: 503 if client is not initialized.
    """
    client: RecipeManagementClient | None = getattr(
        request.app.state, "recipe_management_client", None
    )
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recipe management service not available",
        )
    return client


async def get_ingredient_parser() -> IngredientParser:
    """Get the ingredient parser with LLM client.

    Returns:
        IngredientParser instance.

    Raises:
        HTTPException: 503 if LLM client is not available.
    """
    try:
        llm_client = get_llm_client()
        return IngredientParser(llm_client)
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ingredient parsing service not available",
        ) from None


async def get_popular_recipes_service(request: Request) -> PopularRecipesService:
    """Get the popular recipes service from app state.

    Args:
        request: The incoming request.

    Returns:
        Initialized PopularRecipesService.

    Raises:
        HTTPException: 503 if service is not initialized.
    """
    service: PopularRecipesService | None = getattr(
        request.app.state, "popular_recipes_service", None
    )
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Popular recipes service not available",
        )
    return service


async def get_nutrition_service(request: Request) -> NutritionService:
    """Get the nutrition service from app state.

    Args:
        request: The incoming request.

    Returns:
        Initialized NutritionService.

    Raises:
        HTTPException: 503 if service is not initialized.
    """
    service: NutritionService | None = getattr(
        request.app.state, "nutrition_service", None
    )
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nutrition service not available",
        )
    return service


async def get_allergen_service(request: Request) -> AllergenService:
    """Get the allergen service from app state.

    Args:
        request: The incoming request.

    Returns:
        Initialized AllergenService.

    Raises:
        HTTPException: 503 if service is not initialized.
    """
    service: AllergenService | None = getattr(
        request.app.state, "allergen_service", None
    )
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Allergen service not available",
        )
    return service


async def get_redis_cache_client() -> Redis[bytes] | None:
    """Get the Redis cache client.

    Returns:
        Redis cache client if available, None otherwise.
    """
    try:
        return await get_cache_client()
    except Exception:
        return None


async def get_shopping_service(request: Request) -> ShoppingService:
    """Get the shopping service from app state.

    Args:
        request: The incoming request.

    Returns:
        Initialized ShoppingService.

    Raises:
        HTTPException: 503 if service is not initialized.
    """
    service: ShoppingService | None = getattr(
        request.app.state, "shopping_service", None
    )
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Shopping service not available",
        )
    return service
