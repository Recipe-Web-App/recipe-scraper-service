"""Root endpoint response schema.

Provides the response model for the root endpoint which returns
basic service information and status.
"""

from __future__ import annotations

from pydantic import Field

from app.schemas.base import APIResponse


class RootResponse(APIResponse):
    """Response model for root endpoint.

    Returns basic service information including name, version,
    operational status, and links to documentation and health endpoints.
    """

    service: str = Field(
        ...,
        description="Service name",
        examples=["Recipe Scraper Service"],
    )
    version: str = Field(
        ...,
        description="Service version",
        examples=["2.0.0"],
    )
    status: str = Field(
        ...,
        description="Service operational status",
        examples=["operational"],
    )
    docs: str = Field(
        ...,
        description="API documentation URL or status",
        examples=["/api/v1/recipe-scraper/docs"],
    )
    health: str = Field(
        ...,
        description="Health check endpoint URL",
        examples=["/api/v1/recipe-scraper/health"],
    )
