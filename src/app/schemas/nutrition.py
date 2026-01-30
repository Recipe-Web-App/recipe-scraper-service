"""Nutritional information schemas.

This module contains schemas for nutritional data including macronutrients,
vitamins, and minerals using structured NutrientValue types.
"""

from __future__ import annotations

from pydantic import Field

from app.schemas.base import APIResponse
from app.schemas.enums import NutrientUnit
from app.schemas.ingredient import Quantity


class NutrientValue(APIResponse):
    """A nutrient measurement with amount and unit."""

    amount: float | None = Field(default=None, ge=0, description="Numeric value")
    measurement: NutrientUnit = Field(..., description="Unit of measurement")


class Fats(APIResponse):
    """Fat content breakdown."""

    total: NutrientValue | None = Field(default=None, description="Total fat")
    saturated: NutrientValue | None = Field(
        default=None,
        description="Saturated fat",
    )
    monounsaturated: NutrientValue | None = Field(
        default=None,
        description="Monounsaturated fat",
    )
    polyunsaturated: NutrientValue | None = Field(
        default=None,
        description="Polyunsaturated fat",
    )
    trans: NutrientValue | None = Field(default=None, description="Trans fat")


class MacroNutrients(APIResponse):
    """Macronutrient information."""

    calories: NutrientValue | None = Field(
        default=None,
        description="Total calories",
    )
    carbs: NutrientValue | None = Field(default=None, description="Carbohydrates")
    protein: NutrientValue | None = Field(default=None, description="Protein")
    cholesterol: NutrientValue | None = Field(default=None, description="Cholesterol")
    sodium: NutrientValue | None = Field(default=None, description="Sodium")
    fiber: NutrientValue | None = Field(default=None, description="Dietary fiber")
    sugar: NutrientValue | None = Field(default=None, description="Total sugar")
    added_sugar: NutrientValue | None = Field(
        default=None,
        description="Added sugars",
    )
    fats: Fats | None = Field(default=None, description="Fat breakdown")


class Vitamins(APIResponse):
    """Vitamin content information."""

    vitamin_a: NutrientValue | None = Field(default=None, description="Vitamin A")
    vitamin_b6: NutrientValue | None = Field(default=None, description="Vitamin B6")
    vitamin_b12: NutrientValue | None = Field(default=None, description="Vitamin B12")
    vitamin_c: NutrientValue | None = Field(default=None, description="Vitamin C")
    vitamin_d: NutrientValue | None = Field(default=None, description="Vitamin D")
    vitamin_e: NutrientValue | None = Field(default=None, description="Vitamin E")
    vitamin_k: NutrientValue | None = Field(default=None, description="Vitamin K")


class Minerals(APIResponse):
    """Mineral content information."""

    calcium: NutrientValue | None = Field(default=None, description="Calcium")
    iron: NutrientValue | None = Field(default=None, description="Iron")
    magnesium: NutrientValue | None = Field(default=None, description="Magnesium")
    potassium: NutrientValue | None = Field(default=None, description="Potassium")
    zinc: NutrientValue | None = Field(default=None, description="Zinc")


class IngredientNutritionalInfoResponse(APIResponse):
    """Complete nutritional information for an ingredient."""

    quantity: Quantity = Field(..., description="Quantity for nutritional values")
    usda_food_description: str | None = Field(
        default=None,
        description="USDA food description for matched ingredient",
    )
    macro_nutrients: MacroNutrients | None = Field(
        default=None,
        description="Macronutrient information",
    )
    vitamins: Vitamins | None = Field(default=None, description="Vitamin content")
    minerals: Minerals | None = Field(default=None, description="Mineral content")


class RecipeNutritionalInfoResponse(APIResponse):
    """Nutritional information for a complete recipe."""

    ingredients: dict[str, IngredientNutritionalInfoResponse] | None = Field(
        default=None,
        description="Per-ingredient nutritional data",
    )
    missing_ingredients: list[int] | None = Field(
        default=None,
        description="Ingredient IDs without nutritional data",
    )
    total: IngredientNutritionalInfoResponse | None = Field(
        default=None,
        description="Aggregated nutritional totals",
    )
