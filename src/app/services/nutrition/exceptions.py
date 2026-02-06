"""Exceptions for the nutrition service.

Custom exceptions for handling nutrition lookup, caching, and conversion errors.
"""

from __future__ import annotations


class NutritionError(Exception):
    """Base exception for nutrition service errors."""

    def __init__(self, message: str, ingredient: str | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Error message.
            ingredient: Optional ingredient name related to the error.
        """
        self.ingredient = ingredient
        super().__init__(message)


class NutritionNotFoundError(NutritionError):
    """Raised when nutrition data is not found for an ingredient.

    This is not necessarily an error condition - the service handles missing
    data gracefully by including the ingredient in missing_ingredients list.
    """


class ConversionError(NutritionError):
    """Raised when unit conversion fails.

    This can occur when:
    - The unit is unknown
    - No fallback weight exists for a count-based unit
    - Volume-to-gram conversion lacks density data
    """

    def __init__(
        self,
        message: str,
        ingredient: str | None = None,
        unit: str | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Error message.
            ingredient: Optional ingredient name.
            unit: Optional unit that failed to convert.
        """
        self.unit = unit
        super().__init__(message, ingredient)


class CacheError(NutritionError):
    """Raised when cache operations fail.

    Cache errors should not propagate to the caller - the service
    falls back to database lookup on cache failure.
    """
