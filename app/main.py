"""Application entry point.

This module initializes and starts the FastAPI application, configures middleware,
routers, and other startup procedures.
"""

from fastapi import FastAPI
<<<<<<< HEAD
from flake8 import configure_logging

from app.api.v1.routes import api_router

configure_logging(0)
=======
>>>>>>> 68a88df (Implemented sphinx documentation generation.)

app = FastAPI(
    title="Recipe Scraper Service",
    version="1.0.0",
    description="An API for scraping and managing recipe data.",
)
<<<<<<< HEAD

app.include_router(api_router)
=======
>>>>>>> 68a88df (Implemented sphinx documentation generation.)
