"""Shopping information schemas.

This module contains schemas for ingredient and recipe shopping data.
"""

from __future__ import annotations

from pydantic import Field

from app.schemas.base import APIResponse
from app.schemas.ingredient import Quantity


class IngredientShoppingInfoResponse(APIResponse):
    """Shopping information for a single ingredient."""

    ingredient_name: str = Field(..., description="Name of the ingredient")
    quantity: Quantity = Field(..., description="Required quantity")
    estimated_price: str | None = Field(
        default=None,
        description="Estimated price in currency (None if unavailable)",
    )
    price_confidence: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Confidence score (0-1). Higher for direct pricing, lower for food group averages.",
    )
    data_source: str | None = Field(
        default=None,
        description="Data source for the price (e.g., 'USDA_FVP', 'USDA_FMAP')",
    )
    currency: str = Field(
        default="USD",
        description="Currency code for the estimated price",
    )


class RecipeShoppingInfoResponse(APIResponse):
    """Shopping information for a complete recipe."""

    recipe_id: int = Field(..., ge=1, description="Recipe identifier")
    ingredients: dict[str, IngredientShoppingInfoResponse] = Field(
        ...,
        description="Shopping info by ingredient name",
    )
    total_estimated_cost: str = Field(..., description="Total estimated cost")
    missing_ingredients: list[int] | None = Field(
        default=None,
        description="List of ingredient IDs with unavailable pricing data",
    )
