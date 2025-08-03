"""Health check route handlers.

Comprehensive health endpoints for monitoring service health, readiness, and detailed
status information with Prometheus metrics.
"""

import asyncio
import time
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Annotated, Any

import httpx
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, Info
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_db

router = APIRouter()
_log = get_logger(__name__)
settings = get_settings()

# Prometheus metrics
health_check_counter = Counter(
    "health_checks_total", "Total number of health checks", ["endpoint", "status"]
)

health_check_duration = Histogram(
    "health_check_duration_seconds", "Time spent on health checks", ["endpoint"]
)

service_info = Info("recipe_scraper_service", "Recipe Scraper Service information")

# Initialize service info
service_info.info(
    {"version": "2.0.0", "python_version": "3.13", "fastapi_version": "0.118.0"}
)


class HealthStatus:
    """Health status enumeration."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


async def check_database_connection(db: AsyncSession) -> dict[str, Any]:
    """Check database connectivity.

    Args:     db: Database session

    Returns:     Database health status dict
    """
    start_time = time.time()
    result = await db.execute(text("SELECT 1"))
    duration = time.time() - start_time

    if result.scalar() == 1:
        return {
            "status": HealthStatus.HEALTHY,
            "response_time_ms": round(duration * 1000, 2),
            "message": "Database connection successful",
        }
    return {
        "status": HealthStatus.UNHEALTHY,
        "response_time_ms": round(duration * 1000, 2),
        "message": "Database query returned unexpected result",
    }


async def check_external_apis() -> dict[str, Any]:
    """Check external API connectivity (Spoonacular).

    Returns:     External APIs health status dict
    """
    spoonacular_status: dict[str, Any] = {
        "status": HealthStatus.HEALTHY,
        "message": "Not tested",
    }

    start_time = time.time()
    async with httpx.AsyncClient(timeout=5.0) as client:
        # Simple API key validation call
        response = await client.get(
            "https://api.spoonacular.com/recipes/complexSearch",
            params={
                "apiKey": settings.spoonacular_api_key,
                "number": 1,
                "query": "test",
            },
        )
        duration = time.time() - start_time

        if response.status_code == HTTPStatus.OK:
            spoonacular_status = {
                "status": HealthStatus.HEALTHY,
                "response_time_ms": round(duration * 1000, 2),
                "message": "Spoonacular API accessible",
            }
        else:
            spoonacular_status = {
                "status": HealthStatus.DEGRADED,
                "response_time_ms": round(duration * 1000, 2),
                "message": f"Spoonacular API returned {response.status_code}",
            }

    return {"spoonacular": spoonacular_status}


async def check_redis_connection() -> dict[str, Any]:
    """Check Redis connectivity.

    Returns:     Redis health status dict
    """
    start_time = time.time()
    redis = aioredis.from_url(settings.redis_url)
    await redis.ping()
    duration = time.time() - start_time
    await redis.close()

    return {
        "status": HealthStatus.HEALTHY,
        "response_time_ms": round(duration * 1000, 2),
        "message": "Redis connection successful",
    }


@router.get(
    "/liveness",
    tags=["health"],
    summary="Liveness probe",
    description="Basic liveness check for Kubernetes/container orchestration.",
    status_code=status.HTTP_200_OK,
)
async def liveness_probe() -> JSONResponse:
    """Liveness probe endpoint.

    Simple endpoint that returns 200 OK if the service is running. Used by Kubernetes
    for liveness probes.

    Returns:     JSONResponse with basic status
    """
    with health_check_duration.labels(endpoint="liveness").time():
        health_check_counter.labels(endpoint="liveness", status="success").inc()

        return JSONResponse(
            content={
                "status": "alive",
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "service": "recipe-scraper-service",
            }
        )


@router.get(
    "/readiness",
    tags=["health"],
    summary="Readiness probe",
    description="Readiness check including database and external dependencies.",
    status_code=status.HTTP_200_OK,
)
async def readiness_probe(db: Annotated[AsyncSession, Depends(get_db)]) -> JSONResponse:
    """Readiness probe endpoint.

    Comprehensive readiness check including database connectivity. Used by Kubernetes
    for readiness probes.

    Args:     db: Database session dependency

    Returns:     JSONResponse with readiness status

    Raises:     HTTPException: If service is not ready
    """
    with health_check_duration.labels(endpoint="readiness").time():
        # Check database
        db_status = await check_database_connection(db)

        if db_status["status"] != HealthStatus.HEALTHY:
            health_check_counter.labels(endpoint="readiness", status="failed").inc()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not ready: Database unavailable",
            )

        health_check_counter.labels(endpoint="readiness", status="success").inc()

        return JSONResponse(
            content={
                "status": "ready",
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "checks": {"database": db_status},
            }
        )


@router.get(
    "/health",
    tags=["health"],
    summary="Comprehensive health check",
    description="Detailed health status including all dependencies and metrics.",
    status_code=status.HTTP_200_OK,
)
async def health_check(db: Annotated[AsyncSession, Depends(get_db)]) -> JSONResponse:
    """Comprehensive health check endpoint.

    Provides detailed health information about the service and all its dependencies.

    Args:     db: Database session dependency

    Returns:     JSONResponse with comprehensive health status
    """
    with health_check_duration.labels(endpoint="health").time():
        start_time = time.time()

        # Run all health checks concurrently
        results = await asyncio.gather(
            check_database_connection(db),
            check_external_apis(),
            check_redis_connection(),
            return_exceptions=True,
        )

        # Unpack with explicit type annotations
        db_check: dict[str, Any] | BaseException = results[0]
        external_apis_check: dict[str, Any] | BaseException = results[1]
        redis_check: dict[str, Any] | BaseException = results[2]

        # Handle any exceptions from concurrent checks
        if isinstance(db_check, BaseException):
            db_check = {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Database check failed: {str(db_check)[:100]}",
            }

        if isinstance(external_apis_check, BaseException):
            external_apis_check = {
                "spoonacular": {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "External API check failed: "
                    f"{str(external_apis_check)[:100]}",
                }
            }

        if isinstance(redis_check, BaseException):
            redis_check = {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Redis check failed: {str(redis_check)[:100]}",
            }

        # Determine overall health status
        checks = {
            "database": db_check,
            "cache": redis_check,
            "external_apis": external_apis_check,
        }

        # Calculate overall status
        unhealthy_count = sum(
            1
            for check in [db_check, redis_check]
            if check.get("status") == HealthStatus.UNHEALTHY
        )

        # Check external APIs
        for api_status in external_apis_check.values():
            if api_status.get("status") == HealthStatus.UNHEALTHY:
                unhealthy_count += 1

        if unhealthy_count > 0:
            overall_status = (
                HealthStatus.DEGRADED
                if unhealthy_count == 1
                else HealthStatus.UNHEALTHY
            )
            status_code = (
                status.HTTP_503_SERVICE_UNAVAILABLE
                if overall_status == HealthStatus.UNHEALTHY
                else status.HTTP_200_OK
            )
        else:
            overall_status = HealthStatus.HEALTHY
            status_code = status.HTTP_200_OK

        total_duration = time.time() - start_time

        health_check_counter.labels(
            endpoint="health",
            status=(
                "success" if overall_status != HealthStatus.UNHEALTHY else "failed"
            ),
        ).inc()

        response_content = {
            "status": overall_status,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "version": "2.0.0",
            "uptime_seconds": int(
                time.time()
            ),  # Would need startup time tracking for accurate uptime
            "checks": checks,
            "response_time_ms": round(total_duration * 1000, 2),
        }

        return JSONResponse(content=response_content, status_code=status_code)


# Legacy endpoint for backwards compatibility
@router.get(
    "/recipe-scraper/health",
    tags=["health"],
    summary="Legacy health check (deprecated)",
    description="Legacy health check endpoint. Use /health instead.",
    deprecated=True,
)
async def legacy_health_check() -> JSONResponse:
    """Legacy health check endpoint for backwards compatibility.

    Returns:     JSONResponse with basic status
    """
    health_check_counter.labels(endpoint="legacy", status="success").inc()

    content = {"status": "ok"}
    _log.info("Legacy Health Check Response: {}", content)
    return JSONResponse(content=content)
