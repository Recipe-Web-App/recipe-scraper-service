"""Constants for nutrition service configuration.

Contains:
- Cache configuration for nutrition data
- Unit type sets for classification (weight, volume, count)
- Fallback values for when database lookups fail
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

from app.schemas.enums import IngredientUnit


# =============================================================================
# Unit Type Classification
# =============================================================================
# Used to determine conversion strategy

WEIGHT_UNITS: Final[frozenset[IngredientUnit]] = frozenset(
    {
        IngredientUnit.G,
        IngredientUnit.KG,
        IngredientUnit.OZ,
        IngredientUnit.LB,
    }
)

VOLUME_UNITS: Final[frozenset[IngredientUnit]] = frozenset(
    {
        IngredientUnit.ML,
        IngredientUnit.L,
        IngredientUnit.CUP,
        IngredientUnit.TBSP,
        IngredientUnit.TSP,
    }
)

# Count units are anything not in weight or volume
# PIECE, CLOVE, SLICE, PINCH, CAN, BOTTLE, PACKET, UNIT


# =============================================================================
# Pint Unit Mappings
# =============================================================================
# Maps IngredientUnit to Pint unit strings

PINT_UNIT_MAP: Final[dict[IngredientUnit, str]] = {
    # Weight units
    IngredientUnit.G: "gram",
    IngredientUnit.KG: "kilogram",
    IngredientUnit.OZ: "ounce",
    IngredientUnit.LB: "pound",
    # Volume units
    IngredientUnit.ML: "milliliter",
    IngredientUnit.L: "liter",
    IngredientUnit.CUP: "cup",
    IngredientUnit.TBSP: "tablespoon",
    IngredientUnit.TSP: "teaspoon",
}


# =============================================================================
# Fallback Values
# =============================================================================
# Used when database portion lookup fails

# Default density for volume-to-weight (assumes water-like density)
FALLBACK_DENSITY_G_PER_ML: Final[Decimal] = Decimal("1.0")

# Default weight for count units when no portion data exists
FALLBACK_COUNT_WEIGHT_G: Final[Decimal] = Decimal("100.0")


# =============================================================================
# Cache Configuration
# =============================================================================

NUTRITION_CACHE_KEY_PREFIX: Final[str] = "nutrition"
NUTRITION_CACHE_TTL_SECONDS: Final[int] = 30 * 24 * 60 * 60  # 30 days
