"""Unit tests for app.core.logging (Loguru logging setup and helpers)."""

import logging as pylogging
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from loguru._handler import Message

import app.core.logging as logging_mod
from app.core.config.logging_sink import LoggingSink


@pytest.mark.unit
def test_get_logger_returns_loguru_logger() -> None:
    """Test get_logger returns a loguru logger instance."""
    # Arrange and Act
    logger = logging_mod.get_logger()

    # Assert
    assert hasattr(logger, "info")
    assert hasattr(logger, "bind")


@pytest.mark.unit
def test_get_logger_with_name_binds_name() -> None:
    """Test get_logger binds a custom name."""
    # Arrange and Act
    logger = logging_mod.get_logger("mock-logger")

    # Assert
    assert hasattr(logger, "info")
    assert hasattr(logger, "bind")
    # The logger should have the name bound as extra
    # Loguru only binds extra on log calls, so test with a log and capture the record
    records: list[str | None] = []

    def sink_func(msg: Message) -> None:
        records.append(msg.record["extra"].get("name"))

    logger.add(sink_func, format="{message}")
    logger.info("test")
    assert "mock-logger" in records


@pytest.mark.unit
def test_build_sink_kwargs_stdout() -> None:
    """Test _build_sink_kwargs for sys.stdout sink."""
    # Arrange
    sink = LoggingSink(
        sink="sys.stdout",
        level="DEBUG",
        serialize=True,
        backtrace=True,
        diagnose=True,
        enqueue=True,
        catch=True,
    )

    # Act
    kwargs = logging_mod._build_sink_kwargs(  # noqa: SLF001
        sink=sink,
        sink_target=sys.stdout,
        json_format="{message}",
        pretty_format="{message}",
    )

    # Assert
    assert kwargs["level"] == "DEBUG"
    assert kwargs["format"] == "{message}"
    assert kwargs["serialize"] is True
    assert kwargs["backtrace"] is True
    assert kwargs["diagnose"] is True
    assert kwargs["enqueue"] is True
    assert callable(kwargs["filter"])
    assert kwargs["colorize"] is True
    assert kwargs["catch"] is True


@pytest.mark.unit
def test_build_sink_kwargs_file_sink() -> None:
    """Test _build_sink_kwargs for file sink."""
    # Arrange
    sink = LoggingSink(
        sink="test.log",
        level="INFO",
        serialize=False,
        colorize=False,
        catch=False,
    )

    # Act
    kwargs = logging_mod._build_sink_kwargs(  # noqa: SLF001
        sink=sink,
        sink_target="test.log",
        json_format="{message}",
        pretty_format="{message}",
    )

    # Assert
    assert kwargs["level"] == "INFO"
    assert kwargs["format"] == "{message}"
    assert kwargs["serialize"] is False
    assert kwargs["colorize"] is False
    assert kwargs["catch"] is False
    assert kwargs["filter"] is None


@pytest.mark.unit
def test_configure_logging_creates_log_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test configure_logging creates log directory for file sinks."""
    # Arrange
    log_path = tmp_path / "mock-log.log"
    sink = LoggingSink(sink=str(log_path), level="INFO")
    settings_mock = MagicMock()
    settings_mock.logging_sinks = [sink]
    monkeypatch.setattr(logging_mod, "settings", settings_mock)
    monkeypatch.setattr(logging_mod, "loguru_logger", MagicMock())

    # Act
    logging_mod.configure_logging()

    # Assert
    assert log_path.parent.exists()


@pytest.mark.unit
def test_configure_logging_adds_sink(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test configure_logging adds sinks to loguru_logger."""
    # Arrange
    sink = LoggingSink(sink="sys.stdout", level="INFO")
    settings_mock = MagicMock()
    settings_mock.logging_sinks = [sink]
    loguru_logger_mock = MagicMock()
    monkeypatch.setattr(logging_mod, "settings", settings_mock)
    monkeypatch.setattr(logging_mod, "loguru_logger", loguru_logger_mock)

    # Act
    logging_mod.configure_logging()

    # Assert
    assert loguru_logger_mock.add.called
    assert loguru_logger_mock.remove.called
    assert loguru_logger_mock.configure.called


@pytest.mark.unit
def test_configure_logging_sets_patch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test configure_logging sets patcher to always add request_id."""
    # Arrange
    sink = LoggingSink(sink="sys.stdout", level="INFO")
    settings_mock = MagicMock()
    settings_mock.logging_sinks = [sink]
    loguru_logger_mock = MagicMock()
    monkeypatch.setattr(logging_mod, "settings", settings_mock)
    monkeypatch.setattr(logging_mod, "loguru_logger", loguru_logger_mock)

    # Act
    logging_mod.configure_logging()

    # Assert
    assert loguru_logger_mock.configure.called
    patcher = loguru_logger_mock.configure.call_args.kwargs.get("patcher")
    record: dict[str, dict[str, str]] = {"extra": {}}
    patcher(record)
    assert record["extra"]["request_id"] == "NULL"


@pytest.mark.unit
def test_configure_logging_sets_httpx_levels(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test configure_logging sets httpx and httpcore log levels to WARNING."""
    # Arrange
    sink = LoggingSink(sink="sys.stdout", level="INFO")
    settings_mock = MagicMock()
    settings_mock.logging_sinks = [sink]
    monkeypatch.setattr(logging_mod, "settings", settings_mock)
    monkeypatch.setattr(logging_mod, "loguru_logger", MagicMock())

    # Act
    logging_mod.configure_logging()

    # Assert
    assert pylogging.getLogger("httpx").level == pylogging.WARNING
    assert pylogging.getLogger("httpcore").level == pylogging.WARNING
    assert pylogging.getLogger("httpcore.connection").level == pylogging.WARNING
    assert pylogging.getLogger("httpcore.http11").level == pylogging.WARNING
