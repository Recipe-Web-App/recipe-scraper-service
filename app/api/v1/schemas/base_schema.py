"""Base class with Pydantic config for all schemas."""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BaseSchema(BaseModel):
    """Base class with Pydantic config for all schemas.

    This class provides a common configuration for all Pydantic models used in the
    application, ensuring consistent behavior across all schemas.

    Configured to:
    - Convert snake_case Python fields to camelCase in JSON serialization
    - Accept both camelCase and snake_case during deserialization
    - Use enum values instead of enum names
    - Forbid extra fields for strict validation
    """

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
        use_enum_values=True,
        extra="forbid",
        str_strip_whitespace=True,
    )
