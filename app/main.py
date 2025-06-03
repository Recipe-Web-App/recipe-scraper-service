"""Application entry point.

This module initializes and starts the FastAPI application, configures middleware,
routers, and other startup procedures.
"""

from fastapi import FastAPI

from app.api.v1.routes import api_router
from app.middleware.logging_middleware import RequestLoggingMiddleware

app = FastAPI(
    title="Recipe Scraper Service",
    version="1.0.0",
    description="An API for scraping and managing recipe data.",
)
app.add_middleware(RequestLoggingMiddleware)
app.include_router(api_router, prefix="/api")
