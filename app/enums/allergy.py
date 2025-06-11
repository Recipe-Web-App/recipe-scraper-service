"""Enumeration for common allergens."""

from enum import Enum


class Allergy(str, Enum):
    """Enumeration of common allergens.

    Attributes:
        GLUTEN (str): Contains gluten.
        PEANUTS (str): Contains peanuts.
        TREE_NUTS (str): Contains tree nuts.
        DAIRY (str): Contains dairy.
        SOY (str): Contains soy.
        EGG (str): Contains egg.
        FISH (str): Contains fish.
        SHELLFISH (str): Contains shellfish.
        SESAME (str): Contains sesame.
        MUSTARD (str): Contains mustard.
        SULFITES (str): Contains sulfites.
    """

    GLUTEN = "gluten"
    PEANUTS = "peanuts"
    TREE_NUTS = "tree_nuts"
    DAIRY = "dairy"
    SOY = "soy"
    EGG = "egg"
    FISH = "fish"
    SHELLFISH = "shellfish"
    SESAME = "sesame"
    MUSTARD = "mustard"
    SULFITES = "sulfites"
