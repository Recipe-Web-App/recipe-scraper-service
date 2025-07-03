"""Spoonacular recipe search API response models.

These models represent the structure of responses from Spoonacular's recipe search and
similar recipe endpoints.
"""

from typing import Any

from pydantic import ConfigDict, Field, field_validator

from app.api.v1.schemas.base_schema import BaseSchema
from app.api.v1.schemas.downstream.spoonacular.recipe_info import SpoonacularRecipeInfo
from app.core.logging import get_logger

_log = get_logger(__name__)


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
