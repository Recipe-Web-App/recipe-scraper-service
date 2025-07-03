"""Unit tests for the SpoonacularSubstituteItem schema and its logic."""

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.downstream.spoonacular.substitute_item import (
    SpoonacularSubstituteItem,
)

NAME = "Mock Substitute Name"
SUBSTITUTE = "Mock Substitute"
DESCRIPTION = "Mock description."

_substitute_field_list = list(SpoonacularSubstituteItem.model_fields.keys())


@pytest.mark.unit
def test_substitute_item_instantiation() -> None:
    """Test SpoonacularSubstituteItem can be instantiated with all fields."""
    # Arrange

    # Act
    item = SpoonacularSubstituteItem(
        name=NAME,
        substitute=SUBSTITUTE,
        description=DESCRIPTION,
    )

    # Assert
    assert item.name == NAME
    assert item.substitute == SUBSTITUTE
    assert item.description == DESCRIPTION


@pytest.mark.unit
def test_substitute_item_model_copy() -> None:
    """Test model_copy for SpoonacularSubstituteItem object."""
    # Arrange
    item = SpoonacularSubstituteItem(
        name=NAME,
        substitute=SUBSTITUTE,
        description=DESCRIPTION,
    )

    # Act
    item_copy = item.model_copy()

    # Assert
    assert item == item_copy
    assert item is not item_copy
    for field in _substitute_field_list:
        assert getattr(item, field) == getattr(item_copy, field)


@pytest.mark.unit
def test_substitute_item_equality() -> None:
    """Test equality for SpoonacularSubstituteItem objects with same data."""
    # Arrange
    kwargs1 = {
        "name": NAME,
        "substitute": SUBSTITUTE,
        "description": DESCRIPTION,
    }
    kwargs2 = {
        "name": "Other Name",
        "substitute": "Other Substitute",
        "description": "Other description.",
    }

    # Act
    i1 = SpoonacularSubstituteItem(**kwargs1)
    i2 = SpoonacularSubstituteItem(**kwargs1)
    i3 = SpoonacularSubstituteItem(**kwargs2)

    # Assert
    assert i1 == i2
    assert i1 != i3


@pytest.mark.unit
def test_substitute_item_serialization() -> None:
    """Test that model_dump produces a serializable dict with all fields."""
    # Arrange
    item = SpoonacularSubstituteItem(
        name=NAME,
        substitute=SUBSTITUTE,
        description=DESCRIPTION,
    )

    # Act
    data = item.model_dump()

    # Assert
    assert isinstance(data, dict)
    for field in _substitute_field_list:
        assert data[field] == getattr(item, field)


@pytest.mark.unit
def test_substitute_item_deserialization() -> None:
    """Test model_validate reconstructs a SpoonacularSubstituteItem from dict.

    This test uses a field list and for-loop for field-by-field comparison.
    """
    # Arrange
    data = {
        "name": NAME,
        "substitute": SUBSTITUTE,
        "description": DESCRIPTION,
    }

    # Act
    item = SpoonacularSubstituteItem.model_validate(data)

    # Assert
    assert isinstance(item, SpoonacularSubstituteItem)
    for field in _substitute_field_list:
        assert getattr(item, field) == data[field]


@pytest.mark.unit
def test_substitute_item_default_values() -> None:
    """Test SpoonacularSubstituteItem can be instantiated with default values.

    All fields are optional and should default to None.
    """
    # Arrange

    # Act
    item = SpoonacularSubstituteItem()

    # Assert
    assert item.name is None
    assert item.substitute is None
    assert item.description is None


@pytest.mark.unit
def test_substitute_item_constraints() -> None:
    """Test schema constraints and required fields."""
    # Arrange and Act and Assert
    # No required fields, but test for extra fields
    with pytest.raises(ValidationError):
        SpoonacularSubstituteItem(foo="bar")  # type: ignore[call-arg]
    # Extra fields are not allowed
    item = SpoonacularSubstituteItem(
        name=NAME,
        substitute=SUBSTITUTE,
        description=DESCRIPTION,
    )
    assert hasattr(item, "name")
    assert not hasattr(item, "foo")


@pytest.mark.unit
def test_substitute_item_edge_cases() -> None:
    """Test edge cases for SpoonacularSubstituteItem fields."""
    # Arrange and Act
    item = SpoonacularSubstituteItem(name=None, substitute=None, description="")
    # Assert
    assert item.description == ""
    # All fields can be empty string (should be normalized to None for name/substitute).
    # Description becomes empty string.
    item = SpoonacularSubstituteItem(name="   ", substitute="", description="  ")
    assert item.name is None
    assert item.substitute is None
    assert item.description == ""
    # Fields can be set to non-string types (should be coerced to string and
    # stripped for name/substitute).
    item = SpoonacularSubstituteItem(name=123, substitute=456, description="789")
    assert item.name == "123"
    assert item.substitute == "456"
    assert item.description == "789"
