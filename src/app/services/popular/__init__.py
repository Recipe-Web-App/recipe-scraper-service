"""Popular recipes aggregation service.

This package provides functionality for fetching and aggregating
popular recipes from multiple configurable sources with dynamic
engagement metrics extraction and cross-source scoring.
"""

from app.services.popular.exceptions import (
    PopularRecipesError,
    PopularRecipesFetchError,
    PopularRecipesParseError,
)
from app.services.popular.llm_extraction import RecipeLinkExtractor
from app.services.popular.service import PopularRecipesService


__all__ = [
    "PopularRecipesError",
    "PopularRecipesFetchError",
    "PopularRecipesParseError",
    "PopularRecipesService",
    "RecipeLinkExtractor",
]
