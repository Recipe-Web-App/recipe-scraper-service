"""Contains schema definition for mineral nutritional information."""

from decimal import Decimal

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.utils.aggregation_helpers import sum_decimal_optional


class Minerals(BaseSchema):
    """Contains mineral information for an ingredient.

    Attributes:
        calcium_mg (Decimal | None): Calcium in milligrams, if available.
        iron_mg (Decimal | None): Iron in milligrams, if available.
        magnesium_mg (Decimal | None): Magnesium in milligrams, if available.
        potassium_mg (Decimal | None): Potassium in milligrams, if available.
        sodium_mg (Decimal | None): Sodium in milligrams, if available.
        zinc_mg (Decimal | None): Zinc in milligrams, if available.
    """

    calcium_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Calcium in milligrams",
    )
    iron_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Iron in milligrams",
    )
    magnesium_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Magnesium in milligrams",
    )
    potassium_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Potassium in milligrams",
    )
    sodium_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Sodium in milligrams",
    )
    zinc_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Zinc in milligrams",
    )

    def __add__(self, other: "Minerals") -> "Minerals":
        """Combine all mineral values from to entities.

        Args:
            other (Minerals): The other entity to add.

        Returns:
            Minerals: A sum of all mineral data.
        """
        return Minerals(
            calcium_mg=sum_decimal_optional(
                self.calcium_mg,
                other.calcium_mg,
                "0.000001",  # 6 decimal places for minerals
            ),
            iron_mg=sum_decimal_optional(
                self.iron_mg,
                other.iron_mg,
                "0.000001",  # 6 decimal places for minerals
            ),
            magnesium_mg=sum_decimal_optional(
                self.magnesium_mg,
                other.magnesium_mg,
                "0.000001",  # 6 decimal places for minerals
            ),
            potassium_mg=sum_decimal_optional(
                self.potassium_mg,
                other.potassium_mg,
                "0.000001",  # 6 decimal places for minerals
            ),
            sodium_mg=sum_decimal_optional(
                self.sodium_mg,
                other.sodium_mg,
                "0.000001",  # 6 decimal places for minerals
            ),
            zinc_mg=sum_decimal_optional(
                self.zinc_mg,
                other.zinc_mg,
                "0.000001",  # 6 decimal places for minerals
            ),
        )
