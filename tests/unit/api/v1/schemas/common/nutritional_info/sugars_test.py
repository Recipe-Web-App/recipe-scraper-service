"""Unit tests for the Sugars schema as well as its logic and constraints."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.common.nutritional_info.sugars import Sugars

_field_list = list(Sugars.model_fields.keys())


@pytest.mark.unit
def test_sugars_instantiation() -> None:
    """Test Sugars can be instantiated with all fields."""
    # Arrange
    sugar_g = Decimal("1.1")
    added_sugars_g = Decimal("2.2")

    # Act
    sugars = Sugars(
        sugar_g=sugar_g,
        added_sugars_g=added_sugars_g,
    )

    # Assert
    assert sugars.sugar_g == sugar_g
    assert sugars.added_sugars_g == added_sugars_g


@pytest.mark.unit
def test_sugars_model_copy() -> None:
    """Test that model_copy produces a new, equal object with all fields."""
    # Arrange
    sugars = Sugars(
        sugar_g=Decimal("1.1"),
        added_sugars_g=Decimal("2.2"),
    )

    # Act
    sugars_copy = sugars.model_copy()

    # Assert
    assert sugars == sugars_copy
    assert sugars is not sugars_copy
    for field in _field_list:
        assert getattr(sugars, field) == getattr(sugars_copy, field)


@pytest.mark.unit
def test_sugars_equality() -> None:
    """Test that two Sugars objects with the same data are equal."""
    # Arrange
    kwargs1 = {
        "sugar_g": Decimal("1.1"),
        "added_sugars_g": Decimal("2.2"),
    }
    kwargs2 = {
        "sugar_g": Decimal("3.3"),
        "added_sugars_g": Decimal("4.4"),
    }

    # Act
    s1 = Sugars(**kwargs1)
    s2 = Sugars(**kwargs1)
    s3 = Sugars(**kwargs2)

    # Assert
    assert s1 == s2
    assert s1 != s3


@pytest.mark.unit
def test_sugars_serialization() -> None:
    """Test that model_dump produces a serializable dict with all fields."""
    # Arrange
    sugars = Sugars(
        sugar_g=Decimal("1.1"),
        added_sugars_g=Decimal("2.2"),
    )

    # Act
    data = sugars.model_dump()

    # Assert
    assert isinstance(data, dict)
    for field in _field_list:
        assert data[field] == getattr(sugars, field)


@pytest.mark.unit
def test_sugars_deserialization() -> None:
    """Test that model_validate reconstructs an object from dict with all fields."""
    # Arrange
    data = {
        "sugar_g": Decimal("1.1"),
        "added_sugars_g": Decimal("2.2"),
    }

    # Act
    sugars = Sugars.model_validate(data)

    # Assert
    assert isinstance(sugars, Sugars)
    for field in _field_list:
        assert getattr(sugars, field) == data[field]


@pytest.mark.unit
def test_sugars_addition() -> None:
    """Test the __add__ method of Sugars sums all fields correctly."""
    # Arrange
    s1 = Sugars(
        sugar_g=Decimal("1.0"),
        added_sugars_g=Decimal("2.0"),
    )
    s2 = Sugars(
        sugar_g=Decimal("0.5"),
        added_sugars_g=Decimal("0.5"),
    )

    # Act
    result = s1 + s2

    # Assert
    assert result.sugar_g == s1.sugar_g + s2.sugar_g  # type: ignore[operator]
    assert result.added_sugars_g == s1.added_sugars_g + s2.added_sugars_g  # type: ignore[operator]


@pytest.mark.unit
def test_sugars_addition_with_none_on_one_side() -> None:
    """Test the __add__ method of Sugars handles all None values on one side."""
    # Arrange
    s1 = Sugars(
        sugar_g=Decimal("1.0"),
        added_sugars_g=Decimal("2.0"),
    )
    s2 = Sugars()

    # Act
    result = s1 + s2

    # Assert
    for field in _field_list:
        assert getattr(result, field) == getattr(s1, field)


@pytest.mark.unit
def test_sugars_addition_with_none_on_both_sides() -> None:
    """Test the __add__ method of Sugars handles all None values on both sides."""
    # Arrange
    s1 = Sugars()
    s2 = Sugars()

    # Act
    result = s1 + s2

    # Assert
    for field in _field_list:
        assert getattr(result, field) is None


@pytest.mark.unit
def test_sugars_default_values() -> None:
    """Test Sugars can be instantiated with default values."""
    # Arrange and Act
    sugars = Sugars()

    # Assert
    for field in _field_list:
        assert getattr(sugars, field) is None


@pytest.mark.unit
def test_sugars_constraints() -> None:
    """Test Sugars schema constraints."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        Sugars(sugar_g=Decimal("1.0"), extra_field=123)  # type: ignore[call-arg]


@pytest.mark.unit
@pytest.mark.parametrize(
    "field",
    _field_list,
)
def test_sugars_field_constraints(field: str) -> None:
    """Test each Sugars field for negative and invalid type constraints."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        Sugars(**{field: Decimal("-1.0")})
    with pytest.raises(ValidationError):
        Sugars(**{field: "not-a-decimal"})
