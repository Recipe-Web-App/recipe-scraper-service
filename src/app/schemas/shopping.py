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
        description="Estimated price (None if unavailable)",
    )


class RecipeShoppingInfoResponse(APIResponse):
    """Shopping information for a complete recipe."""

    recipe_id: int = Field(..., ge=1, description="Recipe identifier")
    ingredients: dict[str, IngredientShoppingInfoResponse] = Field(
        ...,
        description="Shopping info by ingredient name",
    )
    total_estimated_cost: str = Field(..., description="Total estimated cost")
