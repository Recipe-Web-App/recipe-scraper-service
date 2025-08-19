"""Unit tests for the logging middleware."""

import logging
from unittest.mock import Mock, patch

import pytest

from app.middleware.logging_middleware import InterceptHandler


class TestInterceptHandler:
    """Unit tests for the InterceptHandler class."""

    @pytest.mark.unit
    def test_intercept_handler_initialization(self) -> None:
        """Test that InterceptHandler initializes correctly."""
        # Act
        handler = InterceptHandler()

        # Assert
        assert isinstance(handler, logging.Handler)

    @pytest.mark.unit
    def test_emit_with_valid_log_level(self) -> None:
        """Test emit method with a valid log level."""
        # Arrange
        handler = InterceptHandler()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Act
        with patch("app.middleware.logging_middleware.uvicorn_logger") as mock_logger:
            mock_level = Mock()
            mock_level.name = "INFO"
            mock_logger.level.return_value = mock_level
            mock_logger.opt.return_value = mock_logger

            handler.emit(record)

        # Assert
        mock_logger.level.assert_called_once_with("INFO")
        mock_logger.opt.assert_called_once_with(depth=6)
        mock_logger.log.assert_called_once_with("INFO", "Test message")

    @pytest.mark.unit
    def test_emit_with_invalid_log_level(self) -> None:
        """Test emit method with an invalid log level that raises ValueError."""
        # Arrange
        handler = InterceptHandler()
        record = logging.LogRecord(
            name="test_logger",
            level=999,  # Invalid level
            pathname="test.py",
            lineno=10,
            msg="Test message with invalid level",
            args=(),
            exc_info=None,
        )

        # Act
        with patch("app.middleware.logging_middleware.uvicorn_logger") as mock_logger:
            mock_logger.level.side_effect = ValueError("Invalid level")
            mock_logger.opt.return_value = mock_logger

            handler.emit(record)

        # Assert
        # First it tries with record.levelname (which is "Level 999" for level 999)
        mock_logger.level.assert_called_once_with("Level 999")
        mock_logger.opt.assert_called_once_with(depth=6)
        # Then it falls back to record.levelno (999) when ValueError is raised
        mock_logger.log.assert_called_once_with(999, "Test message with invalid level")

    @pytest.mark.unit
    def test_emit_with_formatted_message(self) -> None:
        """Test emit method with a log record that has formatting arguments."""
        # Arrange
        handler = InterceptHandler()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=20,
            msg="Error occurred: %s",
            args=("connection failed",),
            exc_info=None,
        )

        # Act
        with patch("app.middleware.logging_middleware.uvicorn_logger") as mock_logger:
            mock_level = Mock()
            mock_level.name = "ERROR"
            mock_logger.level.return_value = mock_level
            mock_logger.opt.return_value = mock_logger

            handler.emit(record)

        # Assert
        mock_logger.level.assert_called_once_with("ERROR")
        mock_logger.opt.assert_called_once_with(depth=6)
        expected_msg = "Error occurred: connection failed"
        mock_logger.log.assert_called_once_with("ERROR", expected_msg)

    @pytest.mark.unit
    def test_emit_with_different_log_levels(self) -> None:
        """Test emit method with different standard log levels."""
        # Arrange
        handler = InterceptHandler()
        test_cases = [
            (logging.DEBUG, "DEBUG"),
            (logging.INFO, "INFO"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
            (logging.CRITICAL, "CRITICAL"),
        ]

        for level_num, level_name in test_cases:
            record = logging.LogRecord(
                name="test_logger",
                level=level_num,
                pathname="test.py",
                lineno=10,
                msg=f"Test {level_name} message",
                args=(),
                exc_info=None,
            )

            # Act
            with patch(
                "app.middleware.logging_middleware.uvicorn_logger"
            ) as mock_logger:
                mock_level = Mock()
                mock_level.name = level_name
                mock_logger.level.return_value = mock_level
                mock_logger.opt.return_value = mock_logger

                handler.emit(record)

                # Assert
                mock_logger.level.assert_called_once_with(level_name)
                mock_logger.opt.assert_called_once_with(depth=6)
                expected_msg = f"Test {level_name} message"
                mock_logger.log.assert_called_once_with(level_name, expected_msg)

    @pytest.mark.unit
    def test_emit_preserves_original_log_record(self) -> None:
        """Test that emit method doesn't modify the original log record."""
        # Arrange
        handler = InterceptHandler()
        original_msg = "Original message"
        original_level = logging.INFO
        record = logging.LogRecord(
            name="test_logger",
            level=original_level,
            pathname="test.py",
            lineno=10,
            msg=original_msg,
            args=(),
            exc_info=None,
        )

        # Act
        with patch("app.middleware.logging_middleware.uvicorn_logger") as mock_logger:
            mock_level = Mock()
            mock_level.name = "INFO"
            mock_logger.level.return_value = mock_level
            mock_logger.opt.return_value = mock_logger

            handler.emit(record)

        # Assert - Original record should remain unchanged
        assert record.msg == original_msg
        assert record.levelno == original_level

    @pytest.mark.unit
    def test_emit_handles_exception_in_get_message(self) -> None:
        """Test that emit method handles exceptions in getMessage()."""
        # Arrange
        handler = InterceptHandler()
        record = Mock(spec=logging.LogRecord)
        record.levelname = "ERROR"
        record.getMessage.side_effect = Exception("getMessage failed")

        # Act & Assert - Exception should propagate since it's not handled
        with patch("app.middleware.logging_middleware.uvicorn_logger") as mock_logger:
            mock_logger.level.return_value.name = "ERROR"
            mock_logger.opt.return_value = mock_logger

            with pytest.raises(Exception, match="getMessage failed"):
                handler.emit(record)

        # Verify the logger methods were called before the exception
        mock_logger.level.assert_called_once_with("ERROR")
        mock_logger.opt.assert_called_once_with(depth=6)

    @pytest.mark.unit
    def test_emit_with_custom_logger_name(self) -> None:
        """Test emit method with different logger names."""
        # Arrange
        handler = InterceptHandler()
        logger_names = ["uvicorn.access", "uvicorn.error", "custom.logger"]

        for logger_name in logger_names:
            record = logging.LogRecord(
                name=logger_name,
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg=f"Message from {logger_name}",
                args=(),
                exc_info=None,
            )

            # Act
            with patch(
                "app.middleware.logging_middleware.uvicorn_logger"
            ) as mock_logger:
                mock_level = Mock()
                mock_level.name = "INFO"
                mock_logger.level.return_value = mock_level
                mock_logger.opt.return_value = mock_logger

                handler.emit(record)

                # Assert
                mock_logger.opt.assert_called_once_with(depth=6)
                expected_msg = f"Message from {logger_name}"
                mock_logger.log.assert_called_once_with("INFO", expected_msg)

    @pytest.mark.unit
    def test_emit_depth_parameter(self) -> None:
        """Test that emit method uses correct depth parameter for stack trace."""
        # Arrange
        handler = InterceptHandler()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test depth parameter",
            args=(),
            exc_info=None,
        )

        # Act
        with patch("app.middleware.logging_middleware.uvicorn_logger") as mock_logger:
            mock_level = Mock()
            mock_level.name = "INFO"
            mock_logger.level.return_value = mock_level
            mock_logger.opt.return_value = mock_logger

            handler.emit(record)

        # Assert - Verify that depth=6 is used consistently
        mock_logger.opt.assert_called_once_with(depth=6)
