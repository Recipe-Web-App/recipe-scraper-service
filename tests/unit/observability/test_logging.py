"""Unit tests for logging module.

Tests cover:
- Context variable management
- Logger retrieval
- InterceptHandler
- Log formatting (JSON and dev)
- File logging setup
"""

from __future__ import annotations

import logging
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.observability.logging import (
    InterceptHandler,
    _format_record,
    _format_record_dev,
    bind_context,
    clear_context,
    get_context,
    get_logger,
    setup_logging,
    unbind_context,
)


pytestmark = pytest.mark.unit


class TestContextManagement:
    """Tests for logging context management."""

    def test_bind_context_adds_values(self) -> None:
        """Should add values to context."""
        clear_context()
        bind_context(request_id="test-123", user_id="user-456")

        context = get_context()
        assert context["request_id"] == "test-123"
        assert context["user_id"] == "user-456"

    def test_bind_context_merges_with_existing(self) -> None:
        """Should merge with existing context values."""
        clear_context()
        bind_context(request_id="test-123")
        bind_context(user_id="user-456")

        context = get_context()
        assert context["request_id"] == "test-123"
        assert context["user_id"] == "user-456"

    def test_bind_context_overwrites_existing_keys(self) -> None:
        """Should overwrite existing keys."""
        clear_context()
        bind_context(request_id="old-id")
        bind_context(request_id="new-id")

        context = get_context()
        assert context["request_id"] == "new-id"

    def test_clear_context_removes_all(self) -> None:
        """Should remove all context values."""
        bind_context(request_id="test-123", user_id="user-456")
        clear_context()

        context = get_context()
        assert context == {}

    def test_unbind_context_removes_specific_keys(self) -> None:
        """Should remove only specified keys."""
        clear_context()
        bind_context(request_id="test-123", user_id="user-456", trace_id="trace-789")
        unbind_context("user_id")

        context = get_context()
        assert "request_id" in context
        assert "user_id" not in context
        assert "trace_id" in context

    def test_unbind_context_handles_missing_keys(self) -> None:
        """Should handle unbinding non-existent keys."""
        clear_context()
        bind_context(request_id="test-123")
        unbind_context("nonexistent")

        context = get_context()
        assert context == {"request_id": "test-123"}

    def test_unbind_context_multiple_keys(self) -> None:
        """Should unbind multiple keys at once."""
        clear_context()
        bind_context(a="1", b="2", c="3")
        unbind_context("a", "c")

        context = get_context()
        assert context == {"b": "2"}

    def test_get_context_returns_copy(self) -> None:
        """Should return a copy, not the original dict."""
        clear_context()
        bind_context(request_id="test-123")

        context = get_context()
        context["modified"] = "value"

        original = get_context()
        assert "modified" not in original


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger_bound_to_name(self) -> None:
        """Should return a logger bound to the given name."""
        result = get_logger("test.module")
        # Just verify it returns something (Loguru logger)
        assert result is not None

    def test_logger_is_callable(self) -> None:
        """Should return a logger with standard methods."""
        result = get_logger("test.module")
        assert callable(result.info)
        assert callable(result.debug)
        assert callable(result.warning)
        assert callable(result.error)


