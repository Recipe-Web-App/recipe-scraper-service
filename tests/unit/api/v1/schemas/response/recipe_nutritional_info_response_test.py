"""Unit tests for the RecipeNutritionalInfoResponse schema and its logic."""

import pytest

from app.api.v1.schemas.response.ingredient_nutritional_info_response import (
    IngredientNutritionalInfoResponse,
)
from app.api.v1.schemas.response.recipe_nutritional_info_response import (
    RecipeNutritionalInfoResponse,
)


@pytest.mark.unit
def test_recipe_nutritional_info_instantiation(
    mock_recipe_nutritional_info_response_schema: RecipeNutritionalInfoResponse,
) -> None:
    """Test RecipeNutritionalInfoResponse can be instantiated with all fields."""
    # Arrange
    resp = mock_recipe_nutritional_info_response_schema

    # Act
    result = RecipeNutritionalInfoResponse(**resp.model_dump())

    # Assert
    assert result == resp
    assert isinstance(result.ingredients, dict) or result.ingredients is None
    assert result.total is None or isinstance(
        result.total,
        IngredientNutritionalInfoResponse,
    )


@pytest.mark.unit
def test_recipe_nutritional_info_serialization(
    mock_recipe_nutritional_info_response_schema: RecipeNutritionalInfoResponse,
) -> None:
    """Test model_dump produces a serializable dict with all fields."""
    # Arrange
    resp = mock_recipe_nutritional_info_response_schema

    # Act
    data = resp.model_dump()

    # Assert
    assert isinstance(data, dict)
    assert "ingredients" in data
    assert "missing_ingredients" in data
    assert "total" in data


@pytest.mark.unit
def test_recipe_nutritional_info_deserialization(
    mock_recipe_nutritional_info_response_schema: RecipeNutritionalInfoResponse,
) -> None:
    """Test model_validate reconstructs a RecipeNutritionalInfoResponse from dict."""
    # Arrange
    resp = mock_recipe_nutritional_info_response_schema
    data = resp.model_dump()

    # Act
    result = RecipeNutritionalInfoResponse.model_validate(data)

    # Assert
    assert isinstance(result, RecipeNutritionalInfoResponse)
    assert result == resp


@pytest.mark.unit
def test_recipe_nutritional_info_equality_and_copy(
    mock_recipe_nutritional_info_response_schema: RecipeNutritionalInfoResponse,
) -> None:
    """Test equality and model_copy for RecipeNutritionalInfoResponse objects."""
    # Arrange
    resp1 = mock_recipe_nutritional_info_response_schema
    resp2 = RecipeNutritionalInfoResponse(**resp1.model_dump())

    # Act
    resp_copy = resp1.model_copy()

    # Assert
    assert resp1 == resp2
    assert resp1 == resp_copy
    assert resp1 is not resp_copy


@pytest.mark.unit
def test_recipe_nutritional_info_required_fields() -> None:
    """Test RecipeNutritionalInfoResponse allows all fields to be optional."""
    # Arrange, Act, Assert
    resp = RecipeNutritionalInfoResponse()
    assert resp.ingredients is None
    assert resp.missing_ingredients is None
    assert resp.total is None


@pytest.mark.unit
def test_recipe_nutritional_info_missing_ingredients(
    mock_recipe_nutritional_info_response_schema_with_missing_ingredients: (
        RecipeNutritionalInfoResponse
    ),
) -> None:
    """Test handling of missing_ingredients field."""
    # Arrange
    resp = mock_recipe_nutritional_info_response_schema_with_missing_ingredients

    # Act
    data = resp.model_dump()
    result = RecipeNutritionalInfoResponse.model_validate(data)

    # Assert
    assert result.missing_ingredients is not None
    assert isinstance(result.missing_ingredients, list)
    assert all(isinstance(i, int) for i in result.missing_ingredients)


@pytest.mark.unit
def test_recipe_nutritional_info_total_field(
    mock_recipe_nutritional_info_response_schema: RecipeNutritionalInfoResponse,
) -> None:
    """Test total field is an IngredientNutritionalInfoResponse or None."""
    # Arrange
    resp = mock_recipe_nutritional_info_response_schema

    # Act
    data = resp.model_dump()
    result = RecipeNutritionalInfoResponse.model_validate(data)

    # Assert
    assert result.total is None or isinstance(
        result.total,
        IngredientNutritionalInfoResponse,
    )
