"""Contains schema definition for fiber nutritional information."""

from decimal import Decimal

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.utils.aggregation_helpers import sum_decimal_optional


class Fibers(BaseSchema):
    """Contains fiber information for an ingredient.

    Attributes:
        fiber_g (Decimal | None): Total fiber content in grams, if available.
        soluble_fiber_g (Decimal | None): Soluble fiber in grams, if available.
        insoluble_fiber_g (Decimal | None): Insoluble fiber in grams, if available.
    """

    fiber_g: Decimal | None = Field(
        None,
        ge=0,
        description="Total fiber content in grams",
    )
    soluble_fiber_g: Decimal | None = Field(
        None,
        ge=0,
        description="Soluble fiber in grams",
    )
    insoluble_fiber_g: Decimal | None = Field(
        None,
        ge=0,
        description="Insoluble fiber in grams",
    )

    def __add__(self, other: "Fibers") -> "Fibers":
        """Combine fiber values from two entities.

        Args:
            other (Fibers): The other entity to add.

        Returns:
            Fibers: A sum of all fiber data.
        """
        return Fibers(
            fiber_g=sum_decimal_optional(
                self.fiber_g,
                other.fiber_g,
                "0.001",  # 3 decimal places for macro-nutrients
            ),
            soluble_fiber_g=sum_decimal_optional(
                self.soluble_fiber_g,
                other.soluble_fiber_g,
                "0.001",  # 3 decimal places for macro-nutrients
            ),
            insoluble_fiber_g=sum_decimal_optional(
                self.insoluble_fiber_g,
                other.insoluble_fiber_g,
                "0.001",  # 3 decimal places for macro-nutrients
            ),
        )
