"""Schema for a recipe from the internet."""

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema


class WebRecipe(BaseSchema):
    """Schema containing a recipe from the internet."""

    recipe_name: str = Field(
        ...,
        description="The name of the recipe as found online.",
    )
    url: str = Field(
        ...,
        description="The source URL where the recipe is located.",
    )