class TestInterceptHandler:
    """Tests for InterceptHandler."""

    def test_handler_is_logging_handler(self) -> None:
        """Should be a valid logging.Handler subclass."""
        handler = InterceptHandler()
        assert isinstance(handler, logging.Handler)

    def test_emit_forwards_to_loguru(self) -> None:
        """Should forward log records to Loguru."""
        handler = InterceptHandler()

        # Create a mock log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # The emit method should not raise
        with patch("app.observability.logging.logger") as mock_logger:
            mock_logger.level.return_value = MagicMock(name="INFO")
            mock_logger.opt.return_value = mock_logger
            handler.emit(record)

    def test_emit_handles_unknown_level(self) -> None:
        """Should handle unknown log levels."""
        handler = InterceptHandler()

        record = logging.LogRecord(
            name="test",
            level=99,  # Custom/unknown level
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.levelname = "CUSTOM"

        with patch("app.observability.logging.logger") as mock_logger:
            mock_logger.level.side_effect = ValueError("Unknown level")
            mock_logger.opt.return_value = mock_logger
            # Should not raise
            handler.emit(record)


class TestContextIsolation:
    """Tests for context isolation between tests."""

    def test_context_is_isolated_1(self) -> None:
        """Context should be isolated (test 1)."""
        clear_context()
        bind_context(test_id="test_1")
        context = get_context()
        assert context.get("test_id") == "test_1"

    def test_context_is_isolated_2(self) -> None:
        """Context should be isolated (test 2)."""
        # Should not see test_1's context
        # Note: In real async scenarios, context vars are isolated
        # For sync tests, we need to explicitly clear
        clear_context()
        context = get_context()
        assert context.get("test_id") is None


# =============================================================================
# Format Record Tests
# =============================================================================


@pytest.fixture
def mock_record() -> MagicMock:
    """Create a mock Loguru record for formatting tests."""
    record = MagicMock()
    record.__getitem__ = lambda self, key: {
        "time": datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        "level": MagicMock(name="INFO"),
        "message": "Test log message",
        "name": "test.module",
        "function": "test_function",
        "line": 42,
        "extra": {},
        "exception": None,
    }.get(key, MagicMock())
    return record


class MockLevel:
    """Mock for Loguru level object."""

    def __init__(self, name: str):
        self.name = name


class TestFormatRecord:
    """Tests for JSON format record function."""

    def test_format_record_basic(self) -> None:
        """Should format basic record to JSON."""
        clear_context()

        record = {
            "time": datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            "level": MockLevel("INFO"),
            "message": "Test message",
            "name": "test.module",
            "function": "test_func",
            "line": 10,
            "extra": {},
            "exception": None,
        }

        result = _format_record(record)

        assert "Test message" in result
        assert "INFO" in result
        assert result.endswith("\n")

    def test_format_record_with_context(self) -> None:
        """Should include context variables in JSON output."""
        clear_context()
        bind_context(request_id="req-123", user_id="user-456")

        record = {
            "time": datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            "level": MockLevel("INFO"),
            "message": "Test message",
            "name": "test.module",
            "function": "test_func",
            "line": 10,
            "extra": {},
            "exception": None,
        }

        result = _format_record(record)

        assert "req-123" in result
        assert "user-456" in result

    def test_format_record_with_exception(self) -> None:
        """Should include exception info in JSON output."""
        clear_context()

        exception = MagicMock()
        exception.type = ValueError
        exception.value = ValueError("Test error")
        exception.traceback = "traceback info"

        record = {
            "time": datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            "level": MockLevel("ERROR"),
            "message": "Error occurred",
            "name": "test.module",
            "function": "test_func",
            "line": 10,
            "extra": {},
            "exception": exception,
        }

        result = _format_record(record)

        assert "ValueError" in result
        assert "Test error" in result


class TestFormatRecordDev:
    """Tests for development format record function."""

    def test_format_record_dev_basic(self) -> None:
        """Should return format string for dev output."""
        clear_context()

        record = {
            "time": datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            "level": MockLevel("INFO"),
            "message": "Test message",
            "name": "test.module",
            "function": "test_func",
            "line": 10,
            "extra": {},
            "exception": None,
        }

        result = _format_record_dev(record)

        # Dev format returns a format string with placeholders
        assert "{time:" in result
        assert "{level:" in result
        assert "{message}" in result

    def test_format_record_dev_with_context(self) -> None:
        """Should include context in dev format string."""
        clear_context()
        bind_context(request_id="req-123", trace_id="trace-456")

        record = {
            "time": datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            "level": MockLevel("INFO"),
            "message": "Test message",
            "name": "test.module",
            "function": "test_func",
            "line": 10,
            "extra": {},
            "exception": None,
        }

        result = _format_record_dev(record)

        # Context should be included in the format string
        assert "request_id=req-123" in result
        assert "trace_id=trace-456" in result

    def test_format_record_dev_with_exception(self) -> None:
        """Should include exception placeholder when exception present."""
        clear_context()

        exception = MagicMock()
        exception.type = ValueError
        exception.value = ValueError("Test error")
        exception.traceback = "traceback"

        record = {
            "time": datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            "level": MockLevel("ERROR"),
            "message": "Error occurred",
            "name": "test.module",
            "function": "test_func",
            "line": 10,
            "extra": {},
            "exception": exception,
        }

        result = _format_record_dev(record)

        # Should include exception placeholder
        assert "{exception}" in result


# =============================================================================
# Setup Logging Tests
# =============================================================================


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_json_format(self) -> None:
        """Should configure JSON logging for production."""
        # Call setup_logging with JSON format
        setup_logging(log_level="INFO", log_format="json", is_development=False)

        # Verify logger was configured (no exception means success)
        logger = get_logger("test")
        assert logger is not None

    def test_setup_logging_text_format(self) -> None:
        """Should configure text logging for development."""
        setup_logging(log_level="DEBUG", log_format="text", is_development=True)

        logger = get_logger("test")
        assert logger is not None

    def test_setup_logging_development_mode(self) -> None:
        """Should use dev format when is_development is True."""
        # is_development=True should force dev format even with json
        setup_logging(log_level="INFO", log_format="json", is_development=True)

        logger = get_logger("test")
        assert logger is not None

    def test_setup_logging_with_file(self) -> None:
        """Should configure file logging with rotation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "logs" / "app.log"

            setup_logging(
                log_level="INFO",
                log_format="json",
                is_development=False,
                log_file=log_file,
            )

            # Directory should be created
            assert log_file.parent.exists()

    def test_setup_logging_creates_parent_directories(self) -> None:
        """Should create parent directories for log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "deep" / "nested" / "path" / "app.log"

            setup_logging(
                log_level="INFO",
                log_format="json",
                log_file=log_file,
            )

            # All parent directories should be created
            assert log_file.parent.exists()

    def test_setup_logging_intercepts_stdlib_logging(self) -> None:
        """Should intercept standard library logging."""
        setup_logging(log_level="INFO", log_format="json")

        # Standard logging should have InterceptHandler
        root_logger = logging.getLogger()
        handler_types = [type(h).__name__ for h in root_logger.handlers]
        assert "InterceptHandler" in handler_types


# =============================================================================
# InterceptHandler Frame Walking Tests
# =============================================================================


class TestInterceptHandlerFrameWalking:
    """Tests for InterceptHandler frame walking logic."""

    def test_emit_walks_frames_correctly(self) -> None:
        """Should walk frames to find correct caller depth."""
        handler = InterceptHandler()

        # Create a nested logging scenario
        def inner_function():
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="Test from inner",
                args=(),
                exc_info=None,
            )
            with patch("app.observability.logging.logger") as mock_logger:
                mock_logger.level.return_value = MagicMock(name="INFO")
                mock_opt = MagicMock()
                mock_logger.opt.return_value = mock_opt
                handler.emit(record)
                # Verify opt was called with a depth parameter
                mock_logger.opt.assert_called()
                call_kwargs = mock_logger.opt.call_args[1]
                assert "depth" in call_kwargs
                assert call_kwargs["depth"] >= 2

        def outer_function():
            inner_function()

        outer_function()

    def test_emit_handles_frame_traversal(self) -> None:
        """Should handle frame traversal when frame.f_back is called."""
        handler = InterceptHandler()

        # Mock currentframe to simulate frame walking
        mock_frame = MagicMock()
        mock_frame.f_code.co_filename = "not_logging.py"
        mock_frame.f_back = None

        with (
            patch("logging.currentframe", return_value=mock_frame),
            patch("app.observability.logging.logger") as mock_logger,
        ):
            mock_logger.level.return_value = MagicMock(name="INFO")
            mock_logger.opt.return_value = mock_logger

            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            # Should not raise even when frame walking terminates
            handler.emit(record)
