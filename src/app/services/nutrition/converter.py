"""Unit conversion utilities for nutrition calculations.

Uses Pint library for weight/volume conversions and database lookups
for portion weights (count units and volume-to-gram conversions).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pint

from app.services.nutrition.constants import (
    FALLBACK_COUNT_WEIGHT_G,
    FALLBACK_DENSITY_G_PER_ML,
    PINT_UNIT_MAP,
    VOLUME_UNITS,
    WEIGHT_UNITS,
)
from app.services.nutrition.exceptions import ConversionError


if TYPE_CHECKING:
    from app.database.repositories.nutrition import NutritionRepository
    from app.schemas.enums import IngredientUnit
    from app.schemas.ingredient import Quantity


# Module-level unit registry (reused across instances)
_ureg: pint.UnitRegistry[pint.Quantity[float]] = pint.UnitRegistry()


class UnitConverter:
    """Converts ingredient quantities to grams.

    Uses Pint for weight-to-weight conversions and database lookups
    for volume-to-gram and count-to-gram conversions.

    Conversion Strategy:
        - Weight units (G, KG, OZ, LB): Pint (built-in conversions)
        - Volume units (ML, L, CUP, TBSP, TSP): Database lookup, fallback to 1 g/ml
        - Count units (PIECE, CLOVE, etc.): Database lookup, fallback to 100g

    Example:
        converter = UnitConverter(nutrition_repository)
        grams = await converter.to_grams(
            quantity=Quantity(amount=2, measurement=IngredientUnit.CUP),
            ingredient_name="flour"
        )
        # Returns Decimal("250.0") (from database: 1 cup flour = 125g)
    """

    def __init__(
        self,
        nutrition_repository: NutritionRepository | None = None,
    ) -> None:
        """Initialize the converter.

        Args:
            nutrition_repository: Repository for portion weight lookups.
                If None, will use fallback values for non-weight conversions.
        """
        self._nutrition_repo = nutrition_repository

    async def to_grams(
        self,
        quantity: Quantity,
        ingredient_name: str,
    ) -> Decimal:
        """Convert a quantity to grams.

        This is the single entry point for all conversions. It automatically
        detects the unit type and routes to the appropriate conversion logic.

        Args:
            quantity: The quantity to convert (amount + unit).
            ingredient_name: Ingredient name for portion weight lookup.

        Returns:
            Amount in grams.

        Raises:
            ConversionError: If conversion is not possible.
        """
        unit = quantity.measurement
        amount = Decimal(str(quantity.amount))

        # Weight units - Pint handles directly
        if unit in WEIGHT_UNITS:
            return self._convert_weight_to_grams(amount, unit)

        # Volume units - try database lookup first, then fallback
        if unit in VOLUME_UNITS:
            return await self._convert_volume_to_grams(amount, unit, ingredient_name)

        # Count units - try database lookup first, then fallback
        return await self._convert_count_to_grams(amount, unit, ingredient_name)

    def _convert_weight_to_grams(
        self,
        amount: Decimal,
        unit: IngredientUnit,
    ) -> Decimal:
        """Convert weight measurement to grams using Pint.

        Args:
            amount: Numeric amount.
            unit: Weight unit (G, KG, OZ, LB).

        Returns:
            Amount in grams.

        Raises:
            ConversionError: If unit is not recognized.
        """
        pint_unit = PINT_UNIT_MAP.get(unit)
        if pint_unit is None:
            msg = f"Unknown weight unit: {unit.value}"
            raise ConversionError(msg, unit=unit.value)

        try:
            pint_qty = float(amount) * _ureg(pint_unit)
            grams = pint_qty.to("gram").magnitude
            return Decimal(str(grams))
        except Exception as e:
            msg = f"Pint conversion failed for {unit.value}: {e}"
            raise ConversionError(msg, unit=unit.value) from e

    async def _convert_volume_to_grams(
        self,
        amount: Decimal,
        unit: IngredientUnit,
        ingredient_name: str,
    ) -> Decimal:
        """Convert volume measurement to grams.

        First attempts database lookup for portion weight (e.g., "1 cup flour = 125g").
        Falls back to volume conversion with 1 g/ml density (water equivalent).

        Args:
            amount: Numeric amount.
            unit: Volume unit (ML, L, CUP, TBSP, TSP).
            ingredient_name: Ingredient name for lookup.

        Returns:
            Amount in grams.
        """
        # Try database lookup for portion weight
        portion_weight = await self._get_portion_weight(ingredient_name, unit, amount)
        if portion_weight is not None:
            return portion_weight

        # Fallback: convert volume to ml, then assume 1 g/ml (water density)
        pint_unit = PINT_UNIT_MAP.get(unit)
        if pint_unit is None:
            msg = f"Unknown volume unit: {unit.value}"
            raise ConversionError(msg, ingredient=ingredient_name, unit=unit.value)

        try:
            pint_qty = float(amount) * _ureg(pint_unit)
            ml = Decimal(str(pint_qty.to("milliliter").magnitude))
            return ml * FALLBACK_DENSITY_G_PER_ML
        except Exception as e:
            msg = f"Pint conversion failed for {unit.value}: {e}"
            raise ConversionError(
                msg, ingredient=ingredient_name, unit=unit.value
            ) from e

    async def _convert_count_to_grams(
        self,
        amount: Decimal,
        unit: IngredientUnit,
        ingredient_name: str,
    ) -> Decimal:
        """Convert count-based measurement to grams.

        First attempts database lookup for portion weight (e.g., "1 medium apple = 182g").
        Falls back to 100g per unit.

        Args:
            amount: Numeric amount.
            unit: Count unit (PIECE, CLOVE, SLICE, etc.).
            ingredient_name: Ingredient name for lookup.

        Returns:
            Amount in grams.
        """
        # Try database lookup for portion weight
        portion_weight = await self._get_portion_weight(ingredient_name, unit, amount)
        if portion_weight is not None:
            return portion_weight

        # Fallback: 100g per unit
        return amount * FALLBACK_COUNT_WEIGHT_G

    async def _get_portion_weight(
        self,
        ingredient_name: str,
        unit: IngredientUnit,
        amount: Decimal,
    ) -> Decimal | None:
        """Look up portion weight from database.

        Args:
            ingredient_name: Ingredient name.
            unit: Unit of measurement.
            amount: Number of units.

        Returns:
            Total gram weight (amount * weight per unit), or None if not found.
        """
        if self._nutrition_repo is None:
            return None

        # Look up weight for 1 unit of this ingredient
        # Use str(unit) to handle both StrEnum members and plain strings
        weight_per_unit = await self._nutrition_repo.get_portion_weight(
            ingredient_name=ingredient_name.lower().strip(),
            unit=str(unit),
        )

        if weight_per_unit is None:
            return None

        return amount * weight_per_unit

    def is_weight_unit(self, unit: IngredientUnit) -> bool:
        """Check if a unit is a weight unit.

        Args:
            unit: Unit to check.

        Returns:
            True if the unit is a weight unit.
        """
        return unit in WEIGHT_UNITS

    def is_volume_unit(self, unit: IngredientUnit) -> bool:
        """Check if a unit is a volume unit.

        Args:
            unit: Unit to check.

        Returns:
            True if the unit is a volume unit.
        """
        return unit in VOLUME_UNITS

    def is_count_unit(self, unit: IngredientUnit) -> bool:
        """Check if a unit is a count-based unit.

        Args:
            unit: Unit to check.

        Returns:
            True if the unit is a count-based unit.
        """
        return unit not in WEIGHT_UNITS and unit not in VOLUME_UNITS
