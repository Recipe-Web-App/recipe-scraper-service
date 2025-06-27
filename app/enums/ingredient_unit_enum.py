"""Enum for ingredient units.

Defines the units of measurement that can be used for ingredients in recipes.
"""

from enum import Enum
from types import MappingProxyType


class IngredientUnitEnum(str, Enum):
    """Units of measurement for recipe ingredients."""

    G = "G"
    KG = "KG"
    OZ = "OZ"
    LB = "LB"
    ML = "ML"
    L = "L"
    CUP = "CUP"
    TBSP = "TBSP"
    TSP = "TSP"
    PIECE = "PIECE"
    CLOVE = "CLOVE"
    SLICE = "SLICE"
    PINCH = "PINCH"
    CAN = "CAN"
    BOTTLE = "BOTTLE"
    PACKET = "PACKET"
    UNIT = "UNIT"

    __NORMALIZATION_MAP = MappingProxyType(
        {
            "g": "G",
            "grams": "G",
            "gram": "G",
            "kg": "KG",
            "kilograms": "KG",
            "kilogram": "KG",
            "oz": "OZ",
            "ounces": "OZ",
            "ounce": "OZ",
            "lb": "LB",
            "pounds": "LB",
            "pound": "LB",
            "#": "LB",
            "#s": "LB",
            "ml": "ML",
            "milliliters": "ML",
            "milliliter": "ML",
            "l": "L",
            "liters": "L",
            "liter": "L",
            "cup": "CUP",
            "cups": "CUP",
            "tbsp": "TBSP",
            "tbs": "TBSP",
            "tablespoons": "TBSP",
            "tablespoon": "TBSP",
            "tsp": "TSP",
            "teaspoons": "TSP",
            "teaspoon": "TSP",
            "piece": "PIECE",
            "pieces": "PIECE",
            "clove": "CLOVE",
            "cloves": "CLOVE",
            "slice": "SLICE",
            "slices": "SLICE",
            "pinch": "PINCH",
            "pinches": "PINCH",
            "can": "CAN",
            "cans": "CAN",
            "bottle": "BOTTLE",
            "bottles": "BOTTLE",
            "packet": "PACKET",
            "packets": "PACKET",
            "unit": "UNIT",
            "units": "UNIT",
        },
    )

    @classmethod
    def from_string(cls, unit_str: str) -> "IngredientUnitEnum | None":
        """Convert a string to the correct enum, normalizing plural/long forms."""
        if not unit_str:
            return None
        normalized = cls.__NORMALIZATION_MAP.get(unit_str.lower(), unit_str.upper())
        try:
            return cls(normalized)
        except ValueError:
            return None

    @classmethod
    def find_unit_in_text(cls, text: str) -> "IngredientUnitEnum":
        """Find the most appropriate unit from text description.

        This method searches for unit patterns in the provided text and returns
        the first matching unit found, or UNIT as default.

        Args:
            text: Text that may contain unit information

        Returns:
            IngredientUnitEnum: The most appropriate unit (defaults to UNIT)
        """
        if not text:
            return cls.UNIT

        text_lower = text.lower()

        # Check all normalization patterns to find matches
        # Sort by length (longest first) to match more specific terms first
        sorted_patterns = sorted(
            cls.__NORMALIZATION_MAP.items(),
            key=lambda x: len(x[0]),
            reverse=True,
        )

        for pattern, unit_value in sorted_patterns:
            if pattern in text_lower:
                try:
                    return cls(unit_value)
                except ValueError:
                    continue

        # Default to UNIT if no specific unit is found
        return cls.UNIT
