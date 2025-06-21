"""Contains schema definition for sugar nutritional information."""

from decimal import Decimal

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.utils.aggregation_helpers import sum_decimal_optional


class Sugars(BaseSchema):
    """Contains sugar information for an ingredient.

    Attributes:
        sugar_g (Decimal | None): Sugar content in grams, if available.
        added_sugars_g (Decimal | None): Added sugars content in grams, if available.
    """

    sugar_g: Decimal | None = Field(
        None,
        ge=0,
        description="Sugar content in grams",
    )
    added_sugars_g: Decimal | None = Field(
        None,
        ge=0,
        description="Added sugars in grams",
    )

    def __add__(self, other: "Sugars") -> "Sugars":
        """Combine sugar values from two entities.

        Args:
            other (Sugars): The other entity to add.

        Returns:
            Sugars: A sum of all sugar data.
        """
        return Sugars(
            sugar_g=sum_decimal_optional(
                self.sugar_g,
                other.sugar_g,
                "0.001",  # 3 decimal places for macronutrients
            ),
            added_sugars_g=sum_decimal_optional(
                self.added_sugars_g,
                other.added_sugars_g,
                "0.001",  # 3 decimal places for macronutrients
            ),
        )
