"""Health check route handler.

Defines endpoints to verify the health and status of the API service.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

router = APIRouter()

__log = get_logger("Routes")


@router.get(
    "/recipe-scraper/health",
    tags=["health"],
    summary="Health check endpoint",
    description="Returns a 200 OK response indicating the server is up.",
    response_class=JSONResponse,
)
def health_check() -> JSONResponse:
    """Health Check Handler.

    Returns:
        JSONResponse: OK
    """
    content = {"status": "ok"}
    __log.info("Health Check Response: {}", content)
    return JSONResponse(content=content)
