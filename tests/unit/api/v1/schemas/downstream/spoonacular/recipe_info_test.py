"""Unit tests for the SpoonacularRecipeInfo schema and its logic."""

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.downstream.spoonacular.recipe_info import SpoonacularRecipeInfo

RECIPE_ID = 123
TITLE = "Mock Recipe Title"
IMAGE = "http://mock-url.com/mock-img.png"
IMAGE_TYPE = "png"
SUMMARY = "Mock recipe summary."
SOURCE_URL = "http://mock-url.com/source"
SPOONACULAR_SOURCE_URL = "http://spoonacular.com/mock-recipe"
READY_IN_MINUTES = 15
SERVINGS = 3

_spoonacular_field_list = list(SpoonacularRecipeInfo.model_fields.keys())


@pytest.mark.unit
def test_spoonacular_recipe_info_instantiation() -> None:
    """Test SpoonacularRecipeInfo can be instantiated with all fields."""
    # Arrange

    # Act
    recipe = SpoonacularRecipeInfo(
        id=RECIPE_ID,
        title=TITLE,
        image=IMAGE,
        image_type=IMAGE_TYPE,
        summary=SUMMARY,
        source_url=SOURCE_URL,
        spoonacular_source_url=SPOONACULAR_SOURCE_URL,
        ready_in_minutes=READY_IN_MINUTES,
        servings=SERVINGS,
    )

    # Assert
    assert recipe.id == RECIPE_ID
    assert recipe.title == TITLE
    assert recipe.image == IMAGE
    assert recipe.image_type == IMAGE_TYPE
    assert recipe.summary == SUMMARY
    assert recipe.source_url == SOURCE_URL
    assert recipe.spoonacular_source_url == SPOONACULAR_SOURCE_URL
    assert recipe.ready_in_minutes == READY_IN_MINUTES
    assert recipe.servings == SERVINGS


@pytest.mark.unit
def test_spoonacular_recipe_info_model_copy() -> None:
    """Test that model_copy produces a new, equal SpoonacularRecipeInfo object."""
    # Arrange
    recipe = SpoonacularRecipeInfo(
        id=RECIPE_ID,
        title=TITLE,
        image=IMAGE,
        image_type=IMAGE_TYPE,
        summary=SUMMARY,
        source_url=SOURCE_URL,
        spoonacular_source_url=SPOONACULAR_SOURCE_URL,
        ready_in_minutes=READY_IN_MINUTES,
        servings=SERVINGS,
    )

    # Act
    recipe_copy = recipe.model_copy()

    # Assert
    assert recipe == recipe_copy
    assert recipe is not recipe_copy
    for field in _spoonacular_field_list:
        assert getattr(recipe, field) == getattr(recipe_copy, field)


@pytest.mark.unit
def test_spoonacular_recipe_info_equality() -> None:
    """Test that two SpoonacularRecipeInfo objects with the same data are equal."""
    # Arrange
    kwargs1 = {
        "id": RECIPE_ID,
        "title": TITLE,
        "image": IMAGE,
        "image_type": IMAGE_TYPE,
        "summary": SUMMARY,
        "source_url": SOURCE_URL,
        "spoonacular_source_url": SPOONACULAR_SOURCE_URL,
        "ready_in_minutes": READY_IN_MINUTES,
        "servings": SERVINGS,
    }
    kwargs2 = {
        "id": 99,
        "title": "Other Recipe",
        "image": "http://mock-url.com/other.png",
        "image_type": "jpg",
        "summary": "Other summary.",
        "source_url": "http://mock-url.com/other",
        "spoonacular_source_url": "http://spoonacular.com/other",
        "ready_in_minutes": 99,
        "servings": 1,
    }

    # Act
    r1 = SpoonacularRecipeInfo(**kwargs1)
    r2 = SpoonacularRecipeInfo(**kwargs1)
    r3 = SpoonacularRecipeInfo(**kwargs2)

    # Assert
    assert r1 == r2
    assert r1 != r3


