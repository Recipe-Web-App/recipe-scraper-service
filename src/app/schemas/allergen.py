"""Allergen information schemas.

This module contains schemas for allergen data including presence types,
confidence levels, and aggregated recipe allergens.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from app.schemas.base import APIResponse
from app.schemas.enums import Allergen


class AllergenPresenceType(StrEnum):
    """Classification of allergen presence in an ingredient."""

    CONTAINS = "CONTAINS"  # Definitely contains this allergen
    MAY_CONTAIN = "MAY_CONTAIN"  # Cross-contamination possible
    TRACES = "TRACES"  # May contain trace amounts


class AllergenDataSource(StrEnum):
    """Source of allergen data."""

    USDA = "USDA"  # USDA FoodData Central
    OPEN_FOOD_FACTS = "OPEN_FOOD_FACTS"  # Open Food Facts API
    LLM_INFERRED = "LLM_INFERRED"  # LLM inference
    MANUAL = "MANUAL"  # Manual entry


class AllergenInfo(APIResponse):
    """Single allergen with presence type and confidence metadata."""

    allergen: Allergen = Field(
        ...,
        description="The allergen type from the Allergen enum",
    )
    presence_type: AllergenPresenceType = Field(
        default=AllergenPresenceType.CONTAINS,
        description="How the allergen is present (contains, may contain, traces)",
    )
    confidence_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1) for this allergen classification",
    )
    source_notes: str | None = Field(
        default=None,
        description="Additional notes about the allergen source or reason",
    )


class IngredientAllergenResponse(APIResponse):
    """Allergen information response for a single ingredient."""

    ingredient_id: int | None = Field(
        default=None,
        description="Database ingredient identifier",
    )
    ingredient_name: str | None = Field(
        default=None,
        description="Ingredient name as queried",
    )
    usda_food_description: str | None = Field(
        default=None,
        description="USDA food description if available",
    )
    allergens: list[AllergenInfo] = Field(
        default_factory=list,
        description="List of allergens present in this ingredient",
    )
    data_source: AllergenDataSource | None = Field(
        default=None,
        description="Source of allergen data (USDA, OPEN_FOOD_FACTS, etc.)",
    )
    overall_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Overall confidence score for the allergen profile",
    )


class RecipeAllergenResponse(APIResponse):
    """Aggregated allergen information for a recipe."""

    contains: list[Allergen] = Field(
        default_factory=list,
        description="Allergens definitely present in the recipe",
    )
    may_contain: list[Allergen] = Field(
        default_factory=list,
        description="Allergens that may be present (cross-contamination, traces)",
    )
    allergens: list[AllergenInfo] = Field(
        default_factory=list,
        description="Detailed allergen information with confidence scores",
    )
    ingredient_details: dict[str, IngredientAllergenResponse] | None = Field(
        default=None,
        description="Per-ingredient allergen breakdown (if requested)",
    )
    missing_ingredients: list[int] = Field(
        default_factory=list,
        description="Ingredient IDs without allergen data",
    )
