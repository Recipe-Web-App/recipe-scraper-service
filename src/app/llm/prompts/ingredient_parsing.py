"""Ingredient parsing prompt for LLM-based ingredient normalization.

This module defines the prompt and output schema for parsing raw ingredient
strings into structured data suitable for the Recipe Management Service.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from .base import BasePrompt


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


class ParsedIngredient(BaseModel):
    """A single parsed ingredient."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="The ingredient name, normalized (e.g., 'all-purpose flour')",
    )
    quantity: float = Field(
        ...,
        gt=0,
        description="The numeric quantity (e.g., 2.5)",
    )
    unit: IngredientUnit = Field(
        ...,
        description="The measurement unit",
    )
    is_optional: bool = Field(
        default=False,
        description="Whether the ingredient is optional",
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Additional notes (e.g., 'sifted', 'room temperature')",
    )


class ParsedIngredientList(BaseModel):
    """Output schema for batch ingredient parsing."""

    ingredients: list[ParsedIngredient] = Field(
        ...,
        min_length=1,
        description="List of parsed ingredients in the same order as input",
    )


class IngredientParsingPrompt(BasePrompt[ParsedIngredientList]):
    """Prompt for parsing raw ingredient strings into structured data.

    Example input:
        ["2 cups all-purpose flour, sifted", "1/2 tsp salt", "3 large eggs"]

    Example output:
        {
            "ingredients": [
                {"name": "all-purpose flour", "quantity": 2.0, "unit": "CUP", "notes": "sifted"},
                {"name": "salt", "quantity": 0.5, "unit": "TSP"},
                {"name": "eggs", "quantity": 3.0, "unit": "PIECE", "notes": "large"}
            ]
        }
    """

    output_schema: ClassVar[type[BaseModel]] = ParsedIngredientList

    system_prompt: ClassVar[
        str | None
    ] = """You are an expert ingredient parser for recipe management.
Your task is to parse raw ingredient strings into structured data.

Rules:
1. Extract the ingredient name without quantities or units
2. Convert fractions to decimals (1/2 = 0.5, 1/4 = 0.25, 1/3 = 0.333)
3. Normalize unit names to the standard enum values
4. Move descriptors like "large", "fresh", "diced" to notes
5. Mark ingredients as optional if they contain "(optional)" or similar
6. For items without clear units (e.g., "3 eggs"), use PIECE
7. For items with "a pinch of" or similar, use PINCH with quantity 1
8. Preserve the input order exactly

Valid units: G, KG, OZ, LB, ML, L, CUP, TBSP, TSP, PIECE, CLOVE, SLICE, PINCH, CAN, BOTTLE, PACKET, UNIT

Common conversions:
- tablespoon/tbsp/T → TBSP
- teaspoon/tsp/t → TSP
- cup/c → CUP
- ounce/oz → OZ
- pound/lb → LB
- gram/g → G
- kilogram/kg → KG
- milliliter/ml → ML
- liter/l → L
- clove (for garlic) → CLOVE
- slice → SLICE
- can → CAN
- bottle → BOTTLE
- packet/package → PACKET
- whole items (eggs, lemons, etc.) → PIECE
- generic countable items → UNIT"""

    temperature: ClassVar[float] = 0.0  # Deterministic parsing
    max_tokens: ClassVar[int | None] = 4096

    def format(self, **kwargs: Any) -> str:
        """Format the prompt with ingredient strings.

        Args:
            **kwargs: Must contain 'ingredients' key with list of raw
                ingredient strings to parse.

        Returns:
            Formatted prompt string.

        Raises:
            ValueError: If 'ingredients' key is missing.
        """
        ingredients = kwargs.get("ingredients")
        if ingredients is None:
            msg = "Missing required 'ingredients' argument"
            raise ValueError(msg)
        ingredient_list = "\n".join(f"- {ing}" for ing in ingredients)
        return f"""Parse the following ingredient strings into structured data.
Return a JSON object with an "ingredients" array containing one object per input ingredient, in the same order.

Ingredients to parse:
{ingredient_list}"""
