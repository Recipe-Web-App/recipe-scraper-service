"""Base class with Pydantic config for all schemas."""

from pydantic import BaseModel


class BaseSchema(BaseModel):
    """Base class with Pydantic config for all schemas.

    This class provides a common configuration for all Pydantic models used in the
    application, ensuring consistent behavior across all schemas.
    """

    class Config:
        """Pydantic configuration for BaseSchema."""

        from_attributes = True
        allow_population_by_field_name = True
        use_enum_values = True
        extra = "forbid"
        anystr_strip_whitespace = True
