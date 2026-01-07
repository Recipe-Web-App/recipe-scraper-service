"""Application entry point.

This module serves as the entry point for the FastAPI application.
It creates the application instance using the factory pattern.

Usage:
    # Development with auto-reload
    uvicorn app.main:app --reload

    # Production with gunicorn
    gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
"""

from app.factory import create_app


# Create the application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn

    from app.core.config import get_settings

    settings = get_settings()

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
    )
