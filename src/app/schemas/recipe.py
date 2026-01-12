"""Recipe-related schemas.

This module contains schemas for recipe creation, retrieval, and listing.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, HttpUrl

from app.schemas.base import APIRequest, APIResponse
from app.schemas.enums import Difficulty
from app.schemas.ingredient import Ingredient, WebRecipe


class RecipeStep(APIResponse):
    """Single step in recipe preparation."""

    step_number: int = Field(..., description="Step sequence number")
    instruction: str = Field(..., description="Step instruction text")
    optional: bool = Field(default=False, description="Whether step is optional")
    timer_seconds: int | None = Field(
        default=None,
        description="Optional timer duration in seconds",
    )
    created_at: datetime | None = Field(
        default=None,
        description="Timestamp when step was created",
    )


class Recipe(APIResponse):
    """Complete recipe with ingredients and steps."""

    recipe_id: int | None = Field(default=None, description="Unique recipe identifier")
    title: str = Field(..., description="Recipe title")
    description: str | None = Field(default=None, description="Recipe description")
    origin_url: str | None = Field(default=None, description="Original source URL")
    servings: float | None = Field(default=None, description="Number of servings")
    preparation_time: int | None = Field(
        default=None,
        description="Preparation time in minutes",
    )
    cooking_time: int | None = Field(
        default=None,
        description="Cooking time in minutes",
    )
    difficulty: Difficulty | None = Field(default=None, description="Difficulty level")
    ingredients: list[Ingredient] = Field(..., description="List of ingredients")
    steps: list[RecipeStep] = Field(..., description="Preparation steps")


class CreateRecipeRequest(APIRequest):
    """Request to create a recipe from a URL."""

    recipe_url: HttpUrl = Field(..., description="URL of recipe to scrape")


class CreateRecipeResponse(APIResponse):
    """Response after successful recipe creation."""

    recipe: Recipe = Field(..., description="Created recipe data")


class PopularRecipesResponse(APIResponse):
    """Paginated list of popular recipes."""

    recipes: list[WebRecipe] = Field(..., description="List of popular recipes")
    limit: int = Field(..., description="Maximum recipes returned")
    offset: int = Field(..., description="Starting index")
    count: int = Field(..., description="Total available recipes")
