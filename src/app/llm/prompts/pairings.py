"""Recipe pairing prompt for LLM-based pairing generation.

This module defines the prompt and output schema for generating recipe
pairing suggestions based on flavor profiles and cuisine types.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from .base import BasePrompt


class PairingResult(BaseModel):
    """A single pairing recommendation from LLM."""

    recipe_name: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Name of the suggested pairing recipe",
    )
    url: str = Field(
        ...,
        description="URL to find this recipe (use popular recipe websites)",
    )
    pairing_reason: str = Field(
        ...,
        max_length=300,
        description="Brief explanation of why this recipe pairs well",
    )
    cuisine_type: str | None = Field(
        default=None,
        max_length=50,
        description="The cuisine type of the suggestion (e.g., Italian, Mexican)",
    )
    confidence: float = Field(
        default=0.8,
        ge=0,
        le=1,
        description="Confidence score for this pairing (0-1)",
    )


class PairingListResult(BaseModel):
    """Output schema for pairing generation."""

    pairings: list[PairingResult] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of recommended recipe pairings",
    )


class RecipePairingPrompt(BasePrompt[PairingListResult]):
    """Prompt for generating recipe pairings.

    Example input:
        title="Grilled Salmon", ingredients=["salmon", "lemon", "dill"]

    Example output:
        {
            "pairings": [
                {
                    "recipe_name": "Roasted Asparagus with Parmesan",
                    "url": "https://www.allrecipes.com/recipe/123/roasted-asparagus/",
                    "pairing_reason": "Light vegetable side that complements rich salmon",
                    "cuisine_type": "American",
                    "confidence": 0.95
                },
                {
                    "recipe_name": "Lemon Rice Pilaf",
                    "url": "https://www.foodnetwork.com/recipes/lemon-rice-pilaf",
                    "pairing_reason": "Citrus notes echo the lemon in the salmon",
                    "cuisine_type": "Mediterranean",
                    "confidence": 0.9
                }
            ]
        }
    """

    output_schema: ClassVar[type[BaseModel]] = PairingListResult

    system_prompt: ClassVar[
        str | None
    ] = """You are a culinary expert specializing in meal planning and recipe pairings.
Your task is to suggest complementary recipes that pair well with the given recipe.

Rules:
1. Generate 5-15 high-quality pairing suggestions
2. Consider flavor profiles (sweet/savory, spicy/mild, rich/light, acidic/creamy)
3. Consider cuisine compatibility (e.g., Italian mains with Italian sides)
4. Suggest a balanced mix of:
   - Side dishes that complement the main
   - Appetizers that set up the meal
   - Desserts that finish the meal
   - Beverages (wine, cocktails, non-alcoholic)
   - Bread/grain accompaniments
5. Include URLs to popular recipe websites (allrecipes.com, foodnetwork.com, epicurious.com, etc.)
6. Rate your confidence for each suggestion (0-1 scale)
7. Provide a brief reason explaining why each pairing works

Pairing principles:
- Balance: Rich dishes pair with light sides; heavy mains need refreshing accompaniments
- Complement: Similar flavor profiles can enhance each other
- Contrast: Opposite flavors can create interesting combinations
- Regional: Dishes from the same cuisine often pair naturally
- Seasonal: Consider seasonal ingredients and traditional combinations"""

    temperature: ClassVar[float] = 0.4  # Moderate creativity for variety
    max_tokens: ClassVar[int | None] = 2048

    def format(self, **kwargs: Any) -> str:
        """Format the prompt with recipe information.

        Args:
            **kwargs: Must contain 'title'. May contain
                'description' and 'ingredients' for additional context.

        Returns:
            Formatted prompt string.

        Raises:
            ValueError: If 'title' key is missing.
        """
        title = kwargs.get("title")
        if title is None:
            msg = "Missing required 'title' argument"
            raise ValueError(msg)

        description = kwargs.get("description", "")
        ingredients = kwargs.get("ingredients", [])

        # Limit ingredients to top 15 for prompt efficiency
        ingredients_str = ", ".join(ingredients[:15]) if ingredients else "N/A"

        # Truncate description if too long
        description_str = description[:500] if description else "N/A"

        return f"""Generate recipe pairing suggestions for the following recipe.
Return a JSON object with a "pairings" array containing 5-15 pairing options.

Recipe: {title}
Description: {description_str}
Key Ingredients: {ingredients_str}

For each pairing, provide:
- recipe_name: Name of the suggested recipe
- url: URL to find this recipe (use real recipe website URLs)
- pairing_reason: Brief explanation of why it pairs well (max 300 chars)
- cuisine_type: The cuisine type of the suggestion
- confidence: Your confidence in this pairing (0-1)

Prioritize practical, complementary pairings that create a complete and balanced meal.
Consider appetizers, side dishes, desserts, and beverages."""
