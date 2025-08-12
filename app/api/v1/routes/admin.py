"""Administrative API routes for Recipe Scraper service management.

This module provides REST API endpoints for administrative operations such as cache
management and other maintenance tasks for the Recipe Scraper service.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.services.admin_service import AdminService

router = APIRouter()


def get_admin_service() -> AdminService:
    """Get AdminService instance."""
    return AdminService()


@router.post(
    "/recipe-scraper/admin/clear-cache",
    tags=["admin"],
    summary="Clears the cache",
    description="Clears the cache for the Recipe Scraper service.",
    status_code=200,
)
async def clear_cache(
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
) -> dict[str, str]:
    """Clear Cache Handler.

    This endpoint clears the cache for the Recipe Scraper service. It is intended for
    administrative use only.

    Returns:     dict: Success message confirming cache was cleared
    """
    await admin_service.clear_cache()
    return {"message": "Cache cleared successfully"}
