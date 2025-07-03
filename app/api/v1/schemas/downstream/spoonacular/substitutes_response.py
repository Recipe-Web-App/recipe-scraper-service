"""Spoonacular ingredient substitutes API response models.

These models represent the structure of responses from Spoonacular's ingredient
substitutes endpoint.
"""

from typing import Any

from pydantic import ConfigDict, Field, field_validator

from app.api.v1.schemas.base_schema import BaseSchema
from app.api.v1.schemas.downstream.spoonacular.substitute_item import (
    SpoonacularSubstituteItem,
)
from app.core.logging import get_logger

_log = get_logger(__name__)


class SpoonacularSubstitutesResponse(BaseSchema):
    """Response model for Spoonacular ingredient substitutes API.

    Represents the complete response structure from the Spoonacular API for ingredient
    substitution requests.
    """

    model_config = ConfigDict(extra="ignore")  # Allow extra fields from API response

    ingredient: str | None = Field(
        default=None,
        description="The original ingredient name from the request",
    )
    status: str | None = Field(
        default=None,
        description="Status of the API response ('success' or 'failure')",
    )
    message: str | None = Field(
        default=None,
        description="Error message if status is 'failure'",
    )
    substitutes: list[SpoonacularSubstituteItem | str] = Field(
        default_factory=list,
        description="List of substitute ingredients (can be strings or objects)",
    )

    @field_validator("substitutes", mode="before")
    @classmethod
    def validate_substitutes(
        cls,
        v: list[Any] | None,
    ) -> list[SpoonacularSubstituteItem | str]:
        """Validate and parse the substitutes list."""
        if not v:
            return []

        if not isinstance(v, list):
            return []

        validated_substitutes: list[SpoonacularSubstituteItem | str] = []
        for item in v:
            if isinstance(item, str):
                # Keep simple string items as strings
                if item.strip():
                    validated_substitutes.append(item.strip())
            elif isinstance(item, dict):
                # Convert dict items to SpoonacularSubstituteItem
                try:
                    substitute_item = SpoonacularSubstituteItem(**item)
                    validated_substitutes.append(substitute_item)
                except (ValueError, TypeError) as e:
                    # Log validation failures and skip invalid items
                    _log.warning("Failed to validate substitute item: {}", e)
                    continue
            # Skip any other types

        return validated_substitutes

    def get_ingredient_name(self, item: SpoonacularSubstituteItem | str) -> str:
        """Extract the ingredient name from a substitute item.

        Args:
            item: Either a string or SpoonacularSubstituteItem

        Returns:
            The ingredient name, cleaned and extracted
        """
        if isinstance(item, str):
            # For string items, extract name before parentheses or dashes
            return item.split(" (")[0].split(" -")[0].strip()

        # For object items, use name field or substitute field
        ingredient_name = item.name or item.substitute or ""
        return ingredient_name.split(" (")[0].split(" -")[0].strip()

    def get_description(self, item: SpoonacularSubstituteItem | str) -> str:
        """Extract description/notes from a substitute item.

        Args:
            item: Either a string or SpoonacularSubstituteItem

        Returns:
            The description or original string
        """
        if isinstance(item, str):
            return item

        return item.description or item.name or item.substitute or ""
