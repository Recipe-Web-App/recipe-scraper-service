"""Schema for a recipe from the internet."""

from pydantic import BaseModel, Field


class WebRecipe(BaseModel):
    """Schema containing a recipe from the internet."""

    recipe_name: str = Field(
        ...,
        description="The name of the recipe as found online.",
    )
    url: str = Field(
        ...,
        description="The source URL where the recipe is located.",
    )
