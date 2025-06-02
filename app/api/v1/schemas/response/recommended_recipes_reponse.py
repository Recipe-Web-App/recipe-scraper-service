"""Popular recipes response schema.

Defines the Pydantic model for popular recipes returned in response payloads.
"""

from pydantic import BaseModel, Field

from app.schemas.common.pagination_params import PaginationParams
from app.schemas.common.web_recipe import WebRecipe


class PopularRecipesResponse(BaseModel):
    """Response schema representing a list of popular recipes from the internet.

    Attributes:
        recipes (list[PopularRecipe]): The list of popular recipes, sliced based
            on the given offset and limit.
        limit (int): The maximum number of recipes to return.
        offset (int): The starting index from which to return recipes.
      count (int): The total number of recipes before applying pagination.
    """

    recipes: list[WebRecipe] = Field(
        ...,
        description="Paginated recipes list.",
    )
    limit: int = Field(..., description="Max number of recipes returned.")
    offset: int = Field(..., description="Start index of recipes.")
    count: int = Field(..., description="Total number of available recipes.")

    @classmethod
    def from_all(
        cls,
        recipes: list[WebRecipe],
        pagination: PaginationParams,
    ) -> "PopularRecipesResponse":
        """Create a response with pagination applied to the list of all recipes.

        Args:
            recipes (list[PopularRecipe]): The complete list of recipes.
            pagination (PaginationParams): Pagination params for response control.

        Returns:
            PopularRecipesResponse: Paginated response with metadata.
        """
        total = len(recipes)
        if pagination.count_only:
            return cls(
                recipes=[],
                limit=pagination.limit,
                offset=pagination.offset,
                count=total,
            )

        paginated = recipes[pagination.offset : pagination.offset + pagination.limit]
        return cls(
            recipes=paginated,
            limit=pagination.limit,
            offset=pagination.offset,
            count=total,
        )
