"""Enum for recipe difficulty levels.

Defines the levels of difficulty that can be given to a recipe.
"""

from enum import Enum


class DifficultyLevelEnum(str, Enum):
    """Difficulty levels for recipes.

    Each member represents a supported difficulty level for a recipe.
    """

    BEGINNER = "BEGINNER"
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    EXPERT = "EXPERT"
