"""Pairings service package.

Provides LLM-powered recipe pairing recommendations based on flavor profiles
and cuisine types.
"""

from app.services.pairings.service import PairingsService, RecipeContext


__all__ = ["PairingsService", "RecipeContext"]
