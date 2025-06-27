"""Spoonacular API schema models.

This package contains Pydantic models for parsing and validating responses from the
Spoonacular API service.
"""

from .recipe_search_response import (
    ParsedRecipeResult,
    SpoonacularRecipeInfo,
    SpoonacularRecipeSearchResponse,
    SpoonacularSimilarRecipesResponse,
)
from .substitutes_response import (
    ParsedSubstituteResult,
    SpoonacularSubstituteItem,
    SpoonacularSubstitutesResponse,
)

__all__ = [
    "ParsedRecipeResult",
    "ParsedSubstituteResult",
    "SpoonacularRecipeInfo",
    "SpoonacularRecipeSearchResponse",
    "SpoonacularSimilarRecipesResponse",
    "SpoonacularSubstituteItem",
    "SpoonacularSubstitutesResponse",
]
