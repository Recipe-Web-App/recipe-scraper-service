"""Reusable model for pagination query parameters."""

from typing import Annotated

from fastapi import Query
from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema


class PaginationParams(BaseSchema):
    """Parameters for controlling pagination in API requests.

    Attributes:     limit (int | None): Number of items per page.         Defaults to
    50.         Must be greater than or equal to 1.         Optional; if omitted,
    defaults to 50.     offset (int | None): Number of items to skip before starting to
    collect the         result set.         Defaults to 0.         Must be greater than
    or equal to 0.         Optional; if omitted, defaults to 0.     count_only (bool |
    None): Indicates if only the count of matching items         should be returned
    instead of the full paginated results.         Defaults to False.         Optional.
    """

    limit: Annotated[int, Query(default=50, ge=1)] = Field(
        description="Number of items per page, minimum 1",
    )
    offset: Annotated[int, Query(default=0, ge=0)] = Field(
        description="Number of items to skip, minimum 0",
    )
    count_only: Annotated[bool, Query(default=False)] = Field(
        description="Indicates if only a count should be returned.",
    )
