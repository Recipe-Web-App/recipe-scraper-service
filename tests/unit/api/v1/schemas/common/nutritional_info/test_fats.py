"""Unit tests for the Fats schema as well as its logic and constraints."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.common.nutritional_info.fats import Fats

_field_list = [
    "fat_g",
    "saturated_fat_g",
    "monounsaturated_fat_g",
    "polyunsaturated_fat_g",
    "omega_3_fat_g",
    "omega_6_fat_g",
    "omega_9_fat_g",
    "trans_fat_g",
]


@pytest.mark.unit
def test_fats_instantiation() -> None:
    """Test Fats can be instantiated with all fields."""
    # Arrange
    fat_g_val = Decimal("1.1")
    saturated_fat_g_val = Decimal("2.2")
    monounsaturated_fat_g_val = Decimal("3.3")
    polyunsaturated_fat_g_val = Decimal("4.4")
    omega_3_fat_g_val = Decimal("5.5")
    omega_6_fat_g_val = Decimal("6.6")
    omega_9_fat_g_val = Decimal("7.7")
    trans_fat_g_val = Decimal("8.8")

    # Act
    fats = Fats(
        fat_g=fat_g_val,
        saturated_fat_g=saturated_fat_g_val,
        monounsaturated_fat_g=monounsaturated_fat_g_val,
        polyunsaturated_fat_g=polyunsaturated_fat_g_val,
        omega_3_fat_g=omega_3_fat_g_val,
        omega_6_fat_g=omega_6_fat_g_val,
        omega_9_fat_g=omega_9_fat_g_val,
        trans_fat_g=trans_fat_g_val,
    )

    # Assert
    assert fats.fat_g == fat_g_val
    assert fats.saturated_fat_g == saturated_fat_g_val
    assert fats.monounsaturated_fat_g == monounsaturated_fat_g_val
    assert fats.polyunsaturated_fat_g == polyunsaturated_fat_g_val
    assert fats.omega_3_fat_g == omega_3_fat_g_val
    assert fats.omega_6_fat_g == omega_6_fat_g_val
    assert fats.omega_9_fat_g == omega_9_fat_g_val
    assert fats.trans_fat_g == trans_fat_g_val


@pytest.mark.unit
def test_fats_model_copy() -> None:
    """Test that model_copy produces a new, equal object with all fields."""
    # Arrange
    fats = Fats(
        fat_g=Decimal("1.1"),
        saturated_fat_g=Decimal("2.2"),
        monounsaturated_fat_g=Decimal("3.3"),
        polyunsaturated_fat_g=Decimal("4.4"),
        omega_3_fat_g=Decimal("5.5"),
        omega_6_fat_g=Decimal("6.6"),
        omega_9_fat_g=Decimal("7.7"),
        trans_fat_g=Decimal("8.8"),
    )

    # Act
    fats_copy = fats.model_copy()

    # Assert
    assert fats == fats_copy
    assert fats is not fats_copy
    for field in _field_list:
        assert getattr(fats, field) == getattr(fats_copy, field)


@pytest.mark.unit
def test_fats_equality() -> None:
    """Test that two Fats objects with the same data for all fields are equal."""
    # Arrange
    kwargs = {
        "fat_g": Decimal("1.1"),
        "saturated_fat_g": Decimal("2.2"),
        "monounsaturated_fat_g": Decimal("3.3"),
        "polyunsaturated_fat_g": Decimal("4.4"),
        "omega_3_fat_g": Decimal("5.5"),
        "omega_6_fat_g": Decimal("6.6"),
        "omega_9_fat_g": Decimal("7.7"),
        "trans_fat_g": Decimal("8.8"),
    }

    # Act
    fats1 = Fats(**kwargs)
    fats2 = Fats(**kwargs)

    # Assert
    assert fats1 == fats2


@pytest.mark.unit
def test_fats_serialization() -> None:
    """Test that model_dump produces a serializable dict with all fields."""
    # Arrange
    fats = Fats(
        fat_g=Decimal("1.1"),
        saturated_fat_g=Decimal("2.2"),
        monounsaturated_fat_g=Decimal("3.3"),
        polyunsaturated_fat_g=Decimal("4.4"),
        omega_3_fat_g=Decimal("5.5"),
        omega_6_fat_g=Decimal("6.6"),
        omega_9_fat_g=Decimal("7.7"),
        trans_fat_g=Decimal("8.8"),
    )

    # Act
    data = fats.model_dump()

    # Assert
    assert isinstance(data, dict)
    for field in _field_list:
        assert data[field] == getattr(fats, field)


@pytest.mark.unit
def test_fats_deserialization() -> None:
    """Test that model_validate reconstructs a Fats object from dict with all fields."""
    # Arrange
    data = {
        "fat_g": Decimal("1.1"),
        "saturated_fat_g": Decimal("2.2"),
        "monounsaturated_fat_g": Decimal("3.3"),
        "polyunsaturated_fat_g": Decimal("4.4"),
        "omega_3_fat_g": Decimal("5.5"),
        "omega_6_fat_g": Decimal("6.6"),
        "omega_9_fat_g": Decimal("7.7"),
        "trans_fat_g": Decimal("8.8"),
    }

    # Act
    fats = Fats.model_validate(data)

    # Assert
    assert isinstance(fats, Fats)
    for field in _field_list:
        assert getattr(fats, field) == data[field]


@pytest.mark.unit
def test_fats_addition() -> None:
    """Test the __add__ method of Fats sums all fields correctly."""
    # Arrange
    f1 = Fats(
        fat_g=Decimal("1.0"),
        saturated_fat_g=Decimal("2.0"),
        monounsaturated_fat_g=Decimal("3.0"),
        polyunsaturated_fat_g=Decimal("4.0"),
        omega_3_fat_g=Decimal("5.0"),
        omega_6_fat_g=Decimal("6.0"),
        omega_9_fat_g=Decimal("7.0"),
        trans_fat_g=Decimal("8.0"),
    )
    f2 = Fats(
        fat_g=Decimal("0.5"),
        saturated_fat_g=Decimal("0.5"),
        monounsaturated_fat_g=Decimal("0.5"),
        polyunsaturated_fat_g=Decimal("0.5"),
        omega_3_fat_g=Decimal("0.5"),
        omega_6_fat_g=Decimal("0.5"),
        omega_9_fat_g=Decimal("0.5"),
        trans_fat_g=Decimal("0.5"),
    )

    # Act
    result = f1 + f2

    # Assert
    assert result.fat_g == (f1.fat_g + f2.fat_g)  # type: ignore[operator]
    assert result.saturated_fat_g == (f1.saturated_fat_g + f2.saturated_fat_g)  # type: ignore[operator]
    assert result.monounsaturated_fat_g == (
        f1.monounsaturated_fat_g + f2.monounsaturated_fat_g  # type: ignore[operator]
    )
    assert result.polyunsaturated_fat_g == (
        f1.polyunsaturated_fat_g + f2.polyunsaturated_fat_g  # type: ignore[operator]
    )
    assert result.omega_3_fat_g == (f1.omega_3_fat_g + f2.omega_3_fat_g)  # type: ignore[operator]
    assert result.omega_6_fat_g == (f1.omega_6_fat_g + f2.omega_6_fat_g)  # type: ignore[operator]
    assert result.omega_9_fat_g == (f1.omega_9_fat_g + f2.omega_9_fat_g)  # type: ignore[operator]
    assert result.trans_fat_g == (f1.trans_fat_g + f2.trans_fat_g)  # type: ignore[operator]


@pytest.mark.unit
def test_fats_addition_with_none_on_right_side() -> None:
    """Test the __add__ method of Fats handles with all None vals on the right side."""
    # Arrange
    f1 = Fats(
        fat_g=Decimal("1.0"),
        saturated_fat_g=Decimal("2.0"),
        monounsaturated_fat_g=Decimal("3.0"),
        polyunsaturated_fat_g=Decimal("4.0"),
        omega_3_fat_g=Decimal("5.0"),
        omega_6_fat_g=Decimal("6.0"),
        omega_9_fat_g=Decimal("7.0"),
        trans_fat_g=Decimal("8.0"),
    )
    f2 = Fats(
        fat_g=None,
        saturated_fat_g=None,
        monounsaturated_fat_g=None,
        polyunsaturated_fat_g=None,
        omega_3_fat_g=None,
        omega_6_fat_g=None,
        omega_9_fat_g=None,
        trans_fat_g=None,
    )

    # Act
    result = f1 + f2

    # Assert
    assert result.fat_g == f1.fat_g
    assert result.saturated_fat_g == f1.saturated_fat_g
    assert result.monounsaturated_fat_g == f1.monounsaturated_fat_g
    assert result.polyunsaturated_fat_g == f1.polyunsaturated_fat_g
    assert result.omega_3_fat_g == f1.omega_3_fat_g
    assert result.omega_6_fat_g == f1.omega_6_fat_g
    assert result.omega_9_fat_g == f1.omega_9_fat_g
    assert result.trans_fat_g == f1.trans_fat_g


@pytest.mark.unit
def test_fats_addition_with_none_on_both_sides() -> None:
    """Test the __add__ method of Fats handles with all None vals on both sides."""
    # Arrange
    f1 = Fats(
        fat_g=None,
        saturated_fat_g=None,
        monounsaturated_fat_g=None,
        polyunsaturated_fat_g=None,
        omega_3_fat_g=None,
        omega_6_fat_g=None,
        omega_9_fat_g=None,
        trans_fat_g=None,
    )
    f2 = f1.model_copy()

    # Act
    result = f1 + f2

    # Assert
    assert result.fat_g is None
    assert result.saturated_fat_g is None
    assert result.monounsaturated_fat_g is None
    assert result.polyunsaturated_fat_g is None
    assert result.omega_3_fat_g is None
    assert result.omega_6_fat_g is None
    assert result.omega_9_fat_g is None
    assert result.trans_fat_g is None


@pytest.mark.unit
def test_fats_default_values() -> None:
    """Test Fats can be instantiated with default values."""
    # Arrange and Act
    fats = Fats()

    # Assert
    for field in _field_list:
        assert getattr(fats, field) is None


@pytest.mark.unit
def test_fats_constraints() -> None:
    """Test Fats schema constraints."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        Fats(fat_g=Decimal("1.0"), extra_field=123)  # type: ignore[call-arg]


@pytest.mark.unit
@pytest.mark.parametrize(
    "field",
    _field_list,
)
def test_fats_field_constraints(field: str) -> None:
    """Test each Fats field for negative and invalid type constraints."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        Fats(**{field: Decimal("-1.0")})

    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        Fats(**{field: "not-a-decimal"})
