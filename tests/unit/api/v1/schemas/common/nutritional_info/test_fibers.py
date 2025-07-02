"""Unit tests for the Fibers schema as well as its logic and constraints."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.common.nutritional_info.fibers import Fibers

_field_list = list(Fibers.model_fields.keys())


@pytest.mark.unit
def test_fibers_instantiation() -> None:
    """Test Fibers can be instantiated with all fields."""
    # Arrange
    fiber_g_val = Decimal("1.1")
    soluble_fiber_g_val = Decimal("2.2")
    insoluble_fiber_g_val = Decimal("3.3")

    # Act
    fibers = Fibers(
        fiber_g=fiber_g_val,
        soluble_fiber_g=soluble_fiber_g_val,
        insoluble_fiber_g=insoluble_fiber_g_val,
    )

    # Assert
    assert fibers.fiber_g == fiber_g_val
    assert fibers.soluble_fiber_g == soluble_fiber_g_val
    assert fibers.insoluble_fiber_g == insoluble_fiber_g_val


@pytest.mark.unit
def test_fibers_model_copy() -> None:
    """Test that model_copy produces a new, equal object with all fields."""
    # Arrange
    fibers = Fibers(
        fiber_g=Decimal("1.1"),
        soluble_fiber_g=Decimal("2.2"),
        insoluble_fiber_g=Decimal("3.3"),
    )

    # Act
    fibers_copy = fibers.model_copy()

    # Assert
    assert fibers == fibers_copy
    assert fibers is not fibers_copy
    for field in _field_list:
        assert getattr(fibers, field) == getattr(fibers_copy, field)


@pytest.mark.unit
def test_fibers_equality() -> None:
    """Test that two Fibers objects with the same data for all fields are equal."""
    # Arrange
    kwargs1 = {
        "fiber_g": Decimal("1.1"),
        "soluble_fiber_g": Decimal("2.2"),
        "insoluble_fiber_g": Decimal("3.3"),
    }
    kwargs2 = {
        "fiber_g": Decimal("4.4"),
        "soluble_fiber_g": Decimal("5.5"),
        "insoluble_fiber_g": Decimal("6.6"),
    }

    # Act
    fibers1 = Fibers(**kwargs1)
    fibers2 = Fibers(**kwargs1)
    fibers3 = Fibers(**kwargs2)

    # Assert
    assert fibers1 == fibers2
    assert fibers1 != fibers3


@pytest.mark.unit
def test_fibers_serialization() -> None:
    """Test that model_dump produces a serializable dict with all fields."""
    # Arrange
    fibers = Fibers(
        fiber_g=Decimal("1.1"),
        soluble_fiber_g=Decimal("2.2"),
        insoluble_fiber_g=Decimal("3.3"),
    )

    # Act
    data = fibers.model_dump()

    # Assert
    assert isinstance(data, dict)
    for field in _field_list:
        assert data[field] == getattr(fibers, field)


@pytest.mark.unit
def test_fibers_deserialization() -> None:
    """Test that model_validate reconstructs an object from dict with all fields."""
    # Arrange
    data = {
        "fiber_g": Decimal("1.1"),
        "soluble_fiber_g": Decimal("2.2"),
        "insoluble_fiber_g": Decimal("3.3"),
    }

    # Act
    fibers = Fibers.model_validate(data)

    # Assert
    assert isinstance(fibers, Fibers)
    for field in _field_list:
        assert getattr(fibers, field) == data[field]


@pytest.mark.unit
def test_fibers_addition() -> None:
    """Test the __add__ method of Fibers sums all fields correctly."""
    # Arrange
    f1 = Fibers(
        fiber_g=Decimal("1.0"),
        soluble_fiber_g=Decimal("2.0"),
        insoluble_fiber_g=Decimal("3.0"),
    )
    f2 = Fibers(
        fiber_g=Decimal("0.5"),
        soluble_fiber_g=Decimal("0.5"),
        insoluble_fiber_g=Decimal("0.5"),
    )

    # Act
    result = f1 + f2

    # Assert
    assert result.fiber_g == (f1.fiber_g + f2.fiber_g)  # type: ignore[operator]
    assert result.soluble_fiber_g == (f1.soluble_fiber_g + f2.soluble_fiber_g)  # type: ignore[operator]
    assert result.insoluble_fiber_g == (f1.insoluble_fiber_g + f2.insoluble_fiber_g)  # type: ignore[operator]


@pytest.mark.unit
def test_fibers_addition_with_none_on_one_side() -> None:
    """Test the __add__ method of Fibers handles with all None vals on one side."""
    # Arrange
    f1 = Fibers(
        fiber_g=Decimal("1.0"),
        soluble_fiber_g=Decimal("2.0"),
        insoluble_fiber_g=Decimal("3.0"),
    )
    f2 = Fibers(
        fiber_g=None,
        soluble_fiber_g=None,
        insoluble_fiber_g=None,
    )

    # Act
    result = f1 + f2

    # Assert
    for field in _field_list:
        assert getattr(result, field) == getattr(f1, field)


@pytest.mark.unit
def test_fibers_addition_with_none_on_both_sides() -> None:
    """Test the __add__ method of Fibers handles with all None vals on both sides."""
    # Arrange
    f1 = Fibers()
    f2 = Fibers()

    # Act
    result = f1 + f2

    # Assert
    for field in _field_list:
        assert getattr(result, field) is None


@pytest.mark.unit
def test_fibers_default_values() -> None:
    """Test Fibers can be instantiated with default values."""
    # Arrange and Act
    fibers = Fibers()

    # Assert
    for field in _field_list:
        assert getattr(fibers, field) is None


@pytest.mark.unit
def test_fibers_constraints() -> None:
    """Test Fibers schema constraints."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        Fibers(fiber_g=Decimal("1.0"), extra_field=123)  # type: ignore[call-arg]


@pytest.mark.unit
@pytest.mark.parametrize(
    "field",
    _field_list,
)
def test_fibers_field_constraints(field: str) -> None:
    """Test each Fibers field for negative and invalid type constraints."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        Fibers(**{field: Decimal("-1.0")})

    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        Fibers(**{field: "not-a-decimal"})
