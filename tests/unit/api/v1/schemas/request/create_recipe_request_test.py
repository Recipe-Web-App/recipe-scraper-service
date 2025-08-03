"""Unit tests for the CreateRecipeRequest schema and its logic."""

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.request.create_recipe_request import CreateRecipeRequest


@pytest.mark.unit
def test_create_recipe_request_instantiation() -> None:
    """Test CreateRecipeRequest can be instantiated with a valid URL."""
    # Arrange
    url = "https://mock-url.com/recipe"

    # Act
    req = CreateRecipeRequest(recipe_url=url)

    # Assert
    assert req.recipe_url == url
    assert req.model_dump(by_alias=True)["recipeUrl"] == url


@pytest.mark.unit
def test_create_recipe_request_alias() -> None:
    """Test CreateRecipeRequest accepts alias 'recipeUrl' in input dict."""
    # Arrange
    url = "https://mock-url.com/recipe"
    data = {"recipeUrl": url}

    # Act
    req = CreateRecipeRequest.model_validate(data)

    # Assert
    assert req.recipe_url == url
    assert req.model_dump(by_alias=True)["recipeUrl"] == url


@pytest.mark.unit
def test_create_recipe_request_required_field() -> None:
    """Test CreateRecipeRequest enforces required recipe_url field."""
    # Arrange, Act, Assert
    with pytest.raises(ValidationError):
        CreateRecipeRequest()
    with pytest.raises(ValidationError):
        CreateRecipeRequest(recipe_url=None)
    # No ValidationError for empty string
    req = CreateRecipeRequest(recipe_url="")
    assert req.recipe_url == ""


@pytest.mark.unit
def test_create_recipe_request_serialization() -> None:
    """Test model_dump produces a serializable dict with alias."""
    # Arrange
    url = "https://mock-url.com/recipe"
    req = CreateRecipeRequest(recipe_url=url)

    # Act
    data = req.model_dump(by_alias=True)

    # Assert
    assert isinstance(data, dict)
    assert data["recipeUrl"] == url
    assert "recipe_url" not in data


@pytest.mark.unit
def test_create_recipe_request_deserialization() -> None:
    """Test model_validate reconstructs a CreateRecipeRequest from dict."""
    # Arrange
    url = "https://mock-url.com/recipe"
    data = {"recipeUrl": url}

    # Act
    req = CreateRecipeRequest.model_validate(data)

    # Assert
    assert isinstance(req, CreateRecipeRequest)
    assert req.recipe_url == url


@pytest.mark.unit
def test_create_recipe_request_equality() -> None:
    """Test equality for CreateRecipeRequest objects with same data."""
    # Arrange
    url = "https://mock-url.com/recipe"
    r1 = CreateRecipeRequest(recipe_url=url)
    r2 = CreateRecipeRequest(recipe_url=url)
    r3 = CreateRecipeRequest(recipe_url="https://other-mock-url.com/recipe")

    # Act & Assert
    assert r1 == r2
    assert r1 != r3


@pytest.mark.unit
def test_create_recipe_request_model_copy() -> None:
    """Test model_copy for CreateRecipeRequest object."""
    # Arrange
    url = "https://mock-url.com/recipe"
    req = CreateRecipeRequest(recipe_url=url)

    # Act
    req_copy = req.model_copy()

    # Assert
    assert req == req_copy
    assert req is not req_copy
    assert req.recipe_url == req_copy.recipe_url
