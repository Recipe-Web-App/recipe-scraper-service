"""Custom exception classes.

Defines application-specific exceptions used to handle error cases with meaningful
messages.
"""

from app.enums.ingredient_unit_enum import IngredientUnitEnum


class IncompatibleUnitsError(ValueError):
    """Raised when attempting to convert between incompatible measurement units.

    This exception is raised when trying to perform unit conversions between units that
    cannot be meaningfully converted (e.g., grams to milliliters).
    """

    def __init__(
        self,
        from_unit: IngredientUnitEnum,
        to_unit: IngredientUnitEnum,
    ) -> None:
        """Initialize the exception with unit information.

        Args:
            from_unit: The source unit that cannot be converted
            to_unit: The target unit that cannot be converted to
        """
        self.from_unit = from_unit
        self.to_unit = to_unit
        super().__init__(f"Cannot convert between {from_unit} and {to_unit}")

    def get_from_unit(self) -> IngredientUnitEnum:
        """Get the source unit that caused the error.

        Returns:
            IngredientUnitEnum: The unit that conversion was attempted from.
        """
        return self.from_unit

    def get_to_unit(self) -> IngredientUnitEnum:
        """Get the target unit that caused the error.

        Returns:
            IngredientUnitEnum: The unit that conversion was attempted to.
        """
        return self.to_unit
