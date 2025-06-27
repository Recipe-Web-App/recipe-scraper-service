"""Recommended substitutions response schema.

Defines the Pydantic model for ingredient or recipe substitution recommendations
returned in responses.
"""

from decimal import Decimal

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.api.v1.schemas.common.ingredient import Ingredient, Quantity
from app.api.v1.schemas.common.pagination_params import PaginationParams
from app.enums.ingredient_unit_enum import IngredientUnitEnum
from app.exceptions.custom_exceptions import IncompatibleUnitsError
from app.utils.unit_converter import UnitConverter


class ConversionRatio(BaseSchema):
    """Represents the conversion ratio between original and substitute ingredients.

    Attributes:
        ratio (float): The numeric conversion ratio (e.g., 1.0 for 1:1, 2.0 for 2:1).
        measurement (IngredientUnitEnum): The unit of measurement for the conversion.
    """

    ratio: float = Field(
        ...,
        description="The numeric conversion ratio from original to substitute.",
        ge=0,
    )
    measurement: IngredientUnitEnum = Field(
        ...,
        description="The unit of measurement for the conversion ratio.",
    )


class IngredientSubstitution(BaseSchema):
    """Represents a single substitution recommendation for an ingredient.

    Attributes:
        ingredient (str): The name of the suggested substitute ingredient.
        quantity (Quantity): The amount of the substitute to use.
        conversion_ratio (ConversionRatio): The conversion ratio between original
            and substitute.
    """

    ingredient: str = Field(
        ...,
        description="The name of the suggested substitute ingredient.",
    )
    quantity: Quantity | None = Field(
        default=None,
        description="The amount of the substitute ingredient to use.",
    )
    conversion_ratio: ConversionRatio = Field(
        ...,
        description="The conversion ratio from original to substitute ingredient.",
    )


class RecommendedSubstitutionsResponse(BaseSchema):
    """Response schema representing a list of substitutions for an ingredient.

    Attributes:
        ingredient (Ingredient): The original ingredient for which substitutions are
            recommended.
        recommended_substitutions (list[IngredientSubstitution]): A list of recommended
            substitutions.
        limit (int): The maximum number of recommendations returned.
        offset (int): The number of skipped recommendations from the beginning.
        count (int): The total number of recommendations available.
    """

    ingredient: Ingredient = Field(
        ...,
        description="The original ingredient to be substituted.",
    )
    recommended_substitutions: list[IngredientSubstitution] = Field(
        ...,
        description="List of recommended substitution options.",
    )
    limit: int = Field(50, description="The maximum number of substitutions to return.")
    offset: int = Field(0, description="The starting index for pagination of results.")
    count: int = Field(
        0,
        description="The total number of substitution recommendations available.",
    )

    @classmethod
    def from_all(
        cls,
        ingredient: Ingredient,
        recommended_substitutions: list[IngredientSubstitution],
        pagination: PaginationParams,
    ) -> "RecommendedSubstitutionsResponse":
        """Create a response with pagination applied to the list of all substitutions.

        Args:
            ingredient: The ingredient to be substituted.
            recommended_substitutions (list[IngredientSubstitution]): The complete list
                of substitutions.
            pagination (PaginationParams): Pagination params for response control.

        Returns:
            RecommendedSubstitutionsResponse: Paginated response with metadata.
        """
        total = len(recommended_substitutions)
        if pagination.count_only:
            return cls(
                ingredient=ingredient,
                recommended_substitutions=[],
                limit=pagination.limit,
                offset=pagination.offset,
                count=total,
            )

        paginated = recommended_substitutions[
            pagination.offset : pagination.offset + pagination.limit
        ]
        response = cls(
            ingredient=ingredient,
            recommended_substitutions=paginated,
            limit=pagination.limit,
            offset=pagination.offset,
            count=total,
        )
        if ingredient.quantity:
            response.adjust_substitute_quantities(ingredient.quantity)
        return response

    def adjust_substitute_quantities(self, adjustment_quantity: Quantity) -> None:
        """Calculate and set substitute quantities based on conversion ratios.

        Takes an original ingredient quantity and applies the conversion ratio
        for each substitute to calculate the required substitute amounts.
        The result quantities will be in the same unit as the original ingredient.

        Args:
            adjustment_quantity (Quantity): The quantity of the original
                ingredient that needs to be substituted.

        Note:
            This method modifies the recommended_substitutions in place by setting
            their quantity fields based on the conversion ratios, keeping the
            original unit of measurement.
        """
        for substitution in self.recommended_substitutions:
            try:
                # Convert original quantity to the conversion ratio's unit first
                converted_original_amount = UnitConverter.convert_quantity(
                    Decimal(str(adjustment_quantity.amount)),
                    adjustment_quantity.measurement,
                    substitution.conversion_ratio.measurement,
                )

                # Apply the conversion ratio
                substitute_amount_in_ratio_unit = converted_original_amount * Decimal(
                    str(substitution.conversion_ratio.ratio),
                )

                # Convert back to the original unit
                substitute_amount_in_original_unit = UnitConverter.convert_quantity(
                    substitute_amount_in_ratio_unit,
                    substitution.conversion_ratio.measurement,
                    adjustment_quantity.measurement,
                )

                # Create a new Quantity object for the substitute in original unit
                substitution.quantity = Quantity(
                    amount=float(substitute_amount_in_original_unit),
                    measurement=adjustment_quantity.measurement,
                )
            except IncompatibleUnitsError:
                # If conversion fails, fallback to direct ratio application
                # This handles cases where units are incompatible
                substitute_amount = (
                    adjustment_quantity.amount * substitution.conversion_ratio.ratio
                )
                substitution.quantity = Quantity(
                    amount=substitute_amount,
                    measurement=adjustment_quantity.measurement,
                )
