"""Unit tests for metrics module.

Tests cover:
- Metrics setup configuration
- Instrumentator initialization
- Disabled metrics path
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.observability.metrics import setup_metrics


pytestmark = pytest.mark.unit


def _create_mock_settings(*, metrics_enabled: bool = True) -> MagicMock:
    """Create mock settings with proper nested structure."""
    mock_settings = MagicMock()
    mock_settings.observability.metrics.enabled = metrics_enabled
    return mock_settings


class TestSetupMetrics:
    """Tests for setup_metrics function."""

    def test_returns_instrumentator_when_disabled(self) -> None:
        """Should return empty instrumentator when metrics disabled."""
        mock_app = MagicMock()
        mock_settings = _create_mock_settings(metrics_enabled=False)

        with patch(
            "app.observability.metrics.get_settings", return_value=mock_settings
        ):
            result = setup_metrics(mock_app)

        # Should return an Instrumentator (empty)
        assert result is not None

    def test_disabled_metrics_does_not_instrument_app(self) -> None:
        """Should not instrument app when metrics are disabled."""
        mock_app = MagicMock()
        mock_settings = _create_mock_settings(metrics_enabled=False)

        with (
            patch("app.observability.metrics.get_settings", return_value=mock_settings),
            patch("app.observability.metrics.Instrumentator") as mock_instr_class,
        ):
            mock_instrumentator = MagicMock()
            mock_instr_class.return_value = mock_instrumentator

            setup_metrics(mock_app)

            # Should NOT call instrument when disabled
            mock_instrumentator.instrument.assert_not_called()

    def test_configures_instrumentator_when_enabled(self) -> None:
        """Should configure instrumentator when metrics enabled."""
        mock_app = MagicMock()
        mock_settings = _create_mock_settings(metrics_enabled=True)

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
        mock_settings = _create_mock_settings(metrics_enabled=True)

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
        mock_settings = _create_mock_settings(metrics_enabled=True)

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


class TestMetricsConfiguration:
    """Tests for metrics configuration options."""

    def test_uses_recipe_scraper_namespace(self) -> None:
        """Should use recipe_scraper as metric namespace."""
        mock_app = MagicMock()
        mock_settings = _create_mock_settings(metrics_enabled=True)

        with (
            patch("app.observability.metrics.get_settings", return_value=mock_settings),
            patch("app.observability.metrics.Instrumentator") as mock_instr_class,
            patch("app.observability.metrics.metrics") as mock_metrics_module,
        ):
            mock_instrumentator = MagicMock()
            mock_instr_class.return_value = mock_instrumentator
            mock_instrumentator.add.return_value = mock_instrumentator

            setup_metrics(mock_app)

            # Verify namespace is set in default metrics
            mock_metrics_module.default.assert_called()
            call_kwargs = mock_metrics_module.default.call_args.kwargs
            assert call_kwargs["metric_namespace"] == "recipe_scraper"

    def test_includes_request_size_metrics(self) -> None:
        """Should add request size metrics."""
        mock_app = MagicMock()
        mock_settings = _create_mock_settings(metrics_enabled=True)

        with (
            patch("app.observability.metrics.get_settings", return_value=mock_settings),
            patch("app.observability.metrics.Instrumentator") as mock_instr_class,
            patch("app.observability.metrics.metrics") as mock_metrics_module,
        ):
            mock_instrumentator = MagicMock()
            mock_instr_class.return_value = mock_instrumentator
            mock_instrumentator.add.return_value = mock_instrumentator

            setup_metrics(mock_app)

            mock_metrics_module.request_size.assert_called()

    def test_includes_response_size_metrics(self) -> None:
        """Should add response size metrics."""
        mock_app = MagicMock()
        mock_settings = _create_mock_settings(metrics_enabled=True)

        with (
            patch("app.observability.metrics.get_settings", return_value=mock_settings),
            patch("app.observability.metrics.Instrumentator") as mock_instr_class,
            patch("app.observability.metrics.metrics") as mock_metrics_module,
        ):
            mock_instrumentator = MagicMock()
            mock_instr_class.return_value = mock_instrumentator
            mock_instrumentator.add.return_value = mock_instrumentator

            setup_metrics(mock_app)

            mock_metrics_module.response_size.assert_called()

    def test_configures_status_code_grouping(self) -> None:
        """Should configure status code grouping."""
        mock_app = MagicMock()
        mock_settings = _create_mock_settings(metrics_enabled=True)

        with (
            patch("app.observability.metrics.get_settings", return_value=mock_settings),
            patch("app.observability.metrics.Instrumentator") as mock_instr_class,
        ):
            mock_instrumentator = MagicMock()
            mock_instr_class.return_value = mock_instrumentator
            mock_instrumentator.add.return_value = mock_instrumentator

            setup_metrics(mock_app)

            call_kwargs = mock_instr_class.call_args.kwargs
            assert call_kwargs["should_group_status_codes"] is True

    def test_configures_inprogress_tracking(self) -> None:
        """Should configure in-progress request tracking."""
        mock_app = MagicMock()
        mock_settings = _create_mock_settings(metrics_enabled=True)

        with (
            patch("app.observability.metrics.get_settings", return_value=mock_settings),
            patch("app.observability.metrics.Instrumentator") as mock_instr_class,
        ):
            mock_instrumentator = MagicMock()
            mock_instr_class.return_value = mock_instrumentator
            mock_instrumentator.add.return_value = mock_instrumentator

            setup_metrics(mock_app)

            call_kwargs = mock_instr_class.call_args.kwargs
            assert call_kwargs["should_instrument_requests_inprogress"] is True
            assert call_kwargs["inprogress_name"] == "http_requests_inprogress"

    def test_expose_includes_in_schema(self) -> None:
        """Should include metrics endpoint in OpenAPI schema."""
        mock_app = MagicMock()
        mock_settings = _create_mock_settings(metrics_enabled=True)

        with (
            patch("app.observability.metrics.get_settings", return_value=mock_settings),
            patch("app.observability.metrics.Instrumentator") as mock_instr_class,
        ):
            mock_instrumentator = MagicMock()
            mock_instr_class.return_value = mock_instrumentator
            mock_instrumentator.add.return_value = mock_instrumentator

            setup_metrics(mock_app)

            call_kwargs = mock_instrumentator.expose.call_args.kwargs
            assert call_kwargs["include_in_schema"] is True

    def test_expose_uses_monitoring_tag(self) -> None:
        """Should use 'Monitoring' tag for OpenAPI documentation."""
        mock_app = MagicMock()
        mock_settings = _create_mock_settings(metrics_enabled=True)

        with (
            patch("app.observability.metrics.get_settings", return_value=mock_settings),
            patch("app.observability.metrics.Instrumentator") as mock_instr_class,
        ):
            mock_instrumentator = MagicMock()
            mock_instr_class.return_value = mock_instrumentator
            mock_instrumentator.add.return_value = mock_instrumentator

            setup_metrics(mock_app)

            call_kwargs = mock_instrumentator.expose.call_args.kwargs
            assert call_kwargs["tags"] == ["Monitoring"]

    def test_adds_three_metric_types(self) -> None:
        """Should add default, request_size, and response_size metrics."""
        mock_app = MagicMock()
        mock_settings = _create_mock_settings(metrics_enabled=True)

        with (
            patch("app.observability.metrics.get_settings", return_value=mock_settings),
            patch("app.observability.metrics.Instrumentator") as mock_instr_class,
            patch("app.observability.metrics.metrics"),
        ):
            mock_instrumentator = MagicMock()
            mock_instr_class.return_value = mock_instrumentator
            mock_instrumentator.add.return_value = mock_instrumentator

            setup_metrics(mock_app)

            # Should have called add() three times
            assert mock_instrumentator.add.call_count == 3

    def test_excludes_documentation_endpoints(self) -> None:
        """Should exclude /docs, /redoc, /openapi.json from instrumentation."""
        mock_app = MagicMock()
        mock_settings = _create_mock_settings(metrics_enabled=True)

        with (
            patch("app.observability.metrics.get_settings", return_value=mock_settings),
            patch("app.observability.metrics.Instrumentator") as mock_instr_class,
        ):
            mock_instrumentator = MagicMock()
            mock_instr_class.return_value = mock_instrumentator
            mock_instrumentator.add.return_value = mock_instrumentator

            setup_metrics(mock_app)

            call_kwargs = mock_instr_class.call_args.kwargs
            excluded = call_kwargs["excluded_handlers"]
            assert "/docs" in excluded
            assert "/redoc" in excluded
            assert "/openapi.json" in excluded