@pytest.mark.unit
def test_spoonacular_recipe_info_serialization() -> None:
    """Test that model_dump produces a serializable dict with all fields."""
    # Arrange
    recipe = SpoonacularRecipeInfo(
        id=RECIPE_ID,
        title=TITLE,
        image=IMAGE,
        image_type=IMAGE_TYPE,
        summary=SUMMARY,
        source_url=SOURCE_URL,
        spoonacular_source_url=SPOONACULAR_SOURCE_URL,
        ready_in_minutes=READY_IN_MINUTES,
        servings=SERVINGS,
    )

    # Act
    data = recipe.model_dump()

    # Assert
    assert isinstance(data, dict)
    for field in _spoonacular_field_list:
        assert data[field] == getattr(recipe, field)


@pytest.mark.unit
def test_spoonacular_recipe_info_deserialization() -> None:
    """Test that model_validate reconstructs a SpoonacularRecipeInfo object from dict.

    This test uses a field list and for-loop for field-by-field comparison.
    """
    # Arrange
    data = {
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
    alias_map = {
        "imageType": "image_type",
        "sourceUrl": "source_url",
        "spoonacularSourceUrl": "spoonacular_source_url",
        "readyInMinutes": "ready_in_minutes",
    }

    # Act
    recipe = SpoonacularRecipeInfo.model_validate(data)

    # Assert
    assert isinstance(recipe, SpoonacularRecipeInfo)
    for field in _spoonacular_field_list:
        data_key = field
        for k, v in alias_map.items():
            if v == field:
                data_key = k
                break
        assert getattr(recipe, field) == data[data_key]


@pytest.mark.unit
def test_spoonacular_recipe_info_default_values() -> None:
    """Test SpoonacularRecipeInfo can be instantiated with default values fields.

    Only required fields are provided; all others should be None.
    """
    # Arrange

    # Act
    recipe = SpoonacularRecipeInfo(id=RECIPE_ID, title=TITLE)

    # Assert
    assert recipe.id == RECIPE_ID
    assert recipe.title == TITLE
    assert recipe.image is None
    assert recipe.image_type is None
    assert recipe.summary is None
    assert recipe.source_url is None
    assert recipe.spoonacular_source_url is None
    assert recipe.ready_in_minutes is None
    assert recipe.servings is None


@pytest.mark.unit
def test_spoonacular_recipe_info_constraints() -> None:
    """Test SpoonacularRecipeInfo schema constraints and required fields."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        SpoonacularRecipeInfo()
    with pytest.raises(ValidationError):
        SpoonacularRecipeInfo(title=TITLE)
    with pytest.raises(ValidationError):
        SpoonacularRecipeInfo(id=RECIPE_ID)
    with pytest.raises(ValidationError):
        SpoonacularRecipeInfo(id=None, title=None)


@pytest.mark.unit
def test_spoonacular_recipe_info_title_validation() -> None:
    """Test title is cleaned and defaults to 'Untitled Recipe' if missing or blank."""
    # Arrange and Act and Assert
    assert SpoonacularRecipeInfo(id=RECIPE_ID, title=None).title == "Untitled Recipe"
    # whitespace becomes empty string
    assert SpoonacularRecipeInfo(id=RECIPE_ID, title="   ").title == ""
    assert SpoonacularRecipeInfo(id=RECIPE_ID, title="  Foo  ").title == "Foo"


@pytest.mark.unit
def test_spoonacular_recipe_info_url_validation() -> None:
    """Test URL fields are cleaned and blank/None become None."""
    # Arrange
    source_url = SOURCE_URL

    # Act
    r = SpoonacularRecipeInfo(
        id=RECIPE_ID,
        title=TITLE,
        source_url="   " + source_url + "   ",
        spoonacular_source_url="   ",
    )

    # Assert
    assert r.source_url == source_url
    assert r.spoonacular_source_url is None
