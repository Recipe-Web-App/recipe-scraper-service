"""Unit tests for the Minerals schema as well as its logic and constraints."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.common.nutritional_info.minerals import Minerals

_field_list = list(Minerals.model_fields.keys())


@pytest.mark.unit
def test_minerals_instantiation() -> None:
    """Test Minerals can be instantiated with all fields."""
    # Arrange
    calcium_mg = Decimal("1.1")
    iron_mg = Decimal("2.2")
    magnesium_mg = Decimal("3.3")
    potassium_mg = Decimal("4.4")
    sodium_mg = Decimal("5.5")
    zinc_mg = Decimal("6.6")

    # Act
    minerals = Minerals(
        calcium_mg=calcium_mg,
        iron_mg=iron_mg,
        magnesium_mg=magnesium_mg,
        potassium_mg=potassium_mg,
        sodium_mg=sodium_mg,
        zinc_mg=zinc_mg,
    )

    # Assert
    assert minerals.calcium_mg == calcium_mg
    assert minerals.iron_mg == iron_mg
    assert minerals.magnesium_mg == magnesium_mg
    assert minerals.potassium_mg == potassium_mg
    assert minerals.sodium_mg == sodium_mg
    assert minerals.zinc_mg == zinc_mg


@pytest.mark.unit
def test_minerals_model_copy() -> None:
    """Test that model_copy produces a new, equal object with all fields."""
    # Arrange
    minerals = Minerals(
        calcium_mg=Decimal("1.1"),
        iron_mg=Decimal("2.2"),
        magnesium_mg=Decimal("3.3"),
        potassium_mg=Decimal("4.4"),
        sodium_mg=Decimal("5.5"),
        zinc_mg=Decimal("6.6"),
    )

    # Act
    minerals_copy = minerals.model_copy()

    # Assert
    assert minerals == minerals_copy
    assert minerals is not minerals_copy
    for field in _field_list:
        assert getattr(minerals, field) == getattr(minerals_copy, field)


@pytest.mark.unit
def test_minerals_equality() -> None:
    """Test that two Minerals objects with the same data are equal."""
    # Arrange
    kwargs1 = {
        "calcium_mg": Decimal("1.1"),
        "iron_mg": Decimal("2.2"),
        "magnesium_mg": Decimal("3.3"),
        "potassium_mg": Decimal("4.4"),
        "sodium_mg": Decimal("5.5"),
        "zinc_mg": Decimal("6.6"),
    }
    kwargs2 = {
        "calcium_mg": Decimal("7.7"),
        "iron_mg": Decimal("8.8"),
        "magnesium_mg": Decimal("9.9"),
        "potassium_mg": Decimal("10.1"),
        "sodium_mg": Decimal("11.2"),
        "zinc_mg": Decimal("12.3"),
    }

    # Act
    m1 = Minerals(**kwargs1)
    m2 = Minerals(**kwargs1)
    m3 = Minerals(**kwargs2)

    # Assert
    assert m1 == m2
    assert m1 != m3


@pytest.mark.unit
def test_minerals_serialization() -> None:
    """Test that model_dump produces a serializable dict with all fields."""
    # Arrange
    minerals = Minerals(
        calcium_mg=Decimal("1.1"),
        iron_mg=Decimal("2.2"),
        magnesium_mg=Decimal("3.3"),
        potassium_mg=Decimal("4.4"),
        sodium_mg=Decimal("5.5"),
        zinc_mg=Decimal("6.6"),
    )

    # Act
    data = minerals.model_dump()

    # Assert
    assert isinstance(data, dict)
    for field in _field_list:
        assert data[field] == getattr(minerals, field)


@pytest.mark.unit
def test_minerals_deserialization() -> None:
    """Test that model_validate reconstructs an object from dict with all fields."""
    # Arrange
    data = {
        "calcium_mg": Decimal("1.1"),
        "iron_mg": Decimal("2.2"),
        "magnesium_mg": Decimal("3.3"),
        "potassium_mg": Decimal("4.4"),
        "sodium_mg": Decimal("5.5"),
        "zinc_mg": Decimal("6.6"),
    }

    # Act
    minerals = Minerals.model_validate(data)

    # Assert
    assert isinstance(minerals, Minerals)
    for field in _field_list:
        assert getattr(minerals, field) == data[field]


@pytest.mark.unit
def test_minerals_addition() -> None:
    """Test the __add__ method of Minerals sums all fields correctly."""
    # Arrange
    m1 = Minerals(
        calcium_mg=Decimal("1.0"),
        iron_mg=Decimal("2.0"),
        magnesium_mg=Decimal("3.0"),
        potassium_mg=Decimal("4.0"),
        sodium_mg=Decimal("5.0"),
        zinc_mg=Decimal("6.0"),
    )
    m2 = Minerals(
        calcium_mg=Decimal("0.5"),
        iron_mg=Decimal("0.5"),
        magnesium_mg=Decimal("0.5"),
        potassium_mg=Decimal("0.5"),
        sodium_mg=Decimal("0.5"),
        zinc_mg=Decimal("0.5"),
    )

    # Act
    result = m1 + m2

    # Assert
    assert result.calcium_mg == m1.calcium_mg + m2.calcium_mg  # type: ignore[operator]
    assert result.iron_mg == m1.iron_mg + m2.iron_mg  # type: ignore[operator]
    assert result.magnesium_mg == m1.magnesium_mg + m2.magnesium_mg  # type: ignore[operator]
    assert result.potassium_mg == m1.potassium_mg + m2.potassium_mg  # type: ignore[operator]
    assert result.sodium_mg == m1.sodium_mg + m2.sodium_mg  # type: ignore[operator]
    assert result.zinc_mg == m1.zinc_mg + m2.zinc_mg  # type: ignore[operator]


@pytest.mark.unit
def test_minerals_addition_with_none_on_one_side() -> None:
    """Test the __add__ method of Minerals handles all None values on one side."""
    # Arrange
    m1 = Minerals(
        calcium_mg=Decimal("1.0"),
        iron_mg=Decimal("2.0"),
        magnesium_mg=Decimal("3.0"),
        potassium_mg=Decimal("4.0"),
        sodium_mg=Decimal("5.0"),
        zinc_mg=Decimal("6.0"),
    )
    m2 = Minerals()

    # Act
    result = m1 + m2

    # Assert
    for field in _field_list:
        assert getattr(result, field) == getattr(m1, field)


@pytest.mark.unit
def test_minerals_addition_with_none_on_both_sides() -> None:
    """Test the __add__ method of Minerals handles all None values on both sides."""
    # Arrange
    m1 = Minerals()
    m2 = Minerals()

    # Act
    result = m1 + m2

    # Assert
    for field in _field_list:
        assert getattr(result, field) is None


@pytest.mark.unit
def test_minerals_default_values() -> None:
    """Test Minerals can be instantiated with default values."""
    # Arrange and Act
    minerals = Minerals()

    # Assert
    for field in _field_list:
        assert getattr(minerals, field) is None


@pytest.mark.unit
def test_minerals_constraints() -> None:
    """Test Minerals schema constraints."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        Minerals(calcium_mg=Decimal("1.0"), extra_field=123)  # type: ignore[call-arg]


@pytest.mark.unit
@pytest.mark.parametrize(
    "field",
    _field_list,
)
def test_minerals_field_constraints(field: str) -> None:
    """Test each Minerals field for negative and invalid type constraints."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        Minerals(**{field: Decimal("-1.0")})
    with pytest.raises(ValidationError):
        Minerals(**{field: "not-a-decimal"})
