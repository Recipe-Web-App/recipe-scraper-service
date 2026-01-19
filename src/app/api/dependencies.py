"""FastAPI dependencies for service access.

This module provides reusable dependencies for accessing application services
in FastAPI route handlers. Services are initialized during application startup
and stored in app.state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, status

from app.core.events.lifespan import get_llm_client
from app.parsing.ingredient import IngredientParser


if TYPE_CHECKING:
    from app.services.recipe_management.client import RecipeManagementClient
    from app.services.scraping.service import RecipeScraperService


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
