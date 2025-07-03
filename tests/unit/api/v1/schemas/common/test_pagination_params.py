"""Unit tests for the PaginationParams schema and its constraints."""

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.common.pagination_params import PaginationParams

_field_list = list(PaginationParams.model_fields.keys())


@pytest.mark.unit
def test_pagination_params_instantiation() -> None:
    """Test PaginationParams can be instantiated with all fields."""
    # Arrange
    limit = 10
    offset = 5
    count_only = True

    # Act
    params = PaginationParams(limit=limit, offset=offset, count_only=count_only)

    # Assert
    assert params.limit == limit
    assert params.offset == offset
    assert params.count_only is True


@pytest.mark.unit
def test_pagination_params_model_copy() -> None:
    """Test that model_copy produces a new, equal object with all fields."""
    # Arrange
    params = PaginationParams(limit=10, offset=5, count_only=True)

    # Act
    params_copy = params.model_copy()

    # Assert
    assert params == params_copy
    assert params is not params_copy
    for field in _field_list:
        assert getattr(params, field) == getattr(params_copy, field)


@pytest.mark.unit
def test_pagination_params_equality() -> None:
    """Test that two PaginationParams objects with the same data are equal."""
    # Arrange
    kwargs1 = {"limit": 10, "offset": 5, "count_only": True}
    kwargs2 = {"limit": 20, "offset": 0, "count_only": False}

    # Act
    p1 = PaginationParams(**kwargs1)
    p2 = PaginationParams(**kwargs1)
    p3 = PaginationParams(**kwargs2)

    # Assert
    assert p1 == p2
    assert p1 != p3


@pytest.mark.unit
def test_pagination_params_serialization() -> None:
    """Test that model_dump produces a serializable dict with all fields."""
    # Arrange
    params = PaginationParams(limit=10, offset=5, count_only=True)

    # Act
    data = params.model_dump()

    # Assert
    assert isinstance(data, dict)
    for field in _field_list:
        assert data[field] == getattr(params, field)


@pytest.mark.unit
def test_pagination_params_deserialization() -> None:
    """Test that model_validate reconstructs an object from dict with all fields."""
    # Arrange
    data = {"limit": 10, "offset": 5, "count_only": True}

    # Act
    params = PaginationParams.model_validate(data)

    # Assert
    assert isinstance(params, PaginationParams)
    for field in _field_list:
        assert getattr(params, field) == data[field]


@pytest.mark.unit
def test_pagination_params_default_values() -> None:
    """Test PaginationParams can be instantiated with default values."""
    # Arrange
    default_limit = 50
    default_offset = 0
    default_count_only = False

    # Act
    params = PaginationParams()

    # Assert
    assert params.limit == default_limit
    assert params.offset == default_offset
    assert params.count_only is default_count_only


@pytest.mark.unit
def test_pagination_params_constraints() -> None:
    """Test PaginationParams schema constraints."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        PaginationParams(limit=0)  # ge=1
    with pytest.raises(ValidationError):
        PaginationParams(offset=-1)  # ge=0
    with pytest.raises(ValidationError):
        PaginationParams(limit="not-an-int")
    with pytest.raises(ValidationError):
        PaginationParams(offset="not-an-int")
    with pytest.raises(ValidationError):
        PaginationParams(count_only="not-a-bool")
    with pytest.raises(ValidationError):
        PaginationParams(limit=10, extra_field=123)  # type: ignore[call-arg]
