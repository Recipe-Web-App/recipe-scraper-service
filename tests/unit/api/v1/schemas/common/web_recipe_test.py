"""Unit tests for the WebRecipe schema and its logic and constraints."""

import pytest
from pydantic import ValidationError

# Import the WebRecipe schema. Adjust the import path if needed.
from app.api.v1.schemas.common.web_recipe import WebRecipe

_field_list = list(WebRecipe.model_fields.keys())


@pytest.mark.unit
def test_web_recipe_instantiation() -> None:
    """Test WebRecipe can be instantiated with all fields."""
    # Arrange
    kwargs = {field: f"value_{field}" for field in _field_list}

    # Act
    web_recipe = WebRecipe(**kwargs)

    # Assert
    for field in _field_list:
        assert getattr(web_recipe, field) == kwargs[field]


@pytest.mark.unit
def test_web_recipe_model_copy() -> None:
    """Test that model_copy produces a new, equal object with all fields."""
    # Arrange
    kwargs = {field: f"value_{field}" for field in _field_list}
    web_recipe = WebRecipe(**kwargs)

    # Act
    web_recipe_copy = web_recipe.model_copy()

    # Assert
    assert web_recipe == web_recipe_copy
    assert web_recipe is not web_recipe_copy
    for field in _field_list:
        assert getattr(web_recipe, field) == getattr(web_recipe_copy, field)


@pytest.mark.unit
def test_web_recipe_equality() -> None:
    """Test that two WebRecipe objects with the same data are equal."""
    # Arrange
    kwargs1 = {field: f"value_{field}" for field in _field_list}
    kwargs2 = {field: f"other_{field}" for field in _field_list}

    # Act
    w1 = WebRecipe(**kwargs1)
    w2 = WebRecipe(**kwargs1)
    w3 = WebRecipe(**kwargs2)

    # Assert
    assert w1 == w2
    assert w1 != w3


@pytest.mark.unit
def test_web_recipe_serialization() -> None:
    """Test that model_dump produces a serializable dict with all fields."""
    # Arrange
    kwargs = {field: f"value_{field}" for field in _field_list}
    web_recipe = WebRecipe(**kwargs)

    # Act
    data = web_recipe.model_dump()

    # Assert
    assert isinstance(data, dict)
    for field in _field_list:
        assert data[field] == getattr(web_recipe, field)


@pytest.mark.unit
def test_web_recipe_deserialization() -> None:
    """Test that model_validate reconstructs a WebRecipe object from dict."""
    # Arrange
    data = {field: f"value_{field}" for field in _field_list}

    # Act
    web_recipe = WebRecipe.model_validate(data)

    # Assert
    assert isinstance(web_recipe, WebRecipe)
    for field in _field_list:
        assert getattr(web_recipe, field) == data[field]


@pytest.mark.unit
def test_web_recipe_default_values() -> None:
    """Test that instantiating WebRecipe with no arguments raises ValidationError."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        WebRecipe()


@pytest.mark.unit
def test_web_recipe_constraints() -> None:
    """Test WebRecipe schema constraints."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        WebRecipe(**dict.fromkeys(_field_list, 123))
    with pytest.raises(ValidationError):
        WebRecipe(
            **{
                **{field: f"value_{field}" for field in _field_list},
                "extra_field": 123,
            },
        )
