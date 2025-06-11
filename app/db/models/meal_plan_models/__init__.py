"""Meal Plan Models package initializer.

This package contains ORM models representing the meal plan data entities used in the
application.
"""

from .meal_plan import MealPlan
from .meal_plan_recipe import MealPlanRecipe

__all__ = [
    "MealPlan",
    "MealPlanRecipe",
]
