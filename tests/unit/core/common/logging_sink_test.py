"""Unit tests for the LoggingSink class in app.core.config.logging_sink."""

import sys
from types import SimpleNamespace

import pytest

from app.core.config.logging_sink import LoggingSink


@pytest.mark.unit
def test_logging_sink_all_fields() -> None:
    """Test LoggingSink with all fields set."""
    # Arrange
    sink = sys.stdout
    level = "DEBUG"
    serialize = True
    rotation = "1 week"
    retention = "30 days"
    compression = "zip"
    backtrace = True
    diagnose = False
    enqueue = True
    filter_val = {"module": "test"}
    colorize = True
    catch = False

    # Act
    logging_sink = LoggingSink(
        sink=sink,
        level=level,
        serialize=serialize,
        rotation=rotation,
        retention=retention,
        compression=compression,
        backtrace=backtrace,
        diagnose=diagnose,
        enqueue=enqueue,
        filter=filter_val,
        colorize=colorize,
        catch=catch,
    )

    # Assert
    assert logging_sink.sink is sink
    assert logging_sink.level == level
    assert logging_sink.serialize is serialize
    assert logging_sink.rotation == rotation
    assert logging_sink.retention == retention
    assert logging_sink.compression == compression
    assert logging_sink.backtrace is backtrace
    assert logging_sink.diagnose is diagnose
    assert logging_sink.enqueue is enqueue
    assert logging_sink.filter == filter_val
    assert logging_sink.colorize is colorize
    assert logging_sink.catch is catch


@pytest.mark.unit
def test_logging_sink_defaults() -> None:
    """Test LoggingSink with only required field set."""
    # Arrange
    sink = "test.log"

    # Act
    logging_sink = LoggingSink(sink=sink)

    # Assert
    assert logging_sink.sink == sink
    assert logging_sink.level is None
    assert logging_sink.serialize is None
    assert logging_sink.rotation is None
    assert logging_sink.retention is None
    assert logging_sink.compression is None
    assert logging_sink.backtrace is None
    assert logging_sink.diagnose is None
    assert logging_sink.enqueue is None
    assert logging_sink.filter is None
    assert logging_sink.colorize is None
    assert logging_sink.catch is None


@pytest.mark.unit
def test_logging_sink_immutable() -> None:
    """Test LoggingSink is immutable (frozen dataclass)."""
    # Arrange
    logging_sink = LoggingSink(sink="test.log", level="INFO")

    # Act and Assert
    with pytest.raises(AttributeError, match="cannot assign to field"):
        # Attempt to mutate a frozen dataclass should raise
        logging_sink.__setattr__("level", "DEBUG")


@pytest.mark.unit
def test_logging_sink_equality() -> None:
    """Test LoggingSink equality and inequality."""
    # Arrange
    sink1 = LoggingSink(sink="a.log", level="INFO")
    sink2 = LoggingSink(sink="a.log", level="INFO")
    sink3 = LoggingSink(sink="b.log", level="DEBUG")

    # Act and Assert
    assert sink1 == sink2
    assert sink1 != sink3


@pytest.mark.unit
def test_logging_sink_from_dict_all_fields() -> None:
    """Test from_dict with all fields set."""
    # Arrange
    data = {
        "sink": sys.stderr,
        "level": "WARNING",
        "serialize": False,
        "rotation": "1 day",
        "retention": "7 days",
        "compression": "gz",
        "backtrace": False,
        "diagnose": True,
        "enqueue": False,
        "filter": "myfilter",
        "colorize": False,
        "catch": True,
    }

    # Act
    logging_sink = LoggingSink.from_dict(data)

    # Assert
    assert logging_sink.sink is sys.stderr
    assert logging_sink.level == "WARNING"
    assert logging_sink.serialize is False
    assert logging_sink.rotation == "1 day"
    assert logging_sink.retention == "7 days"
    assert logging_sink.compression == "gz"
    assert logging_sink.backtrace is False
    assert logging_sink.diagnose is True
    assert logging_sink.enqueue is False
    assert logging_sink.filter == "myfilter"
    assert logging_sink.colorize is False
    assert logging_sink.catch is True


@pytest.mark.unit
def test_logging_sink_from_dict_partial() -> None:
    """Test from_dict with only required field set."""
    # Arrange
    data = {"sink": "partial.log"}

    # Act
    logging_sink = LoggingSink.from_dict(data)

    # Assert
    assert logging_sink.sink == "partial.log"
    assert logging_sink.level is None
    assert logging_sink.serialize is None
    assert logging_sink.rotation is None
    assert logging_sink.retention is None
    assert logging_sink.compression is None
    assert logging_sink.backtrace is None
    assert logging_sink.diagnose is None
    assert logging_sink.enqueue is None
    assert logging_sink.filter is None
    assert logging_sink.colorize is None
    assert logging_sink.catch is None


@pytest.mark.unit
def test_logging_sink_filter_callable() -> None:
    """Test LoggingSink with a callable filter."""

    # Arrange
    def filter_func(record: object) -> bool:
        del record
        return True

    logging_sink = LoggingSink(sink="test.log", filter=filter_func)

    # Act
    filter_callable = logging_sink.filter
    # Assert
    assert callable(filter_callable)
    assert filter_callable is not None
    assert filter_callable(SimpleNamespace())


@pytest.mark.unit
def test_logging_sink_filter_dict() -> None:
    """Test LoggingSink with a dict filter."""
    # Arrange
    filter_dict = {"module": "foo"}
    logging_sink = LoggingSink(sink="test.log", filter=filter_dict)

    # Act and Assert
    assert logging_sink.filter == filter_dict


@pytest.mark.unit
def test_logging_sink_filter_str() -> None:
    """Test LoggingSink with a string filter."""
    # Arrange
    filter_str = "myfilter"
    logging_sink = LoggingSink(sink="test.log", filter=filter_str)

    # Act and Assert
    assert logging_sink.filter == filter_str


@pytest.mark.unit
def test_logging_sink_repr_and_str() -> None:
    """Test __repr__ and __str__ methods."""
    # Arrange
    logging_sink = LoggingSink(sink="test.log", level="INFO")

    # Act
    r = repr(logging_sink)
    s = str(logging_sink)

    # Assert
    assert "test.log" in r
    assert "INFO" in r
    assert "test.log" in s
    assert "INFO" in s


@pytest.mark.unit
def test_logging_sink_from_dict_invalid_key() -> None:
    """Test from_dict ignores extra keys."""
    # Arrange
    data = {"sink": "foo", "invalid": 123}

    # Act
    logging_sink = LoggingSink.from_dict(data)

    # Assert
    assert logging_sink.sink == "foo"
    # Extra keys are ignored
    assert not hasattr(logging_sink, "invalid")
