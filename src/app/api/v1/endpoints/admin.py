"""Admin endpoints for system management operations.

Provides:
- DELETE /admin/cache for clearing all service caches
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import CurrentUser, RequirePermissions
from app.auth.permissions import Permission
from app.cache.redis import clear_cache
from app.observability.logging import get_logger
from app.schemas.admin import CacheClearResponse


logger = get_logger(__name__)

router = APIRouter(tags=["Admin"])


@router.delete(
    "/admin/cache",
    response_model=CacheClearResponse,
    summary="Clear all service caches",
    description=(
        "Clears all cached data from the service cache. This operation removes "
        "all cached recipe data, nutritional information, and other cached lookups. "
        "Use with caution as this may temporarily increase load on downstream services."
    ),
    responses={
        200: {
            "description": "Cache cleared successfully",
            "content": {
                "application/json": {
                    "example": {"message": "Cache cleared successfully"}
                }
            },
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {"example": {"detail": "Not authenticated"}}
            },
        },
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {"example": {"detail": "Insufficient permissions"}}
            },
        },
        503: {
            "description": "Cache service unavailable",
            "content": {
                "application/json": {
                    "example": {
                        "error": "SERVICE_UNAVAILABLE",
                        "message": "Cache service is not available",
                    }
                }
            },
        },
    },
)
async def clear_cache_endpoint(
    user: Annotated[CurrentUser, Depends(RequirePermissions(Permission.ADMIN_SYSTEM))],
) -> CacheClearResponse:
    """Clear all service caches.

    This endpoint clears all cached data from the Redis cache instance.
    It requires ADMIN_SYSTEM permission (available to admin and service roles).

    Args:
        user: Authenticated user with ADMIN_SYSTEM permission.

    Returns:
        CacheClearResponse with success message.

    Raises:
        HTTPException: 401 if not authenticated.
        HTTPException: 403 if user lacks ADMIN_SYSTEM permission.
        HTTPException: 503 if Redis cache is unavailable.
    """
    logger.info(
        "Cache clear requested",
        user_id=user.id,
        user_roles=user.roles,
    )

    try:
        await clear_cache()
    except RuntimeError:
        logger.exception("Cache service not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "SERVICE_UNAVAILABLE",
                "message": "Cache service is not available",
            },
        ) from None
    except Exception as e:
        logger.exception("Failed to clear cache")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "SERVICE_UNAVAILABLE",
                "message": f"Failed to clear cache: {e}",
            },
        ) from None

    logger.info(
        "Cache cleared successfully",
        user_id=user.id,
    )

    return CacheClearResponse(message="Cache cleared successfully")
