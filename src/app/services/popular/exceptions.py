"""Exceptions for the popular recipes service.

This module defines custom exceptions for handling errors during
popular recipe fetching, parsing, and aggregation.
"""

from __future__ import annotations


class PopularRecipesError(Exception):
    """Base exception for popular recipes service errors."""

    def __init__(self, message: str, source: str | None = None) -> None:
        self.source = source
        super().__init__(message)


class PopularRecipesFetchError(PopularRecipesError):
    """Raised when fetching a source page fails.

    This includes HTTP errors, timeouts, and network failures.
    """

    def __init__(
        self,
        message: str,
        source: str | None = None,
        status_code: int | None = None,
    ) -> None:
        self.status_code = status_code
        super().__init__(message, source)


class PopularRecipesParseError(PopularRecipesError):
    """Raised when parsing HTML content fails.

    This includes malformed HTML, missing expected elements,
    and extraction failures.
    """
