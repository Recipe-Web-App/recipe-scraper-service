"""Spoonacular recipe search API response models.

These models represent the structure of responses from Spoonacular's recipe search and
similar recipe endpoints.
"""

from typing import Any

from pydantic import ConfigDict, Field, field_validator

from app.api.v1.schemas.base_schema import BaseSchema
from app.core.logging import get_logger

_log = get_logger(__name__)


class SpoonacularRecipeInfo(BaseSchema):
    """Represents a single recipe from Spoonacular API responses."""

    model_config = ConfigDict(extra="ignore")  # Allow extra fields from API response

    id: int = Field(..., description="Spoonacular recipe ID")
    title: str = Field(..., description="Recipe title")
    image: str | None = Field(default=None, description="Recipe image URL")
    image_type: str | None = Field(
        default=None,
        description="Image file type",
        alias="imageType",
    )
    summary: str | None = Field(default=None, description="Recipe summary")
    source_url: str | None = Field(
        default=None,
        description="Original recipe URL",
        alias="sourceUrl",
    )
    spoonacular_source_url: str | None = Field(
        default=None,
        description="Spoonacular recipe page URL",
        alias="spoonacularSourceUrl",
    )
    ready_in_minutes: int | None = Field(
        default=None,
        description="Preparation time in minutes",
        alias="readyInMinutes",
    )
    servings: int | None = Field(default=None, description="Number of servings")

    @field_validator("title", mode="before")
    @classmethod
    def validate_title(cls, v: str | None) -> str:
        """Validate and clean title field."""
        if not v:
            return "Untitled Recipe"
        return str(v).strip()

    @field_validator("source_url", "spoonacular_source_url", mode="before")
    @classmethod
    def validate_urls(cls, v: str | None) -> str | None:
        """Validate URL fields."""
        if v is None:
            return None
        url_str = str(v).strip()
        return url_str if url_str else None


class SpoonacularRecipeSearchResponse(BaseSchema):
    """Response model for Spoonacular recipe search API."""

    model_config = ConfigDict(extra="ignore")  # Allow extra fields from API response

    results: list[SpoonacularRecipeInfo] = Field(
        default_factory=list,
        description="List of recipe results",
    )
    offset: int = Field(default=0, description="Pagination offset")
    number: int = Field(default=0, description="Number of results requested")
    total_results: int = Field(
        default=0,
        description="Total available results",
        alias="totalResults",
    )

    @field_validator("results", mode="before")
    @classmethod
    def validate_results(
        cls,
        v: list[Any] | None,
    ) -> list[SpoonacularRecipeInfo]:
        """Validate and parse the results list."""
        if not v:
            return []

        if not isinstance(v, list):
            return []

        validated_results: list[SpoonacularRecipeInfo] = []
        for item in v:
            if isinstance(item, dict):
                try:
                    recipe_info = SpoonacularRecipeInfo(**item)
                    validated_results.append(recipe_info)
                except (ValueError, TypeError) as e:
                    # Log validation failures and skip invalid items
                    _log.warning("Failed to validate recipe item: {}", e)
                    continue
            # Skip any other types

        return validated_results


class SpoonacularSimilarRecipesResponse(BaseSchema):
    """Response model for Spoonacular similar recipes API.

    This is typically just a list of recipe info objects.
    """

    model_config = ConfigDict(extra="ignore")  # Allow extra fields from API response

    # Direct list response from similar recipes endpoint
    recipes: list[SpoonacularRecipeInfo] = Field(
        default_factory=list,
        description="List of similar recipes",
    )

    @classmethod
    def from_list(
        cls,
        recipe_list: list[dict[str, Any]],
    ) -> "SpoonacularSimilarRecipesResponse":
        """Create response from a list of recipe dictionaries."""
        validated_recipes = []
        for item in recipe_list:
            if isinstance(item, dict):
                try:
                    recipe_info = SpoonacularRecipeInfo(**item)
                    validated_recipes.append(recipe_info)
                except (ValueError, TypeError) as e:
                    _log.warning("Failed to validate similar recipe item: {}", e)
                    continue

        return cls(recipes=validated_recipes)
