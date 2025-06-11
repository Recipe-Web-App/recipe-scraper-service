"""Enum for ingredient units.

Defines the units of measurement that can be used for ingredients in recipes.
"""

from enum import Enum
from types import MappingProxyType


class IngredientUnitEnum(str, Enum):
    """Units of measurement for recipe ingredients."""

    G = "g"
    KG = "kg"
    OZ = "oz"
    LB = "lb"
    ML = "ml"
    L = "l"
    CUP = "cup"
    TBSP = "tbsp"
    TSP = "tsp"
    PIECE = "piece"
    CLOVE = "clove"
    SLICE = "slice"
    PINCH = "pinch"
    CAN = "can"
    BOTTLE = "bottle"
    PACKET = "packet"
    UNIT = "unit"

    __NORMALIZATION_MAP = MappingProxyType(
        {
            "grams": "g",
            "gram": "g",
            "kilograms": "kg",
            "kilogram": "kg",
            "ounces": "oz",
            "ounce": "oz",
            "pounds": "lb",
            "pound": "lb",
            "#": "lb",
            "#s": "lb",
            "milliliters": "ml",
            "milliliter": "ml",
            "liters": "l",
            "liter": "l",
            "cups": "cup",
            "tablespoons": "tbsp",
            "tablespoon": "tbsp",
            "teaspoons": "tsp",
            "teaspoon": "tsp",
            "pieces": "piece",
            "cloves": "clove",
            "slices": "slice",
            "pinches": "pinch",
            "cans": "can",
            "bottles": "bottle",
            "packets": "packet",
            "units": "unit",
        },
    )

    @classmethod
    def from_string(cls, unit_str: str) -> "IngredientUnitEnum | None":
        """Convert a string to the correct enum, normalizing plural/long forms."""
        if not unit_str:
            return None
        normalized = cls.__NORMALIZATION_MAP.get(unit_str.lower(), unit_str.lower())
        try:
            return cls(normalized)
        except ValueError:
            return None
