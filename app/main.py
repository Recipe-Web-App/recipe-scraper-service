"""Application entry point.

This module initializes and starts the FastAPI application, configures middleware,
routers, and other startup procedures.
"""

from fastapi import FastAPI
from flake8 import configure_logging

from app.api.v1.routes import api_router

configure_logging(0)

app = FastAPI(
    title="Recipe Scraper Service",
    version="1.0.0",
    description="An API for scraping and managing recipe data.",
)

app.include_router(api_router)
