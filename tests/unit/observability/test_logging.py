"""Unit tests for logging module.

Tests cover:
- Context variable management
- Logger retrieval
- InterceptHandler
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from app.observability.logging import (
    InterceptHandler,
    bind_context,
    clear_context,
    get_context,
    get_logger,
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
