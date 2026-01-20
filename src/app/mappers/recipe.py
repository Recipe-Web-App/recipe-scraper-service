"""Recipe-related data mappers.

This module contains functions for transforming recipe data between
different representations (scraped, downstream service, API response).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas import (
    CreateRecipeResponse,
    Ingredient,
    Recipe,
    RecipeStep,
)
from app.services.recipe_management import (
    CreateRecipeIngredientRequest,
    CreateRecipeStepRequest,
    IngredientUnit,
)
from app.services.recipe_management import (
    CreateRecipeRequest as DownstreamRecipeRequest,
)


if TYPE_CHECKING:
    from app.llm.prompts import ParsedIngredient
    from app.services.recipe_management import RecipeResponse
    from app.services.scraping.models import ScrapedRecipe


def build_downstream_recipe_request(
    scraped: ScrapedRecipe,
    parsed_ingredients: list[ParsedIngredient],
) -> DownstreamRecipeRequest:
    """Build downstream recipe request from scraped and parsed data.

    Args:
        scraped: Raw scraped recipe data.
        parsed_ingredients: LLM-parsed ingredients.

    Returns:
        Request schema for downstream Recipe Management Service.
    """
    ingredients = [
        CreateRecipeIngredientRequest.model_validate(
            {
                "ingredientName": ing.name,
                "quantity": ing.quantity,
                "unit": IngredientUnit(ing.unit.value),
                "isOptional": ing.is_optional,
                "notes": ing.notes,
            }
        )
        for ing in parsed_ingredients
    ]

    steps = [
        CreateRecipeStepRequest.model_validate(
            {
                "stepNumber": idx + 1,
                "instruction": instruction,
            }
        )
        for idx, instruction in enumerate(scraped.instructions)
    ]

    servings = scraped.parse_servings() or 1.0

    return DownstreamRecipeRequest.model_validate(
        {
            "title": scraped.title,
            "description": scraped.description or "",
            "servings": servings,
            "preparationTime": scraped.prep_time,
            "cookingTime": scraped.cook_time,
            "ingredients": ingredients,
            "steps": steps,
        }
    )


def build_recipe_response(
    downstream_response: RecipeResponse,
    scraped: ScrapedRecipe,
    parsed_ingredients: list[ParsedIngredient],
) -> CreateRecipeResponse:
    """Build API response from downstream response and parsed data.

    Args:
        downstream_response: Response from Recipe Management Service.
        scraped: Original scraped recipe data.
        parsed_ingredients: Parsed ingredients.

    Returns:
        CreateRecipeResponse for the client.
    """
    ingredients = [
        Ingredient.model_validate(
            {
                "name": ing.name,
                "quantity": {
                    "amount": ing.quantity,
                    "measurement": ing.unit.value,
                },
            }
        )
        for ing in parsed_ingredients
    ]

    steps = [
        RecipeStep.model_validate(
            {
                "stepNumber": idx + 1,
                "instruction": instruction,
            }
        )
        for idx, instruction in enumerate(scraped.instructions)
    ]

    recipe = Recipe.model_validate(
        {
            "recipeId": downstream_response.id,
            "title": downstream_response.title,
            "description": scraped.description,
            "originUrl": scraped.source_url,
            "servings": scraped.parse_servings(),
            "preparationTime": scraped.prep_time,
            "cookingTime": scraped.cook_time,
            "ingredients": ingredients,
            "steps": steps,
        }
    )

    return CreateRecipeResponse(recipe=recipe)
