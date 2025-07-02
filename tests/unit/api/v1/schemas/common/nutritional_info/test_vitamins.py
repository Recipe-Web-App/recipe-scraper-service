"""Unit tests for the Vitamins schema as well as its logic and constraints."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.common.nutritional_info.vitams import Vitamins

_field_list = list(Vitamins.model_fields.keys())


@pytest.mark.unit
def test_vitamins_instantiation() -> None:
    """Test Vitamins can be instantiated with all fields."""
    # Arrange
    vitamin_a_mg = Decimal("1.1")
    vitamin_b6_mg = Decimal("2.2")
    vitamin_b12_mg = Decimal("3.3")
    vitamin_c_mg = Decimal("4.4")
    vitamin_d_mg = Decimal("5.5")
    vitamin_e_mg = Decimal("6.6")
    vitamin_k_mg = Decimal("7.7")

    # Act
    vitamins = Vitamins(
        vitamin_a_mg=vitamin_a_mg,
        vitamin_b6_mg=vitamin_b6_mg,
        vitamin_b12_mg=vitamin_b12_mg,
        vitamin_c_mg=vitamin_c_mg,
        vitamin_d_mg=vitamin_d_mg,
        vitamin_e_mg=vitamin_e_mg,
        vitamin_k_mg=vitamin_k_mg,
    )

    # Assert
    assert vitamins.vitamin_a_mg == vitamin_a_mg
    assert vitamins.vitamin_b6_mg == vitamin_b6_mg
    assert vitamins.vitamin_b12_mg == vitamin_b12_mg
    assert vitamins.vitamin_c_mg == vitamin_c_mg
    assert vitamins.vitamin_d_mg == vitamin_d_mg
    assert vitamins.vitamin_e_mg == vitamin_e_mg
    assert vitamins.vitamin_k_mg == vitamin_k_mg


@pytest.mark.unit
def test_vitamins_model_copy() -> None:
    """Test that model_copy produces a new, equal object with all fields."""
    # Arrange
    vitamins = Vitamins(
        vitamin_a_mg=Decimal("1.1"),
        vitamin_b6_mg=Decimal("2.2"),
        vitamin_b12_mg=Decimal("3.3"),
        vitamin_c_mg=Decimal("4.4"),
        vitamin_d_mg=Decimal("5.5"),
        vitamin_e_mg=Decimal("6.6"),
        vitamin_k_mg=Decimal("7.7"),
    )

    # Act
    vitamins_copy = vitamins.model_copy()

    # Assert
    assert vitamins == vitamins_copy
    assert vitamins is not vitamins_copy
    for field in _field_list:
        assert getattr(vitamins, field) == getattr(vitamins_copy, field)


@pytest.mark.unit
def test_vitamins_equality() -> None:
    """Test that two Vitamins objects with the same data are equal."""
    # Arrange
    kwargs1 = {
        "vitamin_a_mg": Decimal("1.1"),
        "vitamin_b6_mg": Decimal("2.2"),
        "vitamin_b12_mg": Decimal("3.3"),
        "vitamin_c_mg": Decimal("4.4"),
        "vitamin_d_mg": Decimal("5.5"),
        "vitamin_e_mg": Decimal("6.6"),
        "vitamin_k_mg": Decimal("7.7"),
    }
    kwargs2 = {
        "vitamin_a_mg": Decimal("8.8"),
        "vitamin_b6_mg": Decimal("9.9"),
        "vitamin_b12_mg": Decimal("10.1"),
        "vitamin_c_mg": Decimal("11.2"),
        "vitamin_d_mg": Decimal("12.3"),
        "vitamin_e_mg": Decimal("13.4"),
        "vitamin_k_mg": Decimal("14.5"),
    }

    # Act
    v1 = Vitamins(**kwargs1)
    v2 = Vitamins(**kwargs1)
    v3 = Vitamins(**kwargs2)

    # Assert
    assert v1 == v2
    assert v1 != v3


@pytest.mark.unit
def test_vitamins_serialization() -> None:
    """Test that model_dump produces a serializable dict with all fields."""
    # Arrange
    vitamins = Vitamins(
        vitamin_a_mg=Decimal("1.1"),
        vitamin_b6_mg=Decimal("2.2"),
        vitamin_b12_mg=Decimal("3.3"),
        vitamin_c_mg=Decimal("4.4"),
        vitamin_d_mg=Decimal("5.5"),
        vitamin_e_mg=Decimal("6.6"),
        vitamin_k_mg=Decimal("7.7"),
    )

    # Act
    data = vitamins.model_dump()

    # Assert
    assert isinstance(data, dict)
    for field in _field_list:
        assert data[field] == getattr(vitamins, field)


@pytest.mark.unit
def test_vitamins_deserialization() -> None:
    """Test that model_validate reconstructs an object from dict with all fields."""
    # Arrange
    data = {
        "vitamin_a_mg": Decimal("1.1"),
        "vitamin_b6_mg": Decimal("2.2"),
        "vitamin_b12_mg": Decimal("3.3"),
        "vitamin_c_mg": Decimal("4.4"),
        "vitamin_d_mg": Decimal("5.5"),
        "vitamin_e_mg": Decimal("6.6"),
        "vitamin_k_mg": Decimal("7.7"),
    }

    # Act
    vitamins = Vitamins.model_validate(data)

    # Assert
    assert isinstance(vitamins, Vitamins)
    for field in _field_list:
        assert getattr(vitamins, field) == data[field]


@pytest.mark.unit
def test_vitamins_addition() -> None:
    """Test the __add__ method of Vitamins sums all fields correctly."""
    # Arrange
    v1 = Vitamins(
        vitamin_a_mg=Decimal("1.0"),
        vitamin_b6_mg=Decimal("2.0"),
        vitamin_b12_mg=Decimal("3.0"),
        vitamin_c_mg=Decimal("4.0"),
        vitamin_d_mg=Decimal("5.0"),
        vitamin_e_mg=Decimal("6.0"),
        vitamin_k_mg=Decimal("7.0"),
    )
    v2 = Vitamins(
        vitamin_a_mg=Decimal("0.5"),
        vitamin_b6_mg=Decimal("0.5"),
        vitamin_b12_mg=Decimal("0.5"),
        vitamin_c_mg=Decimal("0.5"),
        vitamin_d_mg=Decimal("0.5"),
        vitamin_e_mg=Decimal("0.5"),
        vitamin_k_mg=Decimal("0.5"),
    )

    # Act
    result = v1 + v2

    # Assert
    assert result.vitamin_a_mg == v1.vitamin_a_mg + v2.vitamin_a_mg  # type: ignore[operator]
    assert result.vitamin_b6_mg == v1.vitamin_b6_mg + v2.vitamin_b6_mg  # type: ignore[operator]
    assert result.vitamin_b12_mg == v1.vitamin_b12_mg + v2.vitamin_b12_mg  # type: ignore[operator]
    assert result.vitamin_c_mg == v1.vitamin_c_mg + v2.vitamin_c_mg  # type: ignore[operator]
    assert result.vitamin_d_mg == v1.vitamin_d_mg + v2.vitamin_d_mg  # type: ignore[operator]
    assert result.vitamin_e_mg == v1.vitamin_e_mg + v2.vitamin_e_mg  # type: ignore[operator]
    assert result.vitamin_k_mg == v1.vitamin_k_mg + v2.vitamin_k_mg  # type: ignore[operator]


@pytest.mark.unit
def test_vitamins_addition_with_none_on_one_side() -> None:
    """Test the __add__ method of Vitamins handles all None values on one side."""
    # Arrange
    v1 = Vitamins(
        vitamin_a_mg=Decimal("1.0"),
        vitamin_b6_mg=Decimal("2.0"),
        vitamin_b12_mg=Decimal("3.0"),
        vitamin_c_mg=Decimal("4.0"),
        vitamin_d_mg=Decimal("5.0"),
        vitamin_e_mg=Decimal("6.0"),
        vitamin_k_mg=Decimal("7.0"),
    )
    v2 = Vitamins()

    # Act
    result = v1 + v2

    # Assert
    for field in _field_list:
        assert getattr(result, field) == getattr(v1, field)


@pytest.mark.unit
def test_vitamins_addition_with_none_on_both_sides() -> None:
    """Test the __add__ method of Vitamins handles all None values on both sides."""
    # Arrange
    v1 = Vitamins()
    v2 = Vitamins()

    # Act
    result = v1 + v2

    # Assert
    for field in _field_list:
        assert getattr(result, field) is None


@pytest.mark.unit
def test_vitamins_default_values() -> None:
    """Test Vitamins can be instantiated with default values."""
    # Arrange and Act
    vitamins = Vitamins()

    # Assert
    for field in _field_list:
        assert getattr(vitamins, field) is None


@pytest.mark.unit
def test_vitamins_constraints() -> None:
    """Test Vitamins schema constraints."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        Vitamins(vitamin_a_mg=Decimal("1.0"), extra_field=123)  # type: ignore[call-arg]


@pytest.mark.unit
@pytest.mark.parametrize(
    "field",
    _field_list,
)
def test_vitamins_field_constraints(field: str) -> None:
    """Test each Vitamins field for negative and invalid type constraints."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        Vitamins(**{field: Decimal("-1.0")})
    with pytest.raises(ValidationError):
        Vitamins(**{field: "not-a-decimal"})
