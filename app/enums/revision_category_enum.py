"""Enum for revision categories.

This enum defines the entities that revisions can be made on in a recipe.
"""

from enum import Enum


class RevisionCategoryEnum(str, Enum):
    """Entities that can be revised in a recipe.

    Each member represents a category of recipe revision.
    """

    INGREDIENT = "INGREDIENT"
    STEP = "STEP"
