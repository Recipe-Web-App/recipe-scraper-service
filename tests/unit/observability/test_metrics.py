"""Unit tests for metrics module.

Tests cover:
- Metrics setup configuration
- Instrumentator initialization
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.observability.metrics import setup_metrics


pytestmark = pytest.mark.unit


class TestSetupMetrics:
    """Tests for setup_metrics function."""

    def test_returns_instrumentator_when_disabled(self) -> None:
        """Should return empty instrumentator when metrics disabled."""
        mock_app = MagicMock()
        mock_settings = MagicMock()
        mock_settings.METRICS_ENABLED = False

        with patch(
            "app.observability.metrics.get_settings", return_value=mock_settings
        ):
            result = setup_metrics(mock_app)

        assert result is not None

    def test_configures_instrumentator_when_enabled(self) -> None:
        """Should configure instrumentator when metrics enabled."""
        mock_app = MagicMock()
        mock_settings = MagicMock()
        mock_settings.METRICS_ENABLED = True

        with (
            patch("app.observability.metrics.get_settings", return_value=mock_settings),
            patch("app.observability.metrics.Instrumentator") as mock_instr_class,
        ):
            mock_instrumentator = MagicMock()
            mock_instr_class.return_value = mock_instrumentator
            mock_instrumentator.add.return_value = mock_instrumentator

            result = setup_metrics(mock_app)

            # Should have created instrumentator with config
            mock_instr_class.assert_called_once()
            # Should have added metrics
            assert mock_instrumentator.add.called
            # Should have instrumented app
            mock_instrumentator.instrument.assert_called_once_with(mock_app)
            # Verify result is returned
            assert result is mock_instrumentator

    def test_excludes_health_and_metrics_endpoints(self) -> None:
        """Should exclude health and metrics from instrumentation."""
        mock_app = MagicMock()
        mock_settings = MagicMock()
        mock_settings.METRICS_ENABLED = True

        with (
            patch("app.observability.metrics.get_settings", return_value=mock_settings),
            patch("app.observability.metrics.Instrumentator") as mock_instr_class,
        ):
            mock_instrumentator = MagicMock()
            mock_instr_class.return_value = mock_instrumentator
            mock_instrumentator.add.return_value = mock_instrumentator

            setup_metrics(mock_app)

            # Check excluded_handlers in the call
            call_kwargs = mock_instr_class.call_args.kwargs
            assert "/health" in call_kwargs["excluded_handlers"]
            assert "/metrics" in call_kwargs["excluded_handlers"]

    def test_exposes_metrics_endpoint(self) -> None:
        """Should expose /metrics endpoint."""
        mock_app = MagicMock()
        mock_settings = MagicMock()
        mock_settings.METRICS_ENABLED = True

        with (
            patch("app.observability.metrics.get_settings", return_value=mock_settings),
            patch("app.observability.metrics.Instrumentator") as mock_instr_class,
        ):
            mock_instrumentator = MagicMock()
            mock_instr_class.return_value = mock_instrumentator
            mock_instrumentator.add.return_value = mock_instrumentator

            setup_metrics(mock_app)

            # Should expose endpoint
            mock_instrumentator.expose.assert_called_once()
            call_kwargs = mock_instrumentator.expose.call_args.kwargs
            assert call_kwargs["endpoint"] == "/metrics"
