"""Recommendation schemas for substitutions and pairings.

This module contains schemas for ingredient substitutions and recipe pairings.
"""

from __future__ import annotations

from pydantic import Field

from app.schemas.base import APIResponse
from app.schemas.enums import IngredientUnit
from app.schemas.ingredient import Ingredient, Quantity, WebRecipe


class ConversionRatio(APIResponse):
    """Conversion ratio between original and substitute ingredients."""

    ratio: float = Field(..., ge=0, description="Conversion ratio value")
    measurement: IngredientUnit = Field(..., description="Unit of measurement")


class IngredientSubstitution(APIResponse):
    """Single substitution recommendation."""

    ingredient: str = Field(..., description="Substitute ingredient name")
    quantity: Quantity | None = Field(
        default=None,
        description="Recommended quantity",
    )
    conversion_ratio: ConversionRatio = Field(
        ...,
        description="Conversion ratio from original",
    )


class RecommendedSubstitutionsResponse(APIResponse):
    """Paginated list of ingredient substitutions."""

    ingredient: Ingredient = Field(..., description="Original ingredient")
    recommended_substitutions: list[IngredientSubstitution] = Field(
        ...,
        description="Substitution recommendations",
    )
    limit: int = Field(default=50, description="Maximum items returned")
    offset: int = Field(default=0, description="Starting index")
    count: int = Field(default=0, description="Total available substitutions")


class PairingSuggestionsResponse(APIResponse):
    """Paginated list of recipe pairing suggestions."""

    recipe_id: int = Field(..., description="Source recipe identifier")
    pairing_suggestions: list[WebRecipe] = Field(
        ...,
        description="Recommended pairing recipes",
    )
    limit: int = Field(..., description="Maximum items returned")
    offset: int = Field(..., description="Starting index")
    count: int = Field(..., description="Total available suggestions")
