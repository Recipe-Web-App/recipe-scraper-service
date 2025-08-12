"""Contains schema definition for fat nutritional information."""

from decimal import Decimal

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.utils.aggregation_helpers import sum_decimal_optional


class Fats(BaseSchema):
    """Contains fat information for an ingredient.

    Attributes:     fat_g (Decimal | None): Total fat content in grams, if available.
    saturated_fat_g (Decimal | None): Saturated fat content in grams, if available.
    monounsaturated_fat_g (Decimal | None): Monounsaturated fat content in grams, if
    available.     polyunsaturated_fat_g (Decimal | None): Polyunsaturated fat content
    in grams, if         available.     omega_3_fat_g (Decimal | None): Omega-3 fat
    content in grams, if available.     omega_6_fat_g (Decimal | None): Omega-6 fat
    content in grams, if available.     omega_9_fat_g (Decimal | None): Omega-9 fat
    content in grams, if available.     trans_fat_g (Decimal | None): Trans fat content
    in grams, if available.
    """

    fat_g: Decimal | None = Field(
        None,
        ge=0,
        description="Fat content in grams",
    )
    saturated_fat_g: Decimal | None = Field(
        None,
        ge=0,
        description="Saturated fat content in grams",
    )
    monounsaturated_fat_g: Decimal | None = Field(
        None,
        ge=0,
        description="Monounsaturated fat content in grams",
    )
    polyunsaturated_fat_g: Decimal | None = Field(
        None,
        ge=0,
        description="Polyunsaturated fat content in grams",
    )
    omega_3_fat_g: Decimal | None = Field(
        None,
        ge=0,
        description="Omega-3 fat content in grams",
    )
    omega_6_fat_g: Decimal | None = Field(
        None,
        ge=0,
        description="Omega-6 fat content in grams",
    )
    omega_9_fat_g: Decimal | None = Field(
        None,
        ge=0,
        description="Omega-9 fat content in grams",
    )
    trans_fat_g: Decimal | None = Field(
        None,
        ge=0,
        description="Trans fat content in grams",
    )

    def __add__(self, other: "Fats") -> "Fats":
        """Combine fat values from two entities.

        Args:     other (Fats): The other entity to add.

        Returns:     Fats: A sum of all fat data.
        """
        return Fats(
            fat_g=sum_decimal_optional(self.fat_g, other.fat_g, "0.001"),
            saturated_fat_g=sum_decimal_optional(
                self.saturated_fat_g,
                other.saturated_fat_g,
                "0.001",
            ),
            monounsaturated_fat_g=sum_decimal_optional(
                self.monounsaturated_fat_g,
                other.monounsaturated_fat_g,
                "0.001",
            ),
            polyunsaturated_fat_g=sum_decimal_optional(
                self.polyunsaturated_fat_g,
                other.polyunsaturated_fat_g,
                "0.001",
            ),
            omega_3_fat_g=sum_decimal_optional(
                self.omega_3_fat_g,
                other.omega_3_fat_g,
                "0.001",
            ),
            omega_6_fat_g=sum_decimal_optional(
                self.omega_6_fat_g,
                other.omega_6_fat_g,
                "0.001",
            ),
            omega_9_fat_g=sum_decimal_optional(
                self.omega_9_fat_g,
                other.omega_9_fat_g,
                "0.001",
            ),
            trans_fat_g=sum_decimal_optional(
                self.trans_fat_g,
                other.trans_fat_g,
                "0.001",
            ),
        )
