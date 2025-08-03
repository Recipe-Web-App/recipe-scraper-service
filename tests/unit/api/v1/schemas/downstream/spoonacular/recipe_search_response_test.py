"""Unit tests for the SpoonacularRecipeSearchResponse schema and its logic."""

import pytest

from app.api.v1.schemas.downstream.spoonacular.recipe_info import SpoonacularRecipeInfo
from app.api.v1.schemas.downstream.spoonacular.recipe_search_response import (
    SpoonacularRecipeSearchResponse,
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

_search_field_list = list(SpoonacularRecipeSearchResponse.model_fields.keys())


@pytest.mark.unit
def test_search_response_instantiation() -> None:
    """Test SpoonacularRecipeSearchResponse can be instantiated with all fields."""
    # Arrange
    results = [RECIPE_DICT]  # Pass as dict, not model instance
    offset = 10
    number = 5
    total_results = 100

    # Act
    resp = SpoonacularRecipeSearchResponse(
        results=results,
        offset=offset,
        number=number,
        total_results=total_results,
    )

    # Assert
    assert resp.results == [RECIPE_OBJ]
    assert resp.offset == offset
    assert resp.number == number
    assert resp.total_results == total_results


@pytest.mark.unit
def test_search_response_model_copy() -> None:
    """Test that model_copy produces a new, equal object."""
    # Arrange
    resp = SpoonacularRecipeSearchResponse(
        results=[RECIPE_OBJ],
        offset=1,
        number=2,
        total_results=3,
    )

    # Act
    resp_copy = resp.model_copy()

    # Assert
    assert resp == resp_copy
    assert resp is not resp_copy
    for field in _search_field_list:
        assert getattr(resp, field) == getattr(resp_copy, field)


@pytest.mark.unit
def test_search_response_equality() -> None:
    """Test that two objects with the same data are equal."""
    # Arrange
    kwargs1 = {
        "results": [RECIPE_OBJ],
        "offset": 0,
        "number": 1,
        "total_results": 10,
    }
    kwargs2 = {
        "results": [],
        "offset": 1,
        "number": 2,
        "total_results": 20,
    }

    # Act
    r1 = SpoonacularRecipeSearchResponse(**kwargs1)
    r2 = SpoonacularRecipeSearchResponse(**kwargs1)
    r3 = SpoonacularRecipeSearchResponse(**kwargs2)

    # Assert
    assert r1 == r2
    assert r1 != r3


@pytest.mark.unit
def test_search_response_serialization() -> None:
    """Test that model_dump produces a serializable dict with all fields."""
    # Arrange
    resp = SpoonacularRecipeSearchResponse(
        results=[RECIPE_OBJ],
        offset=2,
        number=3,
        total_results=4,
    )

    # Act
    data = resp.model_dump()

    # Assert
    assert isinstance(data, dict)
    for field in _search_field_list:
        if field == "results":
            assert data[field] == [r.model_dump() for r in resp.results]
        else:
            assert data[field] == getattr(resp, field)


@pytest.mark.unit
def test_search_response_deserialization() -> None:
    """Test that model_validate reconstructs a SpoonacularRecipeSearchResponse object.

    This test uses a field list and for-loop for field-by-field comparison.
    """
    # Arrange
    data = {
        "results": [RECIPE_DICT],
        "offset": 5,
        "number": 2,
        "totalResults": 99,
    }

    # Act
    resp = SpoonacularRecipeSearchResponse.model_validate(data)

    # Assert
    assert isinstance(resp, SpoonacularRecipeSearchResponse)
    for field in _search_field_list:
        if field == "results":
            assert resp.results == [RECIPE_OBJ]
        elif field == "total_results":
            assert getattr(resp, field) == data["totalResults"]
        else:
            assert getattr(resp, field) == data[field]


@pytest.mark.unit
def test_search_response_default_values() -> None:
    """Test SpoonacularRecipeSearchResponse can be instantiated with default values.

    Only results is required; all others should default to 0 or [].
    """
    # Arrange and Act
    resp = SpoonacularRecipeSearchResponse()

    # Assert
    assert resp.results == []
    assert resp.offset == 0
    assert resp.number == 0
    assert resp.total_results == 0


@pytest.mark.unit
def test_search_response_constraints() -> None:
    """Test schema constraints and required fields."""
    # Arrange and Act and Assert
    resp = SpoonacularRecipeSearchResponse(results="not-a-list")
    assert resp.results == []
    resp = SpoonacularRecipeSearchResponse(results=[{"id": None}])
    assert resp.results == []
    # Extra fields are ignored due to extra="ignore"
    resp = SpoonacularRecipeSearchResponse(results=[], extra_field=123)
    assert hasattr(resp, "results")
    assert not hasattr(resp, "extra_field")


@pytest.mark.unit
def test_search_response_results_edge_cases() -> None:
    """Test results field edge cases: None, not a list, invalid items, empty list."""
    # Arrange and Act and Assert
    resp = SpoonacularRecipeSearchResponse(results=None)
    assert resp.results == []
    resp = SpoonacularRecipeSearchResponse(results=[])
    assert resp.results == []
    # Only valid SpoonacularRecipeInfo objects should be present
    resp = SpoonacularRecipeSearchResponse(results=[RECIPE_DICT])
    assert resp.results == [RECIPE_OBJ]
