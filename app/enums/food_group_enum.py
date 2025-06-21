"""Enumeration for food groups."""

from enum import Enum


class FoodGroupEnum(str, Enum):
    """Food group classifications based on OpenFoodFacts taxonomy.

    Categorizes ingredients into major food groups for nutritional analysis and dietary
    planning.
    """

    # Plant-based whole foods
    VEGETABLES = "VEGETABLES"
    FRUITS = "FRUITS"
    GRAINS = "GRAINS"
    LEGUMES = "LEGUMES"
    NUTS_SEEDS = "NUTS_SEEDS"

    # Animal products
    MEAT = "MEAT"
    POULTRY = "POULTRY"
    SEAFOOD = "SEAFOOD"
    DAIRY = "DAIRY"

    # Processed and manufactured foods
    BEVERAGES = "BEVERAGES"
    PROCESSED_FOODS = "PROCESSED_FOODS"

    # Fallback
    UNKNOWN = "UNKNOWN"
