"""Application entry point.

This module initializes and starts the FastAPI application, configures middleware,
routers, and other startup procedures.
"""

from fastapi import FastAPI

from app.api.v1.routes import api_router
from app.exceptions.handlers import unhandled_exception_handler
from app.middleware.request_id_middleware import RequestIDMiddleware

app = FastAPI(
    title="Recipe Scraper Service",
    version="1.0.0",
    description="An API for scraping and managing recipe data.",
)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.add_middleware(RequestIDMiddleware)
app.include_router(api_router, prefix="/api")
