"""Enum for meal types.

This enum defines the types of meals that can be associated with a recipe.
"""

from enum import Enum


class MealTypeEnum(str, Enum):
    """Types of meals that can be associated with a recipe.

    Each member represents a supported meal type.
    """

    BREAKFAST = "BREAKFAST"
    LUNCH = "LUNCH"
    DINNER = "DINNER"
    SNACK = "SNACK"
    DESSERT = "DESSERT"
