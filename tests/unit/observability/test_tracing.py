"""Unit tests for tracing module.

Tests cover:
- Tracing setup
- Tracing shutdown
- Tracer utilities
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from opentelemetry.sdk.trace import TracerProvider

from app.observability.tracing import (
    add_span_attributes,
    get_current_span,
    get_tracer,
    setup_tracing,
    shutdown_tracing,
)


pytestmark = pytest.mark.unit


class TestSetupTracing:
    """Tests for setup_tracing function."""

    def test_returns_early_when_disabled(self) -> None:
        """Should return early when tracing is disabled."""
        mock_app = MagicMock()
        mock_settings = MagicMock()
        mock_settings.ENABLE_TRACING = False

        with patch(
            "app.observability.tracing.get_settings", return_value=mock_settings
        ):
            setup_tracing(mock_app)

        # FastAPIInstrumentor should not be called
        # No error should be raised

    def test_configures_otlp_exporter_when_endpoint_set(self) -> None:
        """Should configure OTLP exporter when endpoint is set."""
        mock_app = MagicMock()
        mock_settings = MagicMock()
        mock_settings.ENABLE_TRACING = True
        mock_settings.APP_NAME = "test-app"
        mock_settings.APP_VERSION = "1.0.0"
        mock_settings.ENVIRONMENT = "test"
        mock_settings.OTLP_ENDPOINT = "http://localhost:4317"
        mock_settings.is_development = False

        with (
            patch("app.observability.tracing.get_settings", return_value=mock_settings),
            patch("app.observability.tracing.Resource.create"),
            patch("app.observability.tracing.TracerProvider") as mock_provider_class,
            patch("app.observability.tracing.OTLPSpanExporter") as mock_otlp,
            patch("app.observability.tracing.BatchSpanProcessor"),
            patch("app.observability.tracing.trace.set_tracer_provider"),
            patch("app.observability.tracing.FastAPIInstrumentor"),
            patch("app.observability.tracing.RedisInstrumentor"),
        ):
            mock_provider = MagicMock()
            mock_provider_class.return_value = mock_provider

            setup_tracing(mock_app)

            mock_otlp.assert_called_once_with(
                endpoint="http://localhost:4317",
                insecure=True,
            )

    def test_configures_console_exporter_in_development(self) -> None:
        """Should configure console exporter in development without OTLP."""
        mock_app = MagicMock()
        mock_settings = MagicMock()
        mock_settings.ENABLE_TRACING = True
        mock_settings.APP_NAME = "test-app"
        mock_settings.APP_VERSION = "1.0.0"
        mock_settings.ENVIRONMENT = "development"
        mock_settings.OTLP_ENDPOINT = None
        mock_settings.is_development = True

        with (
            patch("app.observability.tracing.get_settings", return_value=mock_settings),
            patch("app.observability.tracing.Resource.create"),
            patch("app.observability.tracing.TracerProvider") as mock_provider_class,
            patch("app.observability.tracing.ConsoleSpanExporter") as mock_console,
            patch("app.observability.tracing.BatchSpanProcessor"),
            patch("app.observability.tracing.trace.set_tracer_provider"),
            patch("app.observability.tracing.FastAPIInstrumentor"),
            patch("app.observability.tracing.RedisInstrumentor"),
        ):
            mock_provider = MagicMock()
            mock_provider_class.return_value = mock_provider

            setup_tracing(mock_app)

            mock_console.assert_called_once()

    def test_instruments_fastapi(self) -> None:
        """Should instrument FastAPI application."""
        mock_app = MagicMock()
        mock_settings = MagicMock()
        mock_settings.ENABLE_TRACING = True
        mock_settings.APP_NAME = "test-app"
        mock_settings.APP_VERSION = "1.0.0"
        mock_settings.ENVIRONMENT = "test"
        mock_settings.OTLP_ENDPOINT = None
        mock_settings.is_development = False

        with (
            patch("app.observability.tracing.get_settings", return_value=mock_settings),
            patch("app.observability.tracing.Resource.create"),
            patch("app.observability.tracing.TracerProvider"),
            patch("app.observability.tracing.trace.set_tracer_provider"),
            patch(
                "app.observability.tracing.FastAPIInstrumentor"
            ) as mock_fastapi_instr,
            patch("app.observability.tracing.RedisInstrumentor"),
        ):
            setup_tracing(mock_app)

            mock_fastapi_instr.instrument_app.assert_called_once()

    def test_instruments_redis(self) -> None:
        """Should instrument Redis."""
        mock_app = MagicMock()
        mock_settings = MagicMock()
        mock_settings.ENABLE_TRACING = True
        mock_settings.APP_NAME = "test-app"
        mock_settings.APP_VERSION = "1.0.0"
        mock_settings.ENVIRONMENT = "test"
        mock_settings.OTLP_ENDPOINT = None
        mock_settings.is_development = False

        with (
            patch("app.observability.tracing.get_settings", return_value=mock_settings),
            patch("app.observability.tracing.Resource.create"),
            patch("app.observability.tracing.TracerProvider"),
            patch("app.observability.tracing.trace.set_tracer_provider"),
            patch("app.observability.tracing.FastAPIInstrumentor"),
            patch("app.observability.tracing.RedisInstrumentor") as mock_redis_instr,
        ):
            mock_instance = MagicMock()
            mock_redis_instr.return_value = mock_instance

            setup_tracing(mock_app)

            mock_instance.instrument.assert_called_once()


class TestShutdownTracing:
    """Tests for shutdown_tracing function."""

    def test_shuts_down_tracer_provider(self) -> None:
        """Should shutdown TracerProvider."""
        mock_provider = MagicMock(spec=TracerProvider)

        with patch(
            "app.observability.tracing.trace.get_tracer_provider",
            return_value=mock_provider,
        ):
            shutdown_tracing()

            mock_provider.shutdown.assert_called_once()

    def test_handles_non_tracer_provider(self) -> None:
        """Should handle non-TracerProvider gracefully."""
        mock_provider = MagicMock(spec=[])  # No shutdown method

        with patch(
            "app.observability.tracing.trace.get_tracer_provider",
            return_value=mock_provider,
        ):
            # Should not raise
            shutdown_tracing()


class TestGetTracer:
    """Tests for get_tracer function."""

    def test_returns_tracer(self) -> None:
        """Should return tracer from trace module."""
        mock_tracer = MagicMock()

        with patch(
            "app.observability.tracing.trace.get_tracer",
            return_value=mock_tracer,
        ):
            result = get_tracer("test-module")

            assert result is mock_tracer


class TestGetCurrentSpan:
    """Tests for get_current_span function."""

    def test_returns_current_span(self) -> None:
        """Should return current span from trace module."""
        mock_span = MagicMock()

        with patch(
            "app.observability.tracing.trace.get_current_span",
            return_value=mock_span,
        ):
            result = get_current_span()

            assert result is mock_span


class TestAddSpanAttributes:
    """Tests for add_span_attributes function."""

    def test_adds_attributes_to_recording_span(self) -> None:
        """Should add attributes when span is recording."""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True

        with patch(
            "app.observability.tracing.get_current_span",
            return_value=mock_span,
        ):
            add_span_attributes(key1="value1", key2=123)

            mock_span.set_attribute.assert_any_call("key1", "value1")
            mock_span.set_attribute.assert_any_call("key2", 123)

    def test_skips_non_recording_span(self) -> None:
        """Should not add attributes when span is not recording."""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = False

        with patch(
            "app.observability.tracing.get_current_span",
            return_value=mock_span,
        ):
            add_span_attributes(key1="value1")

            mock_span.set_attribute.assert_not_called()
