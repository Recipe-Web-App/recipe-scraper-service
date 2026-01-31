"""Allergen service exceptions."""

from __future__ import annotations


class AllergenError(Exception):
    """Base exception for allergen service errors."""


class AllergenNotFoundError(AllergenError):
    """Raised when allergen data is not found for an ingredient."""

    def __init__(self, ingredient: str) -> None:
        self.ingredient = ingredient
        super().__init__(f"No allergen data found for ingredient: {ingredient}")


class AllergenServiceError(AllergenError):
    """Raised when the allergen service encounters an error."""
