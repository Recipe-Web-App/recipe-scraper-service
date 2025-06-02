"""Enum for ingredient units.

Defines the units of measurement that can be used for ingredients in recipes.
"""

from enum import Enum


class IngredientUnitEnum(str, Enum):
    """Units of measurement for recipe ingredients.

    Each member represents a supported unit for ingredient quantities in recipes.
    """

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
