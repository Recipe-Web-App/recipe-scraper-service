"""Root endpoint providing service information.

This module provides the root endpoint which returns basic service
information for service discovery and health status navigation.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.root import RootResponse


router = APIRouter(tags=["Root"])


@router.get(
    "/",
    response_model=RootResponse,
    summary="Root endpoint",
    description="Root endpoint providing basic service information and health status.",
)
async def root(
    settings: Annotated[Settings, Depends(get_settings)],
) -> RootResponse:
    """Return basic service information.

    This endpoint is used for service discovery, providing links to
    documentation and health check endpoints. It does not require
    authentication.
    """
    return RootResponse(
        service=settings.app.name,
        version=settings.app.version,
        status="operational",
        docs=f"{settings.api.v1_prefix}/docs"
        if settings.is_non_production
        else "disabled",
        health=f"{settings.api.v1_prefix}/health",
    )
