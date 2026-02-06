"""Exceptions for the shopping service.

Custom exceptions for handling pricing lookup, caching, and calculation errors.
"""

from __future__ import annotations


class ShoppingServiceError(Exception):
    """Base exception for shopping service errors."""

    def __init__(self, message: str, ingredient_id: int | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Error message.
            ingredient_id: Optional ingredient ID related to the error.
        """
        self.ingredient_id = ingredient_id
        super().__init__(message)


class PriceNotAvailableError(ShoppingServiceError):
    """Raised when pricing data is not available for an ingredient.

    This occurs when neither Tier 1 (direct pricing) nor Tier 2 (food group)
    lookups return pricing data. The service handles this gracefully by
    returning null for estimated_price.
    """


class IngredientNotFoundError(ShoppingServiceError):
    """Raised when the ingredient cannot be found in the recipe management service."""


class CacheError(ShoppingServiceError):
    """Raised when cache operations fail.

    Cache errors should not propagate to the caller - the service
    falls back to database lookup on cache failure.
    """
