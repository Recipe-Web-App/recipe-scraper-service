"""Enum for revision types.

This enum defines the types of revisions that can be made to a recipe.
"""

from enum import Enum


class RevisionTypeEnum(str, Enum):
    """Types of revisions that can be made to a recipe.

    Each member represents a supported revision type.
    """

    ADD = "ADD"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
