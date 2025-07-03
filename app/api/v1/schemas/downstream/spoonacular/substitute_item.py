"""Schema for Spoonacular substitute items."""

from pydantic import Field, field_validator

from app.api.v1.schemas.base_schema import BaseSchema


class SpoonacularSubstituteItem(BaseSchema):
    """Represents a single substitute item from Spoonacular API.

    This can be either a simple string or a more detailed object with name and
    description fields.
    """

    name: str | None = Field(
        default=None,
        description="Name of the substitute ingredient",
    )
    substitute: str | None = Field(
        default=None,
        description="Alternative field name for substitute ingredient",
    )
    description: str | None = Field(
        default=None,
        description="Description of the substitute with usage instructions",
    )

    @field_validator("name", "substitute", mode="before")
    @classmethod
    def validate_strings(cls, v: str | None) -> str | None:
        """Validate and clean string fields."""
        if v is None:
            return None
        if isinstance(v, str):
            return v.strip() if v.strip() else None
        return str(v).strip() if str(v).strip() else None
