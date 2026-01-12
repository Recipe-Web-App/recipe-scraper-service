"""Base schema configuration for all Pydantic models.

This module provides centralized base classes with consistent configuration.
All API and downstream schemas should inherit from the appropriate base class.

Usage:
    - APIRequest: For incoming API request bodies
    - APIResponse: For outgoing API response bodies
    - DownstreamRequest: For requests sent to external services
    - DownstreamResponse: For responses received from external services
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _BaseSchema(BaseModel):
    """Private base schema with common configuration.

    Do not use directly - inherit from one of the public subclasses.
    """

    model_config = ConfigDict(
        # Alias configuration for camelCase serialization
        alias_generator=to_camel,
        populate_by_name=True,  # Accept both snake_case and camelCase
        # Serialization settings
        ser_json_bytes="base64",
        ser_json_timedelta="float",
        use_enum_values=True,
        # Validation settings
        validate_default=True,
        validate_assignment=True,
        # Always serialize to camelCase
        serialize_by_alias=True,
    )


class APIRequest(_BaseSchema):
    """Base class for incoming API request schemas.

    Configured to ignore extra fields - clients may send additional
    properties that we don't recognize, and that's okay.
    """

    model_config = ConfigDict(
        extra="ignore",
    )


class APIResponse(_BaseSchema):
    """Base class for outgoing API response schemas.

    Configured to forbid extra fields - we should only return
    properties that are explicitly defined in the schema.
    """

    model_config = ConfigDict(
        extra="forbid",
    )


class DownstreamRequest(_BaseSchema):
    """Base class for requests sent to external services.

    Configured to forbid extra fields - we should only send
    properties that we explicitly intend to send.
    """

    model_config = ConfigDict(
        extra="forbid",
    )


class DownstreamResponse(_BaseSchema):
    """Base class for responses received from external services.

    Configured to ignore extra fields - upstream services may add
    new properties, and we don't want that to break our parsing.
    """

    model_config = ConfigDict(
        extra="ignore",
    )
