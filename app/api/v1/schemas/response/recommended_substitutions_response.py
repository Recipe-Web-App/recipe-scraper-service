"""Recommended substitutions response schema.

Defines the Pydantic model for ingredient or recipe substitution recommendations
returned in responses.
"""

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.api.v1.schemas.common.ingredient import Ingredient, Quantity
from app.api.v1.schemas.common.pagination_params import PaginationParams


class IngredientSubstitution(BaseSchema):
    """Represents a single substitution recommendation for an ingredient.

    Attributes:
        ingredient (str): The name of the suggested substitute ingredient.
        quantity (Quantity): The amount of the substitute to use.
    """

    ingredient: str = Field(
        ...,
        description="The name of the suggested substitute ingredient.",
    )
    quantity: Quantity = Field(
        ...,
        description="The amount of the substitute ingredient to use.",
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
        return cls(
            ingredient=ingredient,
            recommended_substitutions=paginated,
            limit=pagination.limit,
            offset=pagination.offset,
            count=total,
        )
