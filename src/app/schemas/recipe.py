"""Recipe-related schemas.

This module contains schemas for recipe creation, retrieval, and listing.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import Field, HttpUrl

from app.schemas.base import APIRequest, APIResponse
from app.schemas.enums import Difficulty
from app.schemas.ingredient import Ingredient, WebRecipe


# =============================================================================
# Popular Recipes Schemas
# =============================================================================


class RecipeEngagementMetrics(APIResponse):
    """Engagement metrics extracted from a recipe listing.

    All fields are optional since extraction is dynamic and
    different sites expose different metrics. The scoring
    algorithm handles missing values by redistributing weights.
    """

    rating: float | None = Field(
        default=None,
        ge=0.0,
        le=5.0,
        description="Star rating on 0-5 scale",
    )
    rating_count: int | None = Field(
        default=None,
        ge=0,
        description="Number of ratings/votes",
    )
    favorites: int | None = Field(
        default=None,
        ge=0,
        description="Number of favorites/saves/bookmarks",
    )
    reviews: int | None = Field(
        default=None,
        ge=0,
        description="Number of text reviews",
    )

    @property
    def has_any_metrics(self) -> bool:
        """Check if any engagement metrics were extracted."""
        return any(
            v is not None
            for v in (self.rating, self.rating_count, self.favorites, self.reviews)
        )


class PopularRecipe(APIResponse):
    """A popular recipe with engagement metrics and normalized score.

    Internal representation that includes extracted engagement data
    and computed popularity score. Converts to WebRecipe for API responses.
    """

    recipe_name: str = Field(description="Name/title of the recipe")
    url: str = Field(description="Full URL to the recipe page")
    source: str = Field(description="Source website name (e.g., 'AllRecipes')")
    raw_rank: int = Field(
        ge=1,
        description="Original position on the source page (1 = first)",
    )
    metrics: RecipeEngagementMetrics = Field(
        default_factory=RecipeEngagementMetrics,
        description="Extracted engagement metrics",
    )
    normalized_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Final computed popularity score (0-1)",
    )

    def to_web_recipe(self) -> WebRecipe:
        """Convert to WebRecipe for API response."""
        return WebRecipe(recipe_name=self.recipe_name, url=self.url)


class PopularRecipesData(APIResponse):
    """Cached popular recipes aggregation data.

    Contains the full list of fetched and scored recipes along
    with metadata about the fetch operation for cache management.
    """

    recipes: list[PopularRecipe] = Field(
        default_factory=list,
        description="List of popular recipes sorted by score",
    )
    total_count: int = Field(
        default=0,
        ge=0,
        description="Total number of recipes fetched",
    )
    last_updated: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO timestamp of last cache refresh",
    )
    sources_fetched: list[str] = Field(
        default_factory=list,
        description="Names of sources successfully fetched",
    )
    fetch_errors: dict[str, str] = Field(
        default_factory=dict,
        description="Map of source name to error message for failed fetches",
    )

    @property
    def has_recipes(self) -> bool:
        """Check if any recipes were fetched."""
        return len(self.recipes) > 0

    @property
    def partial_success(self) -> bool:
        """Check if some sources failed but we have results."""
        return self.has_recipes and len(self.fetch_errors) > 0


# =============================================================================
# Recipe Scraping Schemas
# =============================================================================


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
