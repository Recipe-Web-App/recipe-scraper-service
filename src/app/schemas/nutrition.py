"""Nutritional information schemas.

This module contains schemas for nutritional data including macronutrients,
vitamins, minerals, and ingredient classification.
"""

from __future__ import annotations

from pydantic import Field

from app.schemas.base import APIResponse
from app.schemas.enums import Allergen, FoodGroup, NutriscoreGrade
from app.schemas.ingredient import Quantity


class Sugars(APIResponse):
    """Sugar content breakdown."""

    sugar_g: str | None = Field(default=None, description="Total sugar in grams")
    added_sugars_g: str | None = Field(
        default=None,
        description="Added sugars in grams",
    )


class Fats(APIResponse):
    """Fat content breakdown."""

    fat_g: str | None = Field(default=None, description="Total fat in grams")
    saturated_fat_g: str | None = Field(
        default=None,
        description="Saturated fat in grams",
    )
    monounsaturated_fat_g: str | None = Field(
        default=None,
        description="Monounsaturated fat in grams",
    )
    polyunsaturated_fat_g: str | None = Field(
        default=None,
        description="Polyunsaturated fat in grams",
    )
    omega3_fat_g: str | None = Field(
        default=None,
        description="Omega-3 fat in grams",
    )
    omega6_fat_g: str | None = Field(
        default=None,
        description="Omega-6 fat in grams",
    )
    omega9_fat_g: str | None = Field(
        default=None,
        description="Omega-9 fat in grams",
    )
    trans_fat_g: str | None = Field(default=None, description="Trans fat in grams")


class Fibers(APIResponse):
    """Fiber content breakdown."""

    fiber_g: str | None = Field(default=None, description="Total fiber in grams")
    soluble_fiber_g: str | None = Field(
        default=None,
        description="Soluble fiber in grams",
    )
    insoluble_fiber_g: str | None = Field(
        default=None,
        description="Insoluble fiber in grams",
    )


class MacroNutrients(APIResponse):
    """Macronutrient information."""

    calories: int | None = Field(default=None, ge=0, description="Total calories")
    carbs_g: str | None = Field(default=None, description="Carbohydrates in grams")
    cholesterol_mg: str | None = Field(
        default=None,
        description="Cholesterol in milligrams",
    )
    protein_g: str | None = Field(default=None, description="Protein in grams")
    sugars: Sugars | None = Field(default=None, description="Sugar breakdown")
    fats: Fats | None = Field(default=None, description="Fat breakdown")
    fibers: Fibers | None = Field(default=None, description="Fiber breakdown")


class Vitamins(APIResponse):
    """Vitamin content information."""

    vitamin_a_mg: str | None = Field(
        default=None,
        description="Vitamin A in milligrams",
    )
    vitamin_b6_mg: str | None = Field(
        default=None,
        description="Vitamin B6 in milligrams",
    )
    vitamin_b12_mg: str | None = Field(
        default=None,
        description="Vitamin B12 in milligrams",
    )
    vitamin_c_mg: str | None = Field(
        default=None,
        description="Vitamin C in milligrams",
    )
    vitamin_d_mg: str | None = Field(
        default=None,
        description="Vitamin D in milligrams",
    )
    vitamin_e_mg: str | None = Field(
        default=None,
        description="Vitamin E in milligrams",
    )
    vitamin_k_mg: str | None = Field(
        default=None,
        description="Vitamin K in milligrams",
    )


class Minerals(APIResponse):
    """Mineral content information."""

    calcium_mg: str | None = Field(default=None, description="Calcium in milligrams")
    iron_mg: str | None = Field(default=None, description="Iron in milligrams")
    magnesium_mg: str | None = Field(
        default=None,
        description="Magnesium in milligrams",
    )
    potassium_mg: str | None = Field(
        default=None,
        description="Potassium in milligrams",
    )
    sodium_mg: str | None = Field(default=None, description="Sodium in milligrams")
    zinc_mg: str | None = Field(default=None, description="Zinc in milligrams")


class IngredientClassification(APIResponse):
    """Ingredient classification and metadata."""

    allergies: list[Allergen] | None = Field(
        default=None,
        description="Associated allergens",
    )
    food_groups: list[FoodGroup] | None = Field(
        default=None,
        description="Food group classifications",
    )
    nutriscore_score: int | None = Field(
        default=None,
        ge=-15,
        le=40,
        description="Nutri-Score value (-15 to +40)",
    )
    nutriscore_grade: NutriscoreGrade | None = Field(
        default=None,
        description="Nutri-Score letter grade",
    )
    product_name: str | None = Field(
        default=None,
        description="Product name from database",
    )
    brands: str | None = Field(default=None, description="Brand information")
    categories: str | None = Field(default=None, description="Product categories")


class IngredientNutritionalInfoResponse(APIResponse):
    """Complete nutritional information for an ingredient."""

    quantity: Quantity = Field(..., description="Quantity for nutritional values")
    classification: IngredientClassification | None = Field(
        default=None,
        description="Ingredient classification",
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
