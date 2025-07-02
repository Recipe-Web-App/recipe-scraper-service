"""Unit tests for Ingredient and Quantity schemas and their constraints."""

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.common.ingredient import Ingredient, Quantity
from app.enums.ingredient_unit_enum import IngredientUnitEnum

_quantity_field_list = list(Quantity.model_fields.keys())
_ingredient_field_list = list(Ingredient.model_fields.keys())


@pytest.mark.unit
def test_quantity_instantiation() -> None:
    """Test Quantity can be instantiated with all fields."""
    # Arrange
    amount = 2.5
    measurement = IngredientUnitEnum.G

    # Act
    quantity = Quantity(amount=amount, measurement=measurement)

    # Assert
    assert quantity.amount == amount
    assert quantity.measurement == measurement


@pytest.mark.unit
def test_quantity_model_copy() -> None:
    """Test that model_copy produces a new, equal Quantity object."""
    # Arrange
    quantity = Quantity(amount=1.0, measurement=IngredientUnitEnum.ML)

    # Act
    quantity_copy = quantity.model_copy()

    # Assert
    assert quantity == quantity_copy
    assert quantity is not quantity_copy
    for field in _quantity_field_list:
        assert getattr(quantity, field) == getattr(quantity_copy, field)


@pytest.mark.unit
def test_quantity_equality() -> None:
    """Test that two Quantity objects with the same data are equal."""
    # Arrange
    kwargs1 = {"amount": 1.0, "measurement": IngredientUnitEnum.UNIT}
    kwargs2 = {"amount": 2.0, "measurement": IngredientUnitEnum.G}

    # Act
    q1 = Quantity(**kwargs1)
    q2 = Quantity(**kwargs1)
    q3 = Quantity(**kwargs2)

    # Assert
    assert q1 == q2
    assert q1 != q3


@pytest.mark.unit
def test_quantity_serialization() -> None:
    """Test that model_dump produces a serializable dict with all fields."""
    # Arrange
    quantity = Quantity(amount=1.5, measurement=IngredientUnitEnum.ML)

    # Act
    data = quantity.model_dump()

    # Assert
    assert isinstance(data, dict)
    for field in _quantity_field_list:
        assert data[field] == getattr(quantity, field)


@pytest.mark.unit
def test_quantity_deserialization() -> None:
    """Test that model_validate reconstructs a Quantity object from dict."""
    # Arrange
    data = {"amount": 1.5, "measurement": IngredientUnitEnum.ML}

    # Act
    quantity = Quantity.model_validate(data)

    # Assert
    assert isinstance(quantity, Quantity)
    for field in _quantity_field_list:
        assert getattr(quantity, field) == data[field]


@pytest.mark.unit
def test_quantity_default_measurement() -> None:
    """Test Quantity uses default measurement if not provided."""
    # Arrange and Act
    quantity = Quantity(amount=1.0)

    # Assert
    assert quantity.measurement == IngredientUnitEnum.UNIT


@pytest.mark.unit
def test_quantity_constraints() -> None:
    """Test Quantity schema constraints."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        Quantity(amount=1.0, measurement=IngredientUnitEnum.UNIT, extra_field=123)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        Quantity(amount="not-a-float", measurement=IngredientUnitEnum.UNIT)


@pytest.mark.unit
def test_ingredient_instantiation() -> None:
    """Test Ingredient can be instantiated with all fields."""
    # Arrange
    ingredient_id = 42
    name = "Tomato"
    quantity = Quantity(amount=3.0, measurement=IngredientUnitEnum.G)

    # Act
    ingredient = Ingredient(ingredient_id=ingredient_id, name=name, quantity=quantity)

    # Assert
    assert ingredient.ingredient_id == ingredient_id
    assert ingredient.name == name
    assert ingredient.quantity == quantity


@pytest.mark.unit
def test_ingredient_model_copy() -> None:
    """Test that model_copy produces a new, equal Ingredient object."""
    # Arrange
    ingredient = Ingredient(
        ingredient_id=1,
        name="Salt",
        quantity=Quantity(amount=1.0, measurement=IngredientUnitEnum.UNIT),
    )

    # Act
    ingredient_copy = ingredient.model_copy()

    # Assert
    assert ingredient == ingredient_copy
    assert ingredient is not ingredient_copy
    for field in _ingredient_field_list:
        assert getattr(ingredient, field) == getattr(ingredient_copy, field)


@pytest.mark.unit
def test_ingredient_equality() -> None:
    """Test that two Ingredient objects with the same data are equal."""
    # Arrange
    kwargs1 = {
        "ingredient_id": 1,
        "name": "Salt",
        "quantity": Quantity(amount=1.0, measurement=IngredientUnitEnum.UNIT),
    }
    kwargs2 = {
        "ingredient_id": 2,
        "name": "Pepper",
        "quantity": Quantity(amount=2.0, measurement=IngredientUnitEnum.G),
    }

    # Act
    i1 = Ingredient(**kwargs1)
    i2 = Ingredient(**kwargs1)
    i3 = Ingredient(**kwargs2)

    # Assert
    assert i1 == i2
    assert i1 != i3


@pytest.mark.unit
def test_ingredient_serialization() -> None:
    """Test that model_dump produces a serializable dict with all fields."""
    # Arrange
    ingredient = Ingredient(
        ingredient_id=1,
        name="Salt",
        quantity=Quantity(amount=1.0, measurement=IngredientUnitEnum.UNIT),
    )

    # Act
    data = ingredient.model_dump()

    # Assert
    assert isinstance(data, dict)
    for field in _ingredient_field_list:
        if field == "quantity":
            if ingredient.quantity is not None:
                assert data[field] == ingredient.quantity.model_dump()
            else:
                assert data[field] is None
        else:
            assert data[field] == getattr(ingredient, field)


@pytest.mark.unit
def test_ingredient_deserialization() -> None:
    """Test that model_validate reconstructs an Ingredient object from dict."""
    # Arrange
    data = {
        "ingredient_id": 1,
        "name": "Salt",
        "quantity": Quantity(amount=1.0, measurement=IngredientUnitEnum.UNIT),
    }

    # Act
    ingredient = Ingredient.model_validate(data)

    # Assert
    assert isinstance(ingredient, Ingredient)
    for field in _ingredient_field_list:
        assert getattr(ingredient, field) == data[field]


@pytest.mark.unit
def test_ingredient_default_values() -> None:
    """Test Ingredient can be instantiated with default values."""
    # Arrange and Act
    ingredient = Ingredient(ingredient_id=1)

    # Assert
    assert ingredient.name is None
    assert ingredient.quantity is None


@pytest.mark.unit
def test_ingredient_constraints() -> None:
    """Test Ingredient schema constraints."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        Ingredient(ingredient_id=1, extra_field=123)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        Ingredient(ingredient_id="not-an-int")
    with pytest.raises(ValidationError):
        Ingredient(ingredient_id=1, quantity="not-a-quantity")
