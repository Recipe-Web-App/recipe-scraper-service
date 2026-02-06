"""Health check schemas.

This module contains schemas for service health monitoring endpoints.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.base import APIResponse
from app.schemas.enums import HealthStatus


class HealthCheckItem(APIResponse):
    """Individual component health status."""

    status: HealthStatus = Field(..., description="Component health status")
    message: str = Field(..., description="Status message")
    response_time_ms: float | None = Field(
        default=None,
        description="Response time in milliseconds",
    )


class ExternalApisHealth(APIResponse):
    """Health status of external API dependencies."""

    spoonacular: HealthCheckItem | None = Field(
        default=None,
        description="Spoonacular API health",
    )


class HealthChecks(APIResponse):
    """Collection of component health checks."""

    database: HealthCheckItem | None = Field(
        default=None,
        description="Database health status",
    )
    cache: HealthCheckItem | None = Field(
        default=None,
        description="Cache (Redis) health status",
    )
    external_apis: ExternalApisHealth | None = Field(
        default=None,
        description="External API health statuses",
    )


class DatabaseMonitoring(APIResponse):
    """Database monitoring status."""

    enabled: bool = Field(..., description="Whether monitoring is enabled")
    last_check: datetime | None = Field(
        default=None,
        description="Last health check timestamp",
    )


class HealthCheckResponse(APIResponse):
    """Comprehensive service health check response."""

    status: HealthStatus = Field(..., description="Overall service health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Service version")
    uptime_seconds: int | None = Field(
        default=None,
        description="Service uptime in seconds",
    )
    checks: HealthChecks | None = Field(
        default=None,
        description="Component health checks",
    )
    database_monitoring: DatabaseMonitoring | None = Field(
        default=None,
        description="Database monitoring status",
    )
    response_time_ms: float | None = Field(
        default=None,
        description="Health check response time",
    )
