"""Recipe Management Service client exceptions.

This module defines exceptions specific to Recipe Management Service
client operations. These exceptions are caught by the endpoint layer
and converted to appropriate HTTP responses.
"""

from __future__ import annotations

from typing import Any


class RecipeManagementError(Exception):
    """Base exception for Recipe Management Service client errors."""


class RecipeManagementUnavailableError(RecipeManagementError):
    """Raised when the Recipe Management Service cannot be reached.

    This includes connection errors, timeouts, and service unavailability.
    """


class RecipeManagementTimeoutError(RecipeManagementUnavailableError):
    """Raised when a request to Recipe Management Service times out."""


class RecipeManagementResponseError(RecipeManagementError):
    """Raised when the Recipe Management Service returns an error response.

    This includes HTTP 4xx/5xx errors from the downstream service.
    """

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


class RecipeManagementValidationError(RecipeManagementResponseError):
    """Raised when the downstream service rejects the request as invalid.

    This typically indicates a 422 response from the downstream service,
    meaning our request payload didn't meet their validation requirements.
    """

    def __init__(
        self, message: str, details: list[dict[str, Any]] | None = None
    ) -> None:
        self.details = details
        super().__init__(status_code=422, message=message)


class RecipeManagementNotFoundError(RecipeManagementResponseError):
    """Raised when a requested resource is not found in Recipe Management Service.

    This typically indicates a 404 response from the downstream service.
    """

    def __init__(self, message: str) -> None:
        super().__init__(status_code=404, message=message)
