"""Open Food Facts API client package.

Provides Tier 2 allergen lookup from the Open Food Facts database.
"""

from app.clients.open_food_facts.client import (
    OpenFoodFactsAllergen,
    OpenFoodFactsClient,
    OpenFoodFactsProduct,
)


__all__ = [
    "OpenFoodFactsAllergen",
    "OpenFoodFactsClient",
    "OpenFoodFactsProduct",
]
