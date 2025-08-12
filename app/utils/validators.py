"""Input validation utilities.

This module provides helper functions to validate user inputs, data formats, and enforce
constraints.
"""

from http import HTTPStatus

from fastapi import HTTPException

from app.api.v1.schemas.common.pagination_params import PaginationParams


def validate_pagination_params(params: PaginationParams) -> None:
    """Validate pagination parameters.

    Ensures that the offset is not greater than the limit.

    Args:     params (PaginationParams): The pagination parameters to validate.

    Raises:     HTTPException: If offset is greater than limit.
    """
    if params.offset > params.limit:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Offset cannot be greater than limit.",
        )
