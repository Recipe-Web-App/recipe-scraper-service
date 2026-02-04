"""API v1 router aggregating all endpoint routers.

All endpoints are mounted under /api/v1/recipe-scraper/ via the v1_prefix configuration.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import admin, health, ingredients, recipes


# Create the main v1 router
# All routes here are prefixed with /api/v1/recipe-scraper/ (configured via v1_prefix)
router = APIRouter()

# Include health endpoints
router.include_router(health.router)

# Include recipe endpoints
router.include_router(recipes.router)

# Include ingredient endpoints
router.include_router(ingredients.router)

# Include admin endpoints
router.include_router(admin.router)

# NOTE: Auth endpoints have been removed from this service.
# Authentication is handled by the external auth-service via OAuth2.
# Token URL: /oauth/token (see OpenAPI spec)
# See docs/architecture.md for the auth provider pattern.
