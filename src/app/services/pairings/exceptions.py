"""Exceptions for the pairings service.

Custom exceptions for handling pairing generation and caching errors.
"""

from __future__ import annotations


class PairingsError(Exception):
    """Base exception for pairings service errors."""

    def __init__(self, message: str, recipe_id: int | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Error message.
            recipe_id: Optional recipe ID related to the error.
        """
        self.recipe_id = recipe_id
        super().__init__(message)


class LLMGenerationError(PairingsError):
    """Raised when LLM fails to generate pairings.

    This can occur when:
    - LLM service is unavailable
    - LLM response fails validation
    - LLM times out
    """

    def __init__(
        self,
        message: str,
        recipe_id: int | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Error message.
            recipe_id: Optional recipe ID.
            cause: Optional underlying exception.
        """
        self.cause = cause
        super().__init__(message, recipe_id)


class CacheError(PairingsError):
    """Raised when cache operations fail.

    Cache errors should not propagate to the caller - the service
    falls back to LLM generation on cache failure.
    """
