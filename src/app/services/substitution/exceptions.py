"""Exceptions for the substitution service.

Custom exceptions for handling substitution generation and caching errors.
"""

from __future__ import annotations


class SubstitutionError(Exception):
    """Base exception for substitution service errors."""

    def __init__(self, message: str, ingredient: str | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Error message.
            ingredient: Optional ingredient name related to the error.
        """
        self.ingredient = ingredient
        super().__init__(message)


class IngredientNotFoundError(SubstitutionError):
    """Raised when ingredient cannot be resolved.

    This occurs when the ingredient name/ID cannot be matched to
    any known ingredient in the system.
    """


class LLMGenerationError(SubstitutionError):
    """Raised when LLM fails to generate substitutions.

    This can occur when:
    - LLM service is unavailable
    - LLM response fails validation
    - LLM times out
    """

    def __init__(
        self,
        message: str,
        ingredient: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Error message.
            ingredient: Optional ingredient name.
            cause: Optional underlying exception.
        """
        self.cause = cause
        super().__init__(message, ingredient)


class CacheError(SubstitutionError):
    """Raised when cache operations fail.

    Cache errors should not propagate to the caller - the service
    falls back to LLM generation on cache failure.
    """
