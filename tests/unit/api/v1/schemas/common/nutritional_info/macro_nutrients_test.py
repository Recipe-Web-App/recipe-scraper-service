"""Unit tests for the MacroNutrients schema as well as its logic and constraints."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.common.nutritional_info.fats import Fats
from app.api.v1.schemas.common.nutritional_info.fibers import Fibers
from app.api.v1.schemas.common.nutritional_info.macro_nutrients import MacroNutrients
from app.api.v1.schemas.common.nutritional_info.sugars import Sugars

_field_list = list(MacroNutrients.model_fields.keys())


@pytest.mark.unit
def test_macro_nutrients_instantiation() -> None:
    """Test MacroNutrients can be instantiated with all fields."""
    # Arrange
    calories = 100
    carbs_g = Decimal("20.5")
    cholesterol_mg = Decimal("5.2")
    protein_g = Decimal("10.1")
    sugars = Sugars(sugar_g=Decimal("3.3"))
    fats = Fats(fat_g=Decimal("2.2"))
    fibers = Fibers(fiber_g=Decimal("1.1"))

    # Act
    macro = MacroNutrients(
        calories=calories,
        carbs_g=carbs_g,
        cholesterol_mg=cholesterol_mg,
        protein_g=protein_g,
        sugars=sugars,
        fats=fats,
        fibers=fibers,
    )

    # Assert
    assert macro.calories == calories
    assert macro.carbs_g == carbs_g
    assert macro.cholesterol_mg == cholesterol_mg
    assert macro.protein_g == protein_g
    assert macro.sugars == sugars
    assert macro.fats == fats
    assert macro.fibers == fibers


@pytest.mark.unit
def test_macro_nutrients_model_copy() -> None:
    """Test that model_copy produces a new, equal object with all fields."""
    # Arrange
    macro = MacroNutrients(
        calories=100,
        carbs_g=Decimal("20.5"),
        cholesterol_mg=Decimal("5.2"),
        protein_g=Decimal("10.1"),
        sugars=Sugars(sugar_g=Decimal("3.3")),
        fats=Fats(fat_g=Decimal("2.2")),
        fibers=Fibers(fiber_g=Decimal("1.1")),
    )

    # Act
    macro_copy = macro.model_copy()

    # Assert
    assert macro == macro_copy
    assert macro is not macro_copy
    for field in _field_list:
        assert getattr(macro, field) == getattr(macro_copy, field)


@pytest.mark.unit
def test_macro_nutrients_equality() -> None:
    """Test that two MacroNutrients objects with the same data are equal."""
    # Arrange
    kwargs1 = {
        "calories": 100,
        "carbs_g": Decimal("20.5"),
        "cholesterol_mg": Decimal("5.2"),
        "protein_g": Decimal("10.1"),
        "sugars": Sugars(sugar_g=Decimal("3.3")),
        "fats": Fats(fat_g=Decimal("2.2")),
        "fibers": Fibers(fiber_g=Decimal("1.1")),
    }
    kwargs2 = {
        "calories": 200,
        "carbs_g": Decimal("40.0"),
        "cholesterol_mg": Decimal("10.0"),
        "protein_g": Decimal("20.0"),
        "sugars": Sugars(sugar_g=Decimal("6.6")),
        "fats": Fats(fat_g=Decimal("4.4")),
        "fibers": Fibers(fiber_g=Decimal("2.2")),
    }

    # Act
    macro1 = MacroNutrients(**kwargs1)
    macro2 = MacroNutrients(**kwargs1)
    macro3 = MacroNutrients(**kwargs2)

    # Assert
    assert macro1 == macro2
    assert macro1 != macro3


@pytest.mark.unit
def test_macro_nutrients_serialization() -> None:
    """Test that model_dump produces a serializable dict with all fields."""
    # Arrange
    macro = MacroNutrients(
        calories=100,
        carbs_g=Decimal("20.5"),
        cholesterol_mg=Decimal("5.2"),
        protein_g=Decimal("10.1"),
        sugars=Sugars(sugar_g=Decimal("3.3")),
        fats=Fats(fat_g=Decimal("2.2")),
        fibers=Fibers(fiber_g=Decimal("1.1")),
    )

    # Act
    data = macro.model_dump()

    # Assert
    assert isinstance(data, dict)
    for field in _field_list:
        if field in ("sugars", "fats", "fibers"):
            # Nested models are dumped as dicts
            assert data[field] == getattr(macro, field).model_dump()
        else:
            assert data[field] == getattr(macro, field)


@pytest.mark.unit
def test_macro_nutrients_deserialization() -> None:
    """Test that model_validate reconstructs an object from dict with all fields."""
    # Arrange
    data = {
        "calories": 100,
        "carbs_g": Decimal("20.5"),
        "cholesterol_mg": Decimal("5.2"),
        "protein_g": Decimal("10.1"),
        "sugars": Sugars(sugar_g=Decimal("3.3")),
        "fats": Fats(fat_g=Decimal("2.2")),
        "fibers": Fibers(fiber_g=Decimal("1.1")),
    }

    # Act
    macro = MacroNutrients.model_validate(data)

    # Assert
    assert isinstance(macro, MacroNutrients)
    for field in _field_list:
        assert getattr(macro, field) == data[field]


@pytest.mark.unit
def test_macro_nutrients_addition() -> None:
    """Test the __add__ method of MacroNutrients sums all fields and nested schemas."""
    # Arrange
    m1 = MacroNutrients(
        calories=100,
        carbs_g=Decimal("20.5"),
        cholesterol_mg=Decimal("5.2"),
        protein_g=Decimal("10.1"),
        sugars=Sugars(sugar_g=Decimal("3.3")),
        fats=Fats(fat_g=Decimal("2.2")),
        fibers=Fibers(fiber_g=Decimal("1.1")),
    )
    m2 = MacroNutrients(
        calories=50,
        carbs_g=Decimal("10.0"),
        cholesterol_mg=Decimal("2.5"),
        protein_g=Decimal("5.0"),
        sugars=Sugars(sugar_g=Decimal("1.1")),
        fats=Fats(fat_g=Decimal("1.1")),
        fibers=Fibers(fiber_g=Decimal("0.9")),
    )

    # Act
    result = m1 + m2

    # Assert
    assert result.calories == m1.calories + m2.calories  # type: ignore[operator]
    assert result.carbs_g == m1.carbs_g + m2.carbs_g  # type: ignore[operator]
    assert result.cholesterol_mg == m1.cholesterol_mg + m2.cholesterol_mg  # type: ignore[operator]
    assert result.protein_g == m1.protein_g + m2.protein_g  # type: ignore[operator]
    assert result.sugars == m1.sugars + m2.sugars
    assert result.fats == m1.fats + m2.fats
    assert result.fibers == m1.fibers + m2.fibers


@pytest.mark.unit
def test_macro_nutrients_addition_with_none_on_one_side() -> None:
    """Test the __add__ method handles all None values on one side."""
    # Arrange
    m1 = MacroNutrients(
        calories=100,
        carbs_g=Decimal("20.5"),
        cholesterol_mg=Decimal("5.2"),
        protein_g=Decimal("10.1"),
        sugars=Sugars(sugar_g=Decimal("3.3")),
        fats=Fats(fat_g=Decimal("2.2")),
        fibers=Fibers(fiber_g=Decimal("1.1")),
    )
    m2 = MacroNutrients()

    # Act
    result = m1 + m2

    # Assert
    for field in _field_list:
        assert getattr(result, field) == getattr(m1, field)


@pytest.mark.unit
def test_macro_nutrients_addition_with_none_on_both_sides() -> None:
    """Test the __add__ method handles all None values on both sides."""
    # Arrange
    m1 = MacroNutrients()
    m2 = MacroNutrients()

    # Act
    result = m1 + m2

    # Assert
    for field in ("calories", "carbs_g", "cholesterol_mg", "protein_g"):
        assert getattr(result, field) is None
    # Nested schemas should be default instances
    assert isinstance(result.sugars, Sugars)
    assert isinstance(result.fats, Fats)
    assert isinstance(result.fibers, Fibers)
    for nested in (result.sugars, result.fats, result.fibers):
        for nested_field in type(nested).model_fields:
            assert getattr(nested, nested_field) is None


@pytest.mark.unit
def test_macro_nutrients_default_values() -> None:
    """Test MacroNutrients can be instantiated with default values."""
    # Arrange and Act
    macro = MacroNutrients()

    # Assert
    for field in ("calories", "carbs_g", "cholesterol_mg", "protein_g"):
        assert getattr(macro, field) is None
    assert isinstance(macro.sugars, Sugars)
    assert isinstance(macro.fats, Fats)
    assert isinstance(macro.fibers, Fibers)
    for nested in (macro.sugars, macro.fats, macro.fibers):
        for nested_field in type(nested).model_fields:
            assert getattr(nested, nested_field) is None


@pytest.mark.unit
def test_macro_nutrients_constraints() -> None:
    """Test MacroNutrients schema constraints."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        MacroNutrients(calories=100, extra_field=123)  # type: ignore[call-arg]


@pytest.mark.unit
@pytest.mark.parametrize(
    "field",
    ["calories", "carbs_g", "cholesterol_mg", "protein_g"],
)
def test_macro_nutrients_field_constraints(field: str) -> None:
    """Test each MacroNutrients numeric field for negative and invalid type."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        MacroNutrients(**{field: -1})
    with pytest.raises(ValidationError):
        MacroNutrients(**{field: "not-a-number"})
