"""Unit tests for IngredientClassification and its logic and constraints."""

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.common.nutritional_info.ingredient_classification import (
    IngredientClassification,
)
from app.enums.allergen_enum import AllergenEnum
from app.enums.food_group_enum import FoodGroupEnum

_field_list = list(IngredientClassification.model_fields.keys())


@pytest.mark.unit
def test_ingredient_classification_instantiation() -> None:
    """Test IngredientClassification can be instantiated with all fields."""
    # Arrange
    allergies = [AllergenEnum.MILK, AllergenEnum.EGGS]
    food_groups = [FoodGroupEnum.VEGETABLES, FoodGroupEnum.FRUITS]
    nutriscore_score = 10
    nutriscore_grade = "B"
    product_name = "Test Product"
    brands = "Test Brand"
    categories = "Test Category"

    # Act
    ic = IngredientClassification(
        allergies=allergies,
        food_groups=food_groups,
        nutriscore_score=nutriscore_score,
        nutriscore_grade=nutriscore_grade,
        product_name=product_name,
        brands=brands,
        categories=categories,
    )

    # Assert
    assert ic.allergies == allergies
    assert ic.food_groups == food_groups
    assert ic.nutriscore_score == nutriscore_score
    assert ic.nutriscore_grade == nutriscore_grade
    assert ic.product_name == product_name
    assert ic.brands == brands
    assert ic.categories == categories


@pytest.mark.unit
def test_ingredient_classification_model_copy() -> None:
    """Test that model_copy produces a new, equal object with all fields."""
    # Arrange
    ic = IngredientClassification(
        allergies=[AllergenEnum.MILK],
        food_groups=[FoodGroupEnum.FRUITS],
        nutriscore_score=5,
        nutriscore_grade="A",
        product_name="Apple",
        brands="BrandA",
        categories="Fruit",
    )

    # Act
    ic_copy = ic.model_copy()

    # Assert
    assert ic == ic_copy
    assert ic is not ic_copy
    for field in _field_list:
        assert getattr(ic, field) == getattr(ic_copy, field)


@pytest.mark.unit
def test_ingredient_classification_equality() -> None:
    """Test that two IngredientClassification objects with the same data are equal."""
    # Arrange
    kwargs1 = {
        "allergies": [AllergenEnum.MILK],
        "food_groups": [FoodGroupEnum.FRUITS],
        "nutriscore_score": 5,
        "nutriscore_grade": "A",
        "product_name": "Apple",
        "brands": "BrandA",
        "categories": "Fruit",
    }
    kwargs2 = {
        "allergies": [AllergenEnum.EGGS],
        "food_groups": [FoodGroupEnum.VEGETABLES],
        "nutriscore_score": 10,
        "nutriscore_grade": "B",
        "product_name": "Banana",
        "brands": "BrandB",
        "categories": "Snack",
    }

    # Act
    ic1 = IngredientClassification(**kwargs1)
    ic2 = IngredientClassification(**kwargs1)
    ic3 = IngredientClassification(**kwargs2)

    # Assert
    assert ic1 == ic2
    assert ic1 != ic3


@pytest.mark.unit
def test_ingredient_classification_serialization() -> None:
    """Test that model_dump produces a serializable dict with all fields."""
    # Arrange
    ic = IngredientClassification(
        allergies=[AllergenEnum.MILK],
        food_groups=[FoodGroupEnum.FRUITS],
        nutriscore_score=5,
        nutriscore_grade="A",
        product_name="Apple",
        brands="BrandA",
        categories="Fruit",
    )

    # Act
    data = ic.model_dump()

    # Assert
    assert isinstance(data, dict)
    for field in _field_list:
        assert data[field] == getattr(ic, field)


