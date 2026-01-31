"""Constants for allergen service configuration."""

from __future__ import annotations

from typing import Final


# Cache Configuration
ALLERGEN_CACHE_KEY_PREFIX: Final[str] = "allergen"
ALLERGEN_CACHE_TTL_SECONDS: Final[int] = 30 * 24 * 60 * 60  # 30 days

# Recipe allergen cache (shorter TTL since recipe ingredients may change)
RECIPE_ALLERGEN_CACHE_KEY_PREFIX: Final[str] = "recipe_allergen"
RECIPE_ALLERGEN_CACHE_TTL_SECONDS: Final[int] = 7 * 24 * 60 * 60  # 7 days

# Data source confidence scores
CONFIDENCE_USDA: Final[float] = 1.0
CONFIDENCE_OPEN_FOOD_FACTS: Final[float] = 0.95
CONFIDENCE_LLM_INFERRED: Final[float] = 0.75
