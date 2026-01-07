"""API v1 router aggregating all endpoint routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import auth, health


# Create the main v1 router
router = APIRouter()

# Include endpoint routers
router.include_router(health.router)
router.include_router(auth.router)  # Auth endpoints at /api/v1/auth/*

# TODO: Add additional routers (e.g., recipes.router)
