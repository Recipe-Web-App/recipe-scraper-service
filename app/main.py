"""Application entry point.

This module initializes and starts the FastAPI application, configures middleware,
routers, and other startup procedures.
"""

from fastapi import FastAPI

app = FastAPI(
    title="Recipe Scraper Service",
    version="1.0.0",
    description="An API for scraping and managing recipe data.",
)
