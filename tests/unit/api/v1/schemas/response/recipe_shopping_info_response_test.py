"""Unit tests for the RecipeShoppingInfoResponse schema and its logic."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.response.ingredient_shopping_info_response import (
    IngredientShoppingInfoResponse,
)
from app.api.v1.schemas.response.recipe_shopping_info_response import (
    RecipeShoppingInfoResponse,
)


@pytest.mark.unit
def test_recipe_shopping_info_instantiation(
    mock_recipe_shopping_info_response_schema: RecipeShoppingInfoResponse,
) -> None:
    """Test RecipeShoppingInfoResponse can be instantiated with all fields."""
    # Arrange
    resp = mock_recipe_shopping_info_response_schema

    # Act
    result = RecipeShoppingInfoResponse(**resp.model_dump())

    # Assert
    assert result == resp
    assert isinstance(result.recipe_id, int)
    assert isinstance(result.ingredients, dict)
    assert isinstance(result.total_estimated_cost, Decimal)
    assert all(
        isinstance(ingredient, IngredientShoppingInfoResponse)
        for ingredient in result.ingredients.values()
    )


@pytest.mark.unit
def test_recipe_shopping_info_serialization(
    mock_recipe_shopping_info_response_schema: RecipeShoppingInfoResponse,
) -> None:
    """Test model_dump produces a serializable dict with all fields."""
    # Arrange
    resp = mock_recipe_shopping_info_response_schema

    # Act
    data = resp.model_dump()

    # Assert
    assert isinstance(data, dict)
    assert "recipe_id" in data
    assert "ingredients" in data
    assert "total_estimated_cost" in data


@pytest.mark.unit
def test_recipe_shopping_info_deserialization(
    mock_recipe_shopping_info_response_schema: RecipeShoppingInfoResponse,
) -> None:
    """Test model_validate reconstructs a RecipeShoppingInfoResponse from dict."""
    # Arrange
    resp = mock_recipe_shopping_info_response_schema
    data = resp.model_dump()

    # Act
    result = RecipeShoppingInfoResponse.model_validate(data)

    # Assert
    assert isinstance(result, RecipeShoppingInfoResponse)
    assert result == resp


@pytest.mark.unit
def test_recipe_shopping_info_equality_and_copy(
    mock_recipe_shopping_info_response_schema: RecipeShoppingInfoResponse,
) -> None:
    """Test equality and model_copy for RecipeShoppingInfoResponse objects."""
    # Arrange
    resp1 = mock_recipe_shopping_info_response_schema
    resp2 = RecipeShoppingInfoResponse(**resp1.model_dump())

    # Act
    resp_copy = resp1.model_copy()

    # Assert
    assert resp1 == resp2
    assert resp1 == resp_copy
    assert resp1 is not resp_copy


@pytest.mark.unit
def test_recipe_shopping_info_required_fields() -> None:
    """Test RecipeShoppingInfoResponse enforces required fields."""
    # Arrange, Act, Assert
    with pytest.raises(ValidationError):
        RecipeShoppingInfoResponse()

    with pytest.raises(ValidationError):
        RecipeShoppingInfoResponse(
            recipe_id=None,
            ingredients={},
            total_estimated_cost=Decimal("0.00"),
        )

    with pytest.raises(ValidationError):
        RecipeShoppingInfoResponse(
            recipe_id=1,
            ingredients=None,
            total_estimated_cost=Decimal("0.00"),
        )


@pytest.mark.unit
def test_recipe_shopping_info_total_cost_validation() -> None:
    """Test total cost validation in RecipeShoppingInfoResponse."""
    # Arrange, Act, Assert
    with pytest.raises(ValidationError):
        RecipeShoppingInfoResponse(
            recipe_id=1,
            ingredients={},
            total_estimated_cost=Decimal("-1.00"),
        )


@pytest.mark.unit
def test_recipe_shopping_info_with_ingredients(
    mock_ingredient_shopping_info_response_schema: IngredientShoppingInfoResponse,
) -> None:
    """Test RecipeShoppingInfoResponse with ingredient data."""
    # Arrange
    ingredient = mock_ingredient_shopping_info_response_schema
    ingredients = {1: ingredient}

    # Act
    resp = RecipeShoppingInfoResponse(
        recipe_id=1,
        ingredients=ingredients,
        total_estimated_cost=Decimal(str(ingredient.estimated_price)),
    )

    # Assert
    assert resp.ingredients == ingredients
    assert resp.total_estimated_cost == ingredient.estimated_price
    ingredient_info = resp.ingredients[1]
    assert isinstance(ingredient_info, IngredientShoppingInfoResponse)
    ingredient_info = resp.ingredients[1]
    assert isinstance(ingredient_info, IngredientShoppingInfoResponse)
