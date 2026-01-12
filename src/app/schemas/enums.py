"""Enumeration types for recipe scraper schemas.

This module contains all enum definitions used across the API schemas.
"""

from __future__ import annotations

from enum import StrEnum


class IngredientUnit(StrEnum):
    """Units of measurement for recipe ingredients."""

    # Weight
    G = "G"
    KG = "KG"
    OZ = "OZ"
    LB = "LB"
    # Volume
    ML = "ML"
    L = "L"
    CUP = "CUP"
    TBSP = "TBSP"
    TSP = "TSP"
    # Count/Quantity
    PIECE = "PIECE"
    CLOVE = "CLOVE"
    SLICE = "SLICE"
    PINCH = "PINCH"
    CAN = "CAN"
    BOTTLE = "BOTTLE"
    PACKET = "PACKET"
    UNIT = "UNIT"


class Allergen(StrEnum):
    """Common allergens for ingredient classification."""

    # Major allergens
    MILK = "MILK"
    EGGS = "EGGS"
    FISH = "FISH"
    SHELLFISH = "SHELLFISH"
    TREE_NUTS = "TREE_NUTS"
    PEANUTS = "PEANUTS"
    WHEAT = "WHEAT"
    SOYBEANS = "SOYBEANS"
    SESAME = "SESAME"
    # Additional allergens
    CELERY = "CELERY"
    MUSTARD = "MUSTARD"
    LUPIN = "LUPIN"
    SULPHITES = "SULPHITES"
    # Specific nuts
    ALMONDS = "ALMONDS"
    CASHEWS = "CASHEWS"
    HAZELNUTS = "HAZELNUTS"
    WALNUTS = "WALNUTS"
    # Other
    GLUTEN = "GLUTEN"
    COCONUT = "COCONUT"
    CORN = "CORN"
    YEAST = "YEAST"
    GELATIN = "GELATIN"
    KIWI = "KIWI"
    PORK = "PORK"
    BEEF = "BEEF"
    ALCOHOL = "ALCOHOL"
    SULFUR_DIOXIDE = "SULFUR_DIOXIDE"
    PHENYLALANINE = "PHENYLALANINE"
    # Special values
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"


class FoodGroup(StrEnum):
    """Food group classifications for nutritional analysis."""

    VEGETABLES = "VEGETABLES"
    FRUITS = "FRUITS"
    GRAINS = "GRAINS"
    LEGUMES = "LEGUMES"
    NUTS_SEEDS = "NUTS_SEEDS"
    MEAT = "MEAT"
    POULTRY = "POULTRY"
    SEAFOOD = "SEAFOOD"
    DAIRY = "DAIRY"
    BEVERAGES = "BEVERAGES"
    PROCESSED_FOODS = "PROCESSED_FOODS"
    UNKNOWN = "UNKNOWN"


class Difficulty(StrEnum):
    """Recipe difficulty levels."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class NutriscoreGrade(StrEnum):
    """Nutri-Score letter grades (A-E)."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


class HealthStatus(StrEnum):
    """Health check status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ReadinessStatus(StrEnum):
    """Readiness probe status values."""

    READY = "ready"
    DEGRADED = "degraded"
