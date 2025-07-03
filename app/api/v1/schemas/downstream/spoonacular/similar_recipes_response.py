"""Schema for Spoonacular similar recipes API response."""

from typing import Any

from pydantic import ConfigDict, Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.api.v1.schemas.downstream.spoonacular.recipe_info import SpoonacularRecipeInfo
from app.core.logging import get_logger

_log = get_logger(__name__)


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
