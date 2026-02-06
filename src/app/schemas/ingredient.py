"""Ingredient-related schemas.

This module contains schemas for ingredients, quantities, and web recipes.
"""

from __future__ import annotations

from pydantic import Field

from app.schemas.base import APIResponse
from app.schemas.enums import IngredientUnit


class Quantity(APIResponse):
    """Quantity specification for an ingredient."""

    amount: float = Field(..., ge=0, description="Numeric quantity value")
    measurement: IngredientUnit = Field(
        default=IngredientUnit.UNIT,
        description="Unit of measurement",
    )


class Ingredient(APIResponse):
    """Ingredient data with optional quantity."""

    ingredient_id: int | None = Field(
        default=None,
        description="Unique ingredient identifier",
    )
    name: str | None = Field(default=None, description="Ingredient name")
    quantity: Quantity | None = Field(default=None, description="Ingredient quantity")


class WebRecipe(APIResponse):
    """Recipe reference from an external website."""

    recipe_name: str = Field(..., description="Name of the recipe")
    url: str = Field(..., description="Source URL of the recipe")
