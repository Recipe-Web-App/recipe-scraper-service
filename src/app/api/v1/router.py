"""API v1 router aggregating all endpoint routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import health


# Create the main v1 router
router = APIRouter()

# Include endpoint routers
router.include_router(health.router)

# NOTE: Auth endpoints (/api/v1/auth/*) have been removed.
# Authentication is now handled by the external auth-service.
# See docs/architecture.md for the auth provider pattern.

# TODO: Add additional routers (e.g., recipes.router)
