"""Allergen service package.

Provides allergen information retrieval with tiered data source lookup.
"""

from app.services.allergen.exceptions import (
    AllergenError,
    AllergenNotFoundError,
    AllergenServiceError,
)
from app.services.allergen.service import AllergenService


__all__ = [
    "AllergenError",
    "AllergenNotFoundError",
    "AllergenService",
    "AllergenServiceError",
]
