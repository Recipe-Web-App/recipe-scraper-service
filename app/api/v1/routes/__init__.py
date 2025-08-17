"""Routes package initializer.

Groups all route modules for API version 1.
"""

from fastapi import APIRouter

from app.api.v1.routes import shopping

from . import admin, health, nutritional_info, recipes, recommendations

api_router = APIRouter()
api_router.include_router(admin.router)
api_router.include_router(health.router)
api_router.include_router(nutritional_info.router)
api_router.include_router(recipes.router)
api_router.include_router(recommendations.router)
api_router.include_router(shopping.router)
