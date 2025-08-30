"""Health check route handlers.

Comprehensive health endpoints for monitoring service health, readiness, and detailed
status information with Prometheus metrics.
"""

import asyncio
import time
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

import httpx
import redis.asyncio as aioredis
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, Info
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.config import get_settings
from app.core.logging import get_logger
from app.db.session import check_database_health
from app.services.database_monitor import get_database_monitor_status

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


async def check_database_connection_with_session(db: AsyncSession) -> dict[str, Any]:
    """Check database connectivity with an existing session.

    Args:
        db: Database session

    Returns:
        Database health status dict
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


async def check_database_connection() -> dict[str, Any]:
    """Check database connectivity without requiring a session dependency.

    This function uses the check_database_health utility to test connectivity
    and handles database unavailability gracefully for health endpoints.

    Returns:
        Database health status dict
    """
    start_time = time.time()
    try:
        is_healthy = await check_database_health()
        duration = time.time() - start_time

        if is_healthy:
            return {
                "status": HealthStatus.HEALTHY,
                "response_time_ms": round(duration * 1000, 2),
                "message": "Database connection successful",
            }
        else:
            return {
                "status": HealthStatus.DEGRADED,
                "response_time_ms": round(duration * 1000, 2),
                "message": "Database connection failed",
            }
    except Exception as e:
        duration = time.time() - start_time
        return {
            "status": HealthStatus.DEGRADED,
            "response_time_ms": round(duration * 1000, 2),
            "message": f"Database health check error: {str(e)[:100]}",
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
async def readiness_probe() -> JSONResponse:
    """Readiness probe endpoint.

    Comprehensive readiness check including database connectivity. Used by Kubernetes
    for readiness probes. Returns degraded status when database is unavailable but
    service can still function.

    Returns:
        JSONResponse with readiness status (200 OK even when degraded)
    """
    with health_check_duration.labels(endpoint="readiness").time():
        # Check database without dependency injection to avoid exceptions
        db_status = await check_database_connection()

        # Determine overall readiness status
        if db_status["status"] == HealthStatus.HEALTHY:
            overall_status = "ready"
            health_check_counter.labels(endpoint="readiness", status="success").inc()
        else:
            overall_status = "degraded"
            health_check_counter.labels(endpoint="readiness", status="degraded").inc()

        return JSONResponse(
            content={
                "status": overall_status,
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "checks": {"database": db_status},
                "message": (
                    "Service ready"
                    if overall_status == "ready"
                    else "Service degraded but operational"
                ),
            }
        )


@router.get(
    "/health",
    tags=["health"],
    summary="Comprehensive health check",
    description="Detailed health status including all dependencies and metrics.",
    status_code=status.HTTP_200_OK,
)
async def health_check() -> JSONResponse:
    """Comprehensive health check endpoint.

    Provides detailed health information about the service and all its dependencies.
    Handles database unavailability gracefully and shows degraded status.

    Returns:
        JSONResponse with comprehensive health status
    """
    with health_check_duration.labels(endpoint="health").time():
        start_time = time.time()

        # Run all health checks concurrently without database dependency injection
        results = await asyncio.gather(
            check_database_connection(),
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

        # Calculate overall status with proper handling of degraded components
        unhealthy_count = 0
        degraded_count = 0

        # Count unhealthy and degraded components
        for check in [db_check, redis_check]:
            if check.get("status") == HealthStatus.UNHEALTHY:
                unhealthy_count += 1
            elif check.get("status") == HealthStatus.DEGRADED:
                degraded_count += 1

        # Check external APIs
        for api_status in external_apis_check.values():
            if api_status.get("status") == HealthStatus.UNHEALTHY:
                unhealthy_count += 1
            elif api_status.get("status") == HealthStatus.DEGRADED:
                degraded_count += 1

        # Determine overall status - service remains operational with degraded database
        if unhealthy_count > 0:
            overall_status = HealthStatus.UNHEALTHY
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif degraded_count > 0:
            overall_status = HealthStatus.DEGRADED
            status_code = status.HTTP_200_OK  # Service still operational
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

        # Include database monitoring status
        db_monitor_status = get_database_monitor_status()

        response_content = {
            "status": overall_status,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "version": "2.0.0",
            "uptime_seconds": int(
                time.time()
            ),  # Would need startup time tracking for accurate uptime
            "checks": checks,
            "database_monitoring": db_monitor_status,
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
