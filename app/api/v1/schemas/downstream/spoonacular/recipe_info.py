"""Schema for Spoonacular recipe information."""

from pydantic import ConfigDict, Field, field_validator

from app.api.v1.schemas.base_schema import BaseSchema


class SpoonacularRecipeInfo(BaseSchema):
    """Represents a single recipe from Spoonacular API responses."""

    model_config = ConfigDict(extra="ignore")  # Allow extra fields from API response

    id: int = Field(..., description="Spoonacular recipe ID")
    title: str = Field(..., description="Recipe title")
    image: str | None = Field(default=None, description="Recipe image URL")
    image_type: str | None = Field(
        default=None,
        description="Image file type",
        alias="imageType",
    )
    summary: str | None = Field(default=None, description="Recipe summary")
    source_url: str | None = Field(
        default=None,
        description="Original recipe URL",
        alias="sourceUrl",
    )
    spoonacular_source_url: str | None = Field(
        default=None,
        description="Spoonacular recipe page URL",
        alias="spoonacularSourceUrl",
    )
    ready_in_minutes: int | None = Field(
        default=None,
        description="Preparation time in minutes",
        alias="readyInMinutes",
    )
    servings: int | None = Field(default=None, description="Number of servings")

    @field_validator("title", mode="before")
    @classmethod
    def validate_title(cls, v: str | None) -> str:
        """Validate and clean title field."""
        if not v:
            return "Untitled Recipe"
        return str(v).strip()

    @field_validator("source_url", "spoonacular_source_url", mode="before")
    @classmethod
    def validate_urls(cls, v: str | None) -> str | None:
        """Validate URL fields."""
        if v is None:
            return None
        url_str = str(v).strip()
        return url_str if url_str else None
