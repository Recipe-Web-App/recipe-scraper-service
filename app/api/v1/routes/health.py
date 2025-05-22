"""Health check route handler.

Defines endpoints to verify the health and status of the API service.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get(
    "/recipe-scraper/health",
    tags=["health"],
    summary="Health check endpoint",
    description="Returns a 200 OK response indicating the server is up.",
    response_class=JSONResponse,
)  # type: ignore[misc]
def health_check() -> JSONResponse:
    """Health Check Handler.

    Returns:
        JSONResponse: OK
    """
    return JSONResponse(content={"status": "ok"})