@pytest.mark.unit
def test_ingredient_classification_deserialization() -> None:
    """Test that model_validate reconstructs an object from dict with all fields."""
    # Arrange
    data = {
        "allergies": [AllergenEnum.MILK],
        "food_groups": [FoodGroupEnum.FRUITS],
        "nutriscore_score": 5,
        "nutriscore_grade": "A",
        "product_name": "Apple",
        "brands": "BrandA",
        "categories": "Fruit",
    }

    # Act
    ic = IngredientClassification.model_validate(data)

    # Assert
    assert isinstance(ic, IngredientClassification)
    for field in _field_list:
        assert getattr(ic, field) == data[field]


@pytest.mark.unit
def test_ingredient_classification_addition() -> None:
    """Test the __add__ method combines all fields correctly."""
    # Arrange
    ic1 = IngredientClassification(
        allergies=[AllergenEnum.MILK],
        food_groups=[FoodGroupEnum.FRUITS],
        nutriscore_score=5,
        nutriscore_grade="A",
        product_name="Apple",
        brands="BrandA",
        categories="Fruit",
    )
    ic2 = IngredientClassification(
        allergies=[AllergenEnum.EGGS],
        food_groups=[FoodGroupEnum.VEGETABLES],
        nutriscore_score=3,
        nutriscore_grade="B",
        product_name="Banana",
        brands="BrandB",
        categories="Snack",
    )

    # Act
    result = ic1 + ic2

    # Assert
    assert sorted(result.allergies) == sorted(ic1.allergies + ic2.allergies)  # type: ignore[arg-type,operator]
    assert sorted(result.food_groups) == sorted(ic1.food_groups + ic2.food_groups)  # type: ignore[arg-type,operator]
    assert result.nutriscore_score == ic1.nutriscore_score + ic2.nutriscore_score  # type: ignore[operator]
    # Logic for fields is delegated, just check type
    assert isinstance(result.nutriscore_grade, str)
    assert isinstance(result.product_name, str)
    assert isinstance(result.brands, str)
    assert isinstance(result.categories, str)


@pytest.mark.unit
def test_ingredient_classification_addition_with_none_on_one_side() -> None:
    """Test the __add__ method handles all None values on one side."""
    # Arrange
    ic1 = IngredientClassification(
        allergies=[AllergenEnum.MILK],
        food_groups=[FoodGroupEnum.FRUITS],
        nutriscore_score=5,
        nutriscore_grade="A",
        product_name="Apple",
        brands="BrandA",
        categories="Fruit",
    )
    ic2 = IngredientClassification()

    # Act
    result = ic1 + ic2

    # Assert
    for field in _field_list:
        assert getattr(result, field) == getattr(ic1, field)


@pytest.mark.unit
def test_ingredient_classification_addition_with_none_on_both_sides() -> None:
    """Test the __add__ method handles all None values on both sides."""
    # Arrange
    ic1 = IngredientClassification()
    ic2 = IngredientClassification()

    # Act
    result = ic1 + ic2

    # Assert
    for field in _field_list:
        assert getattr(result, field) is None


@pytest.mark.unit
def test_ingredient_classification_default_values() -> None:
    """Test IngredientClassification can be instantiated with default values."""
    # Arrange and Act
    ic = IngredientClassification()

    # Assert
    for field in _field_list:
        assert getattr(ic, field) is None


@pytest.mark.unit
def test_ingredient_classification_constraints() -> None:
    """Test IngredientClassification schema constraints."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        IngredientClassification(allergies=[AllergenEnum.MILK], extra_field=123)  # type: ignore[call-arg]


@pytest.mark.unit
@pytest.mark.parametrize(
    "field",
    _field_list,
)
def test_ingredient_classification_field_constraints(field: str) -> None:
    """Test each IngredientClassification field for invalid type constraints."""
    # Arrange and Act and Assert
    # allergies and food_groups expect lists, others expect int/str/None
    if field in ("allergies", "food_groups"):
        with pytest.raises(ValidationError):
            IngredientClassification(**{field: "not-a-list"})
    elif field == "nutriscore_score":
        with pytest.raises(ValidationError):
            IngredientClassification(**{field: "not-an-int"})
        with pytest.raises(ValidationError):
            IngredientClassification(**{field: -100})
    else:
        with pytest.raises(ValidationError):
            IngredientClassification(**{field: 12345})
