"""OpenTelemetry distributed tracing configuration.

This module provides:
- Trace context propagation
- FastAPI instrumentation
- Redis instrumentation
- OTLP exporter configuration
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.core.config import get_settings
from app.observability.logging import get_logger


if TYPE_CHECKING:
    from fastapi import FastAPI

    from app.core.config import Settings

logger = get_logger(__name__)


def setup_tracing(app: FastAPI, settings: Settings | None = None) -> None:
    """Configure OpenTelemetry tracing.

    Sets up trace collection, instrumentation, and export
    for distributed tracing across services.

    Args:
        app: The FastAPI application instance.
        settings: Optional settings override. If not provided, uses get_settings().
    """
    if settings is None:
        settings = get_settings()

    if not settings.observability.tracing.enabled:
        logger.info("Tracing disabled")
        return

    logger.info("Setting up OpenTelemetry tracing")

    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": settings.app.name.lower().replace(" ", "-"),
            "service.version": settings.app.version,
            "deployment.environment": settings.APP_ENV,
        }
    )

    # Create and configure tracer provider
    provider = TracerProvider(resource=resource)

    # Configure exporter based on environment
    if settings.observability.tracing.otlp_endpoint:
        # Production: Send traces to OTLP collector (Jaeger, Tempo, etc.)
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.observability.tracing.otlp_endpoint,
            insecure=True,  # Configure TLS in production
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info(
            "OTLP trace exporter configured",
            endpoint=settings.observability.tracing.otlp_endpoint,
        )
    elif settings.is_development:
        # Development: Log traces to console
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))
        logger.info("Console trace exporter configured (development mode)")

    # Set as global tracer provider
    trace.set_tracer_provider(provider)

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="health,health/live,health/ready,metrics,docs,redoc,openapi.json",
    )
    logger.debug("FastAPI instrumented for tracing")

    # Instrument Redis
    RedisInstrumentor().instrument()
    logger.debug("Redis instrumented for tracing")

    logger.info("OpenTelemetry tracing configured")


def shutdown_tracing() -> None:
    """Shutdown tracing and flush pending spans.

    Should be called during application shutdown to ensure
    all traces are exported before the process exits.
    """
    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        provider.shutdown()
        logger.info("Tracing shutdown complete")


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance for manual span creation.

    Args:
        name: Tracer name (typically __name__).

    Returns:
        OpenTelemetry Tracer instance.
    """
    return trace.get_tracer(name)


def get_current_span() -> trace.Span:
    """Get the currently active span.

    Returns:
        The current span from the active context.
    """
    return trace.get_current_span()


def add_span_attributes(**attributes: str | int | float | bool) -> None:
    """Add attributes to the current span.

    Convenience function to annotate the current span
    with additional context.

    Args:
        **attributes: Key-value pairs to add to the span.
    """
    span = get_current_span()
    if span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, value)


__all__ = [
    "add_span_attributes",
    "get_current_span",
    "get_tracer",
    "setup_tracing",
    "shutdown_tracing",
]
