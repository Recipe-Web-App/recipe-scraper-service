"""Contains schema definition for vitamin nutritional information."""

from decimal import Decimal

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.utils.aggregation_helpers import sum_decimal_optional


class Vitamins(BaseSchema):
    """Contains vitamin information for an ingredient.

    Attributes:     vitamin_a_mg (Decimal | None): Vitamin A in milligrams, if
    available.     vitamin_b6_mg (Decimal | None): Vitamin B6 in milligrams, if
    available.     vitamin_b12_mg (Decimal | None): Vitamin B12 in milligrams, if
    available.     vitamin_c_mg (Decimal | None): Vitamin C in milligrams, if available.
    vitamin_d_mg (Decimal | None): Vitamin D in milligrams, if available. vitamin_e_mg
    (Decimal | None): Vitamin E in milligrams, if available. vitamin_k_mg (Decimal |
    None): Vitamin K in milligrams, if available.
    """

    vitamin_a_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Vitamin A in milligrams",
    )
    vitamin_b6_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Vitamin B6 in milligrams",
    )
    vitamin_b12_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Vitamin B12 in milligrams",
    )
    vitamin_c_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Vitamin C in milligrams",
    )
    vitamin_d_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Vitamin D in milligrams",
    )
    vitamin_e_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Vitamin E in milligrams",
    )
    vitamin_k_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Vitamin K in milligrams",
    )

    def __add__(self, other: "Vitamins") -> "Vitamins":
        """Combine all vitamin values from to entities.

        Args:     other (Vitamins): The other entity to add.

        Returns:     Vitamins: A sum of all vitamin data.
        """
        return Vitamins(
            vitamin_a_mg=sum_decimal_optional(
                self.vitamin_a_mg,
                other.vitamin_a_mg,
                "0.000001",  # 6 decimal places for vitamins
            ),
            vitamin_b6_mg=sum_decimal_optional(
                self.vitamin_b6_mg,
                other.vitamin_b6_mg,
                "0.000001",  # 6 decimal places for vitamins
            ),
            vitamin_b12_mg=sum_decimal_optional(
                self.vitamin_b12_mg,
                other.vitamin_b12_mg,
                "0.000001",  # 6 decimal places for vitamins
            ),
            vitamin_c_mg=sum_decimal_optional(
                self.vitamin_c_mg,
                other.vitamin_c_mg,
                "0.000001",  # 6 decimal places for vitamins
            ),
            vitamin_d_mg=sum_decimal_optional(
                self.vitamin_d_mg,
                other.vitamin_d_mg,
                "0.000001",  # 6 decimal places for vitamins
            ),
            vitamin_e_mg=sum_decimal_optional(
                self.vitamin_e_mg,
                other.vitamin_e_mg,
                "0.000001",  # 6 decimal places for vitamins
            ),
            vitamin_k_mg=sum_decimal_optional(
                self.vitamin_k_mg,
                other.vitamin_k_mg,
                "0.000001",  # 6 decimal places for vitamins
            ),
        )
