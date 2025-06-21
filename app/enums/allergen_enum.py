"""Enumeration for common allergens."""

from enum import Enum


class AllergenEnum(str, Enum):
    """Enumeration of common allergens.

    Attributes:
        MILK (str): Contains milk/dairy.
        EGGS (str): Contains eggs.
        FISH (str): Contains fish.
        SHELLFISH (str): Contains shellfish.
        TREE_NUTS (str): Contains tree nuts.
        PEANUTS (str): Contains peanuts.
        WHEAT (str): Contains wheat.
        SOYBEANS (str): Contains soybeans.
        SESAME (str): Contains sesame.
        CELERY (str): Contains celery.
        MUSTARD (str): Contains mustard.
        LUPIN (str): Contains lupin.
        SULPHITES (str): Contains sulphites.
        ALMONDS (str): Contains almonds.
        CASHEWS (str): Contains cashews.
        HAZELNUTS (str): Contains hazelnuts.
        WALNUTS (str): Contains walnuts.
        GLUTEN (str): Contains gluten.
        COCONUT (str): Contains coconut.
        CORN (str): Contains corn.
        YEAST (str): Contains yeast.
        GELATIN (str): Contains gelatin.
        KIWI (str): Contains kiwi.
        PORK (str): Contains pork.
        BEEF (str): Contains beef.
        ALCOHOL (str): Contains alcohol.
        SULFUR_DIOXIDE (str): Contains sulfur dioxide.
        PHENYLALANINE (str): Contains phenylalanine.
        NONE (str): No allergens.
        UNKNOWN (str): Unknown allergens.
    """

    # FDA Major Allergens (Top 9)
    MILK = "MILK"
    EGGS = "EGGS"
    FISH = "FISH"
    SHELLFISH = "SHELLFISH"
    TREE_NUTS = "TREE_NUTS"
    PEANUTS = "PEANUTS"
    WHEAT = "WHEAT"
    SOYBEANS = "SOYBEANS"
    SESAME = "SESAME"

    # Additional EU Major Allergens
    CELERY = "CELERY"
    MUSTARD = "MUSTARD"
    LUPIN = "LUPIN"
    SULPHITES = "SULPHITES"

    # Tree Nut Specifics
    ALMONDS = "ALMONDS"
    CASHEWS = "CASHEWS"
    HAZELNUTS = "HAZELNUTS"
    WALNUTS = "WALNUTS"

    # Common Additional Allergens
    GLUTEN = "GLUTEN"
    COCONUT = "COCONUT"
    CORN = "CORN"
    YEAST = "YEAST"
    GELATIN = "GELATIN"
    KIWI = "KIWI"

    # Religious/Dietary
    PORK = "PORK"
    BEEF = "BEEF"
    ALCOHOL = "ALCOHOL"

    # Additives/Chemicals
    SULFUR_DIOXIDE = "SULFUR_DIOXIDE"
    PHENYLALANINE = "PHENYLALANINE"

    # Other
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"
