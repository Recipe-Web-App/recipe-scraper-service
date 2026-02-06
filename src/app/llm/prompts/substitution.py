"""Ingredient substitution prompt for LLM-based substitution generation.

This module defines the prompt and output schema for generating ingredient
substitutions with conversion ratios.
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


class SubstitutionResult(BaseModel):
    """A single substitution recommendation from LLM."""

    ingredient: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="The substitute ingredient name",
    )
    ratio: float = Field(
        ...,
        gt=0,
        le=10,
        description="Conversion ratio (multiply original amount by this)",
    )
    measurement: IngredientUnit = Field(
        ...,
        description="Unit of measurement for the substitute",
    )
    notes: str | None = Field(
        default=None,
        max_length=200,
        description="Usage notes (e.g., 'best for baking', 'adds moisture')",
    )
    confidence: float = Field(
        default=0.8,
        ge=0,
        le=1,
        description="Confidence score for this substitution (0-1)",
    )


class SubstitutionListResult(BaseModel):
    """Output schema for substitution generation."""

    substitutions: list[SubstitutionResult] = Field(
        ...,
        min_length=1,
        max_length=15,
        description="List of recommended substitutions",
    )


class IngredientSubstitutionPrompt(BasePrompt[SubstitutionListResult]):
    """Prompt for generating ingredient substitutions.

    Example input:
        ingredient_name="butter", food_group="DAIRY"

    Example output:
        {
            "substitutions": [
                {
                    "ingredient": "coconut oil",
                    "ratio": 1.0,
                    "measurement": "CUP",
                    "notes": "Best for baking, adds slight coconut flavor",
                    "confidence": 0.9
                },
                {
                    "ingredient": "olive oil",
                    "ratio": 0.75,
                    "measurement": "CUP",
                    "notes": "Best for savory dishes",
                    "confidence": 0.85
                }
            ]
        }
    """

    output_schema: ClassVar[type[BaseModel]] = SubstitutionListResult

    system_prompt: ClassVar[
        str | None
    ] = """You are a culinary expert specializing in ingredient substitutions.
Your task is to suggest practical ingredient substitutes with accurate conversion ratios.

Rules:
1. Generate 5-10 high-quality substitutions
2. Provide accurate conversion ratios (e.g., 0.75 means use 75% of the original amount)
3. Consider the food group when suggesting substitutes
4. Include both common and less-known alternatives
5. Account for dietary variations (vegan, dairy-free, gluten-free options when applicable)
6. Rate your confidence for each suggestion (0-1 scale)
7. Add brief notes about best use cases or flavor differences

Conversion ratio guidelines:
- 1.0 = equal substitution (1 cup butter = 1 cup coconut oil)
- 0.75 = use 75% of original (1 cup butter = 0.75 cup olive oil)
- 1.25 = use 125% of original (more volume needed)

Valid units: G, KG, OZ, LB, ML, L, CUP, TBSP, TSP, PIECE, CLOVE, SLICE, PINCH, CAN, BOTTLE, PACKET, UNIT

Common substitution patterns:
- Butter: coconut oil, olive oil, applesauce, mashed banana, Greek yogurt
- Eggs: flax egg, chia egg, applesauce, mashed banana, silken tofu
- Milk: oat milk, almond milk, soy milk, coconut milk
- All-purpose flour: whole wheat flour, almond flour, oat flour, gluten-free blend
- Sugar: honey, maple syrup, coconut sugar, stevia"""

    temperature: ClassVar[float] = 0.3  # Some creativity for variety
    max_tokens: ClassVar[int | None] = 2048

    def format(self, **kwargs: Any) -> str:
        """Format the prompt with ingredient information.

        Args:
            **kwargs: Must contain 'ingredient_name'. May contain
                'food_group' and 'quantity' for additional context.

        Returns:
            Formatted prompt string.

        Raises:
            ValueError: If 'ingredient_name' key is missing.
        """
        ingredient_name = kwargs.get("ingredient_name")
        if ingredient_name is None:
            msg = "Missing required 'ingredient_name' argument"
            raise ValueError(msg)

        food_group = kwargs.get("food_group")
        quantity = kwargs.get("quantity")

        # Build context sections
        context_parts = [f"Ingredient: {ingredient_name}"]

        if food_group:
            context_parts.append(f"Food group: {food_group}")

        if quantity:
            amount = quantity.get("amount")
            measurement = quantity.get("measurement")
            if amount and measurement:
                context_parts.append(f"Quantity context: {amount} {measurement}")

        context = "\n".join(context_parts)

        return f"""Generate substitution recommendations for the following ingredient.
Return a JSON object with a "substitutions" array containing 5-10 substitution options.

{context}

For each substitution, provide:
- ingredient: The substitute ingredient name
- ratio: Conversion ratio (multiply original amount by this value)
- measurement: Unit of measurement (use the same unit as the original when possible)
- notes: Brief usage notes or flavor considerations
- confidence: Your confidence in this substitution (0-1)

Prioritize practical, commonly available substitutes first."""
