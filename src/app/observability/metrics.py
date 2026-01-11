"""Prometheus metrics instrumentation.

This module provides:
- FastAPI automatic request metrics
- Custom application metrics
- Metrics endpoint configuration
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prometheus_fastapi_instrumentator import Instrumentator, metrics

from app.core.config import get_settings
from app.observability.logging import get_logger


if TYPE_CHECKING:
    from fastapi import FastAPI

logger = get_logger(__name__)


def setup_metrics(app: FastAPI) -> Instrumentator:
    """Configure Prometheus metrics instrumentation.

    Sets up automatic HTTP request metrics collection including:
    - Request count by method, path, and status code
    - Request duration histogram
    - Request/response size
    - Requests in progress gauge

    Args:
        app: The FastAPI application instance.

    Returns:
        Configured Instrumentator instance.
    """
    settings = get_settings()

    if not settings.observability.metrics.enabled:
        logger.info("Metrics collection disabled")
        return Instrumentator()

    logger.info("Setting up Prometheus metrics")

    # Create instrumentator with configuration
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=[
            "/health",
            "/health/live",
            "/health/ready",
            "/metrics",
            "/openapi.json",
            "/docs",
            "/redoc",
        ],
        env_var_name="METRICS_ENABLED",
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )

    # Add default metrics (latency, request count, etc.)
    instrumentator.add(
        metrics.default(
            metric_namespace="recipe_scraper",
            metric_subsystem="http",
            should_only_respect_2xx_for_highr=False,
        )
    )

    # Add request size metrics
    instrumentator.add(
        metrics.request_size(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
            metric_namespace="recipe_scraper",
            metric_subsystem="http",
        )
    )

    # Add response size metrics
    instrumentator.add(
        metrics.response_size(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
            metric_namespace="recipe_scraper",
            metric_subsystem="http",
        )
    )

    # Instrument the app
    instrumentator.instrument(app)

    # Expose metrics endpoint
    instrumentator.expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,
        tags=["monitoring"],
    )

    logger.info("Prometheus metrics configured", endpoint="/metrics")

    return instrumentator


__all__ = ["setup_metrics"]
