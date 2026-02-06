"""LLM prompt templates."""

from app.llm.prompts.base import BasePrompt
from app.llm.prompts.ingredient_parsing import (
    IngredientParsingPrompt,
    IngredientUnit,
    ParsedIngredient,
    ParsedIngredientList,
)
from app.llm.prompts.pairings import (
    PairingListResult,
    PairingResult,
    RecipePairingPrompt,
)
from app.llm.prompts.recipe_link_extraction import (
    ExtractedRecipeLink,
    ExtractedRecipeLinkList,
    RecipeLinkExtractionPrompt,
)


__all__ = [
    "BasePrompt",
    "ExtractedRecipeLink",
    "ExtractedRecipeLinkList",
    "IngredientParsingPrompt",
    "IngredientUnit",
    "PairingListResult",
    "PairingResult",
    "ParsedIngredient",
    "ParsedIngredientList",
    "RecipeLinkExtractionPrompt",
    "RecipePairingPrompt",
]
