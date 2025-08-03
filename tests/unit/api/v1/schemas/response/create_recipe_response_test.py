"""Unit tests for the CreateRecipeResponse schema and its logic."""

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.common.recipe import Recipe as RecipeSchema
from app.api.v1.schemas.response.create_recipe_response import CreateRecipeResponse


@pytest.mark.unit
def test_create_recipe_response_instantiation(mock_recipe_schema: RecipeSchema) -> None:
    """Test CreateRecipeResponse can be instantiated with a valid Recipe."""
    # Arrange
    recipe = mock_recipe_schema

    # Act
    resp = CreateRecipeResponse(recipe=recipe)

    # Assert
    assert resp.recipe == recipe
    assert isinstance(resp.recipe, RecipeSchema)


@pytest.mark.unit
def test_create_recipe_response_serialization(
    mock_create_recipe_response_schema: CreateRecipeResponse,
) -> None:
    """Test model_dump produces a serializable dict with all fields."""
    # Arrange
    resp = mock_create_recipe_response_schema

    # Act
    data = resp.model_dump()

    # Assert
    assert isinstance(data, dict)
    assert "recipe" in data
    assert data["recipe"] == resp.recipe.model_dump()


@pytest.mark.unit
def test_create_recipe_response_deserialization(
    mock_recipe_schema: RecipeSchema,
) -> None:
    """Test model_validate reconstructs a CreateRecipeResponse from dict."""
    # Arrange
    recipe = mock_recipe_schema
    data = {"recipe": recipe.model_dump()}

    # Act
    resp = CreateRecipeResponse.model_validate(data)

    # Assert
    assert isinstance(resp, CreateRecipeResponse)
    assert resp.recipe == recipe


@pytest.mark.unit
def test_create_recipe_response_equality(
    mock_create_recipe_response_schema: CreateRecipeResponse,
    mock_recipe_schema: RecipeSchema,
) -> None:
    """Test equality for CreateRecipeResponse objects with same data."""
    # Arrange
    resp1 = mock_create_recipe_response_schema
    resp2 = CreateRecipeResponse(recipe=mock_recipe_schema)
    resp3 = CreateRecipeResponse(
        recipe=RecipeSchema(title="Other", ingredients=[], steps=[]),
    )

    # Act & Assert
    assert resp1 == resp2
    assert resp1 != resp3


@pytest.mark.unit
def test_create_recipe_response_model_copy(
    mock_create_recipe_response_schema: CreateRecipeResponse,
) -> None:
    """Test model_copy for CreateRecipeResponse object."""
    # Arrange
    resp = mock_create_recipe_response_schema

    # Act
    resp_copy = resp.model_copy()

    # Assert
    assert resp == resp_copy
    assert resp is not resp_copy
    assert resp.recipe == resp_copy.recipe


@pytest.mark.unit
def test_create_recipe_response_required_field() -> None:
    """Test CreateRecipeResponse enforces required recipe field."""
    # Arrange, Act, Assert
    with pytest.raises(ValidationError):
        CreateRecipeResponse()
    with pytest.raises(ValidationError):
        CreateRecipeResponse(recipe=None)
