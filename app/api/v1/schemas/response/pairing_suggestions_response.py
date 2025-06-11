"""Pairing suggestions response schema.

Defines the Pydantic model for suggested pairings of ingredients or recipes.
"""

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.api.v1.schemas.common.pagination_params import PaginationParams
from app.api.v1.schemas.common.web_recipe import WebRecipe


class PairingSuggestionsResponse(BaseSchema):
    """Response model for pairing suggestions.

    Attributes:
        recipe_id (int): The ID of the recipe being evaluated for pairing.
        pairing_suggestions (list[WebRecipe]): A list of recommended pairing recipes.
        limit (int): The maximum number of items returned.
        offset (int): The offset used for pagination.
        count (int): The total number of available suggestions.
    """

    recipe_id: int = Field(
        ...,
        description="The ID of the recipe being evaluated for pairing.",
    )
    pairing_suggestions: list[WebRecipe] = Field(
        ...,
        description="A list of recommended pairing recipes.",
    )
    limit: int = Field(..., description="The maximum number of items returned.")
    offset: int = Field(..., description="The offset used for pagination.")
    count: int = Field(..., description="The total number of available suggestions.")

    @classmethod
    def from_all(
        cls,
        recipe_id: int,
        pairing_suggestions: list[WebRecipe],
        pagination: PaginationParams,
    ) -> "PairingSuggestionsResponse":
        """Create a paginated response for pairing suggestions.

        Args:
            recipe_id (int): The ID of the recipe for which suggestions are being made.
            pairing_suggestions (list[WebRecipe]): The full list of suggested recipes.
            pagination (PaginationParams): Pagination params for response control.

        Returns:
            PairingSuggestionsResponse: The paginated pairing suggestions response.
        """
        total = len(pairing_suggestions)
        if pagination.count_only:
            return cls(
                recipe_id=recipe_id,
                pairing_suggestions=[],
                limit=pagination.limit,
                offset=pagination.offset,
                count=total,
            )

        paginated = pairing_suggestions[
            pagination.offset : pagination.offset + pagination.limit
        ]
        return cls(
            recipe_id=recipe_id,
            pairing_suggestions=paginated,
            limit=pagination.limit,
            offset=pagination.offset,
            count=total,
        )
