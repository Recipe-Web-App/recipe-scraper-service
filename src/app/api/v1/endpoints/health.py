"""Health check endpoints.

Provides liveness and readiness probes for Kubernetes and load balancers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Health status", examples=["healthy"])
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Current server timestamp",
    )
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Deployment environment")


class ReadinessResponse(HealthResponse):
    """Readiness check response with dependency status."""

    dependencies: dict[str, str] = Field(
        default_factory=dict,
        description="Status of external dependencies",
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Basic health check to verify the service is running.",
)
async def health_check(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """Check if the service is alive.

    This endpoint is used by Kubernetes liveness probes and load balancers
    to verify the service is running. It does not check external dependencies.
    """
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description="Readiness check verifying all dependencies are available.",
)
async def readiness_check(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReadinessResponse:
    """Check if the service is ready to handle requests.

    This endpoint is used by Kubernetes readiness probes to determine
    if the service should receive traffic. It checks all external dependencies.
    """
    dependencies: dict[str, str] = {}

    # Check Redis connection (will be implemented in Phase 4)
    # try:
    #     await redis_client.ping()
    #     dependencies["redis"] = "healthy"
    # except Exception:
    #     dependencies["redis"] = "unhealthy"

    # For now, assume all dependencies are healthy
    dependencies["redis"] = "not_configured"

    # Determine overall status
    all_healthy = all(
        status in ("healthy", "not_configured") for status in dependencies.values()
    )

    return ReadinessResponse(
        status="ready" if all_healthy else "degraded",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        dependencies=dependencies,
    )
