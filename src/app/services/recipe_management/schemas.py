"""Schemas for Recipe Management Service API.

These schemas match the downstream Recipe Management Service's
OpenAPI specification for recipe creation.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class IngredientUnit(StrEnum):
    """Valid ingredient measurement units.

    Must match the IngredientUnit enum in Recipe Management Service.
    """

    G = "G"
    KG = "KG"
    OZ = "OZ"
    LB = "LB"
    ML = "ML"
    L = "L"
    CUP = "CUP"
    TBSP = "TBSP"
    TSP = "TSP"
    PIECE = "PIECE"
    CLOVE = "CLOVE"
    SLICE = "SLICE"
    PINCH = "PINCH"
    CAN = "CAN"
    BOTTLE = "BOTTLE"
    PACKET = "PACKET"
    UNIT = "UNIT"


class DifficultyLevel(StrEnum):
    """Recipe difficulty levels."""

    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class CreateRecipeIngredientRequest(BaseModel):
    """Request schema for creating a recipe ingredient."""

    ingredient_id: int | None = Field(
        default=None,
        alias="ingredientId",
        description="Optional ID for referencing existing ingredients",
    )
    ingredient_name: str = Field(
        ...,
        alias="ingredientName",
        min_length=1,
        max_length=100,
        description="The ingredient name",
    )
    quantity: float = Field(
        ...,
        gt=0,
        description="The quantity of the ingredient",
    )
    unit: IngredientUnit = Field(
        ...,
        description="The measurement unit",
    )
    is_optional: bool = Field(
        default=False,
        alias="isOptional",
        description="Whether the ingredient is optional",
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Notes about the ingredient",
    )

    model_config = {"populate_by_name": True}


class CreateRecipeStepRequest(BaseModel):
    """Request schema for creating a recipe step."""

    step_number: int = Field(
        ...,
        alias="stepNumber",
        ge=1,
        description="Step sequence number",
    )
    instruction: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Step instructions",
    )
    optional: bool = Field(
        default=False,
        description="Whether this step is optional",
    )
    timer_seconds: int | None = Field(
        default=None,
        alias="timerSeconds",
        ge=0,
        description="Timer in seconds for this step",
    )

    model_config = {"populate_by_name": True}


class CreateRecipeRequest(BaseModel):
    """Request schema for creating a recipe in Recipe Management Service."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Recipe title",
    )
    description: str = Field(
        ...,
        max_length=2000,
        description="Recipe description",
    )
    servings: float = Field(
        ...,
        ge=1,
        le=1000,
        description="Number of servings",
    )
    preparation_time: int | None = Field(
        default=None,
        alias="preparationTime",
        ge=0,
        description="Preparation time in minutes",
    )
    cooking_time: int | None = Field(
        default=None,
        alias="cookingTime",
        ge=0,
        description="Cooking time in minutes",
    )
    difficulty: DifficultyLevel | None = Field(
        default=None,
        description="Recipe difficulty level",
    )
    ingredients: list[CreateRecipeIngredientRequest] = Field(
        ...,
        min_length=1,
        description="List of recipe ingredients",
    )
    steps: list[CreateRecipeStepRequest] = Field(
        ...,
        min_length=1,
        description="List of cooking steps",
    )

    model_config = {"populate_by_name": True}


class RecipeResponse(BaseModel):
    """Response schema from Recipe Management Service after creating a recipe."""

    id: int = Field(..., description="Created recipe ID")
    title: str = Field(..., description="Recipe title")
    slug: str | None = Field(default=None, description="URL-friendly slug")

    model_config = {"populate_by_name": True}
