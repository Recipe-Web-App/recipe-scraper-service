"""Spoonacular API schema models.

This package contains Pydantic models for parsing and validating responses from the
Spoonacular API service.
"""

from .recipe_search_response import (
    SpoonacularRecipeInfo,
    SpoonacularRecipeSearchResponse,
    SpoonacularSimilarRecipesResponse,
)
from .substitutes_response import (
    SpoonacularSubstituteItem,
    SpoonacularSubstitutesResponse,
)

__all__ = [
    "SpoonacularRecipeInfo",
    "SpoonacularRecipeSearchResponse",
    "SpoonacularSimilarRecipesResponse",
    "SpoonacularSubstituteItem",
    "SpoonacularSubstitutesResponse",
]
