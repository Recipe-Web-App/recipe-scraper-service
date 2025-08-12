"""Unit conversion utilities for ingredient measurements.

Provides functionality to convert between different units of measurement for proper
nutritional scaling calculations.
"""

from decimal import Decimal
from typing import ClassVar

from app.enums.ingredient_unit_enum import IngredientUnitEnum
from app.exceptions.custom_exceptions import IncompatibleUnitsError


class UnitConverter:
    """Utility class for converting between different ingredient measurement units."""

    # Base conversion factors to grams (for weight) and milliliters (for volume)
    _WEIGHT_CONVERSIONS: ClassVar[dict[IngredientUnitEnum, Decimal]] = {
        IngredientUnitEnum.G: Decimal(1),
        IngredientUnitEnum.KG: Decimal(1000),
        IngredientUnitEnum.OZ: Decimal("28.3495"),
        IngredientUnitEnum.LB: Decimal("453.592"),
    }

    _VOLUME_CONVERSIONS: ClassVar[dict[IngredientUnitEnum, Decimal]] = {
        IngredientUnitEnum.ML: Decimal(1),
        IngredientUnitEnum.L: Decimal(1000),
        IngredientUnitEnum.CUP: Decimal("236.588"),  # US cup
        IngredientUnitEnum.TBSP: Decimal("14.7868"),  # US tablespoon
        IngredientUnitEnum.TSP: Decimal("4.92892"),  # US teaspoon
    }

    # Units that don't have meaningful conversions (count-based)
    _COUNT_UNITS: ClassVar[set[IngredientUnitEnum]] = {
        IngredientUnitEnum.PIECE,
        IngredientUnitEnum.CLOVE,
        IngredientUnitEnum.SLICE,
        IngredientUnitEnum.PINCH,
        IngredientUnitEnum.CAN,
        IngredientUnitEnum.BOTTLE,
        IngredientUnitEnum.PACKET,
        IngredientUnitEnum.UNIT,
    }

    @classmethod
    def can_convert_between(
        cls,
        from_unit: IngredientUnitEnum,
        to_unit: IngredientUnitEnum,
    ) -> bool:
        """Check if conversion is possible between two units.

        Args:     from_unit: Source unit     to_unit: Target unit

        Returns:     bool: True if conversion is possible, False otherwise
        """
        # Same unit is always convertible
        if from_unit == to_unit:
            return True

        # Check if both are weight units
        if from_unit in cls._WEIGHT_CONVERSIONS and to_unit in cls._WEIGHT_CONVERSIONS:
            return True

        # Check if both are volume units
        if from_unit in cls._VOLUME_CONVERSIONS and to_unit in cls._VOLUME_CONVERSIONS:
            return True

        # Count units can only convert to the same count unit
        if from_unit in cls._COUNT_UNITS and to_unit in cls._COUNT_UNITS:
            return from_unit == to_unit

        return False

    @classmethod
    def convert_quantity(
        cls,
        quantity: Decimal,
        from_unit: IngredientUnitEnum,
        to_unit: IngredientUnitEnum,
    ) -> Decimal:
        """Convert a quantity from one unit to another.

        Args:     quantity: The quantity to convert     from_unit: Source unit to_unit:
        Target unit

        Returns:     Decimal: The converted quantity

        Raises:     IncompatibleUnitsError: If conversion is not possible between the
        units
        """
        if from_unit == to_unit:
            return quantity

        if not cls.can_convert_between(from_unit, to_unit):
            raise IncompatibleUnitsError(from_unit, to_unit)

        # Convert weight units
        if from_unit in cls._WEIGHT_CONVERSIONS and to_unit in cls._WEIGHT_CONVERSIONS:
            # Convert to base unit (grams) then to target unit
            base_quantity = quantity * cls._WEIGHT_CONVERSIONS[from_unit]
            return base_quantity / cls._WEIGHT_CONVERSIONS[to_unit]

        # Convert volume units
        if from_unit in cls._VOLUME_CONVERSIONS and to_unit in cls._VOLUME_CONVERSIONS:
            # Convert to base unit (milliliters) then to target unit
            base_quantity = quantity * cls._VOLUME_CONVERSIONS[from_unit]
            return base_quantity / cls._VOLUME_CONVERSIONS[to_unit]

        raise IncompatibleUnitsError(from_unit, to_unit)

    @classmethod
    def calculate_scale_factor(
        cls,
        old_quantity: Decimal,
        old_unit: IngredientUnitEnum,
        new_quantity: Decimal,
        new_unit: IngredientUnitEnum,
    ) -> Decimal:
        """Calculate the scale factor between two quantities with units.

        This method properly handles unit conversions when calculating the scaling
        factor for nutritional adjustments.

        Args:     old_quantity: Original quantity value     old_unit: Original unit
        new_quantity: New quantity value     new_unit: New unit

        Returns:     Decimal: Scale factor to apply to nutritional values

        Raises:     IncompatibleUnitsError: If conversion is not possible between the
        units
        """
        if not cls.can_convert_between(old_unit, new_unit):
            # Raise exception for incompatible units
            raise IncompatibleUnitsError(old_unit, new_unit)

        # Convert new quantity to the same unit as old quantity
        converted_new_quantity = cls.convert_quantity(new_quantity, new_unit, old_unit)

        # Calculate scale factor using converted quantities
        return converted_new_quantity / old_quantity
