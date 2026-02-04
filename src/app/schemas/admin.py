"""Admin operation schemas.

Provides response models for admin endpoints.
"""

from __future__ import annotations

from pydantic import Field

from app.schemas.base import APIResponse


class CacheClearResponse(APIResponse):
    """Response model for cache clear operation."""

    message: str = Field(
        ...,
        description="Success message",
        examples=["Cache cleared successfully"],
    )
