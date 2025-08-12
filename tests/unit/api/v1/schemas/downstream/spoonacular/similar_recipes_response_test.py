"""Unit tests for the SpoonacularSimilarRecipesResponse schema and its logic."""

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.downstream.spoonacular.recipe_info import SpoonacularRecipeInfo
from app.api.v1.schemas.downstream.spoonacular.similar_recipes_response import (
    SpoonacularSimilarRecipesResponse,
)

RECIPE_ID = 123
TITLE = "Mock Recipe Title"
IMAGE = "http://mock-url.com/mock-img.png"
IMAGE_TYPE = "png"
SUMMARY = "Mock recipe summary."
SOURCE_URL = "http://mock-url.com/source"
SPOONACULAR_SOURCE_URL = "http://spoonacular.com/mock-recipe"
READY_IN_MINUTES = 15
SERVINGS = 3

RECIPE_DICT = {
    "id": RECIPE_ID,
    "title": TITLE,
    "image": IMAGE,
    "imageType": IMAGE_TYPE,
    "summary": SUMMARY,
    "sourceUrl": SOURCE_URL,
    "spoonacularSourceUrl": SPOONACULAR_SOURCE_URL,
    "readyInMinutes": READY_IN_MINUTES,
    "servings": SERVINGS,
}

RECIPE_OBJ = SpoonacularRecipeInfo.model_validate(RECIPE_DICT)

_similar_field_list = list(SpoonacularSimilarRecipesResponse.model_fields.keys())


@pytest.mark.unit
def test_similar_response_instantiation() -> None:
    """Test SpoonacularSimilarRecipesResponse can be instantiated with all fields."""
    # Arrange
    recipes = [RECIPE_OBJ]

    # Act
    resp = SpoonacularSimilarRecipesResponse(recipes=recipes)

    # Assert
    assert resp.recipes == recipes


@pytest.mark.unit
def test_similar_response_model_copy() -> None:
    """Test model_copy for SpoonacularSimilarRecipesResponse object."""
    # Arrange
    resp = SpoonacularSimilarRecipesResponse(recipes=[RECIPE_OBJ])

    # Act
    resp_copy = resp.model_copy()

    # Assert
    assert resp == resp_copy
    assert resp is not resp_copy
    for field in _similar_field_list:
        assert getattr(resp, field) == getattr(resp_copy, field)


@pytest.mark.unit
def test_similar_response_equality() -> None:
    """Test equality for SpoonacularSimilarRecipesResponse objects with same data."""
    # Arrange
    kwargs1 = {"recipes": [RECIPE_OBJ]}
    kwargs2: dict[str, list[SpoonacularRecipeInfo]] = {"recipes": []}

    # Act
    r1 = SpoonacularSimilarRecipesResponse(**kwargs1)
    r2 = SpoonacularSimilarRecipesResponse(**kwargs1)
    r3 = SpoonacularSimilarRecipesResponse(**kwargs2)

    # Assert
    assert r1 == r2
    assert r1 != r3


@pytest.mark.unit
def test_similar_response_serialization() -> None:
    """Test that model_dump produces a serializable dict with all fields."""
    # Arrange
    resp = SpoonacularSimilarRecipesResponse(recipes=[RECIPE_OBJ])

    # Act
    data = resp.model_dump()

    # Assert
    assert isinstance(data, dict)
    for field in _similar_field_list:
        if field == "recipes":
            assert data[field] == [r.model_dump() for r in resp.recipes]
        else:
            assert data[field] == getattr(resp, field)


@pytest.mark.unit
def test_similar_response_deserialization() -> None:
    """Test model_validate reconstructs a SpoonacularSimilarRecipesResponse from dict.

    This test uses a field list and for-loop for field-by-field comparison.
    """
    # Arrange
    data = {"recipes": [RECIPE_DICT]}

    # Act
    resp = SpoonacularSimilarRecipesResponse.model_validate(data)

    # Assert
    assert isinstance(resp, SpoonacularSimilarRecipesResponse)
    for field in _similar_field_list:
        if field == "recipes":
            assert resp.recipes == [RECIPE_OBJ]
        else:
            assert getattr(resp, field) == data[field]


@pytest.mark.unit
def test_similar_response_from_list() -> None:
    """Test from_list creates a valid response from a list of dicts."""
    # Arrange
    recipe_list = [RECIPE_DICT]

    # Act
    resp = SpoonacularSimilarRecipesResponse.from_list(recipe_list)

    # Assert
    assert isinstance(resp, SpoonacularSimilarRecipesResponse)
    assert resp.recipes == [RECIPE_OBJ]


@pytest.mark.unit
def test_similar_response_default_values() -> None:
    """Test SpoonacularSimilarRecipesResponse can be instantiated with default values.

    Only recipes is required; it should default to [].
    """
    # Arrange and Act
    resp = SpoonacularSimilarRecipesResponse()

    # Assert
    assert resp.recipes == []


@pytest.mark.unit
def test_similar_response_constraints() -> None:
    """Test schema constraints and required fields."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        SpoonacularSimilarRecipesResponse(recipes="not-a-list")
    with pytest.raises(ValidationError):
        SpoonacularSimilarRecipesResponse(recipes=[{"id": None}])
    # Extra fields are ignored due to extra="ignore"
    resp = SpoonacularSimilarRecipesResponse(recipes=[], extra_field=123)
    assert hasattr(resp, "recipes")
    assert not hasattr(resp, "extra_field")


@pytest.mark.unit
def test_similar_response_recipes_edge_cases() -> None:
    """Test recipes field edge cases: None, not a list, invalid items, empty list."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        SpoonacularSimilarRecipesResponse(recipes=None)
    with pytest.raises(ValidationError):
        SpoonacularSimilarRecipesResponse(recipes=[RECIPE_OBJ, None, "foo", 123, {}])
    resp = SpoonacularSimilarRecipesResponse(recipes=[])
    assert resp.recipes == []
