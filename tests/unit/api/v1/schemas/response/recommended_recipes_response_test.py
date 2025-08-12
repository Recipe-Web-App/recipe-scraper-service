"""Unit tests for the PopularRecipesResponse schema and its logic."""

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.common.pagination_params import PaginationParams
from app.api.v1.schemas.common.web_recipe import WebRecipe
from app.api.v1.schemas.response.recommended_recipes_response import (
    PopularRecipesResponse,
)


@pytest.mark.unit
def test_popular_recipes_response_instantiation(
    mock_popular_recipes_response_schema: PopularRecipesResponse,
) -> None:
    """Test PopularRecipesResponse can be instantiated with all fields."""
    # Arrange
    resp = mock_popular_recipes_response_schema

    # Act
    result = PopularRecipesResponse(**resp.model_dump())

    # Assert
    assert result == resp
    assert isinstance(result.recipes, list)
    assert isinstance(result.limit, int)
    assert isinstance(result.offset, int)
    assert isinstance(result.count, int)


@pytest.mark.unit
def test_popular_recipes_response_serialization(
    mock_popular_recipes_response_schema: PopularRecipesResponse,
) -> None:
    """Test model_dump produces a serializable dict with all fields."""
    # Arrange
    resp = mock_popular_recipes_response_schema

    # Act
    data = resp.model_dump()

    # Assert
    assert isinstance(data, dict)
    assert "recipes" in data
    assert "limit" in data
    assert "offset" in data
    assert "count" in data


@pytest.mark.unit
def test_popular_recipes_response_deserialization(
    mock_popular_recipes_response_schema: PopularRecipesResponse,
) -> None:
    """Test model_validate reconstructs a PopularRecipesResponse from dict."""
    # Arrange
    resp = mock_popular_recipes_response_schema
    data = resp.model_dump()

    # Act
    result = PopularRecipesResponse.model_validate(data)

    # Assert
    assert isinstance(result, PopularRecipesResponse)
    assert result == resp


@pytest.mark.unit
def test_popular_recipes_response_equality_and_copy(
    mock_popular_recipes_response_schema: PopularRecipesResponse,
) -> None:
    """Test equality and model_copy for PopularRecipesResponse objects."""
    # Arrange
    resp1 = mock_popular_recipes_response_schema
    resp2 = PopularRecipesResponse(**resp1.model_dump())

    # Act
    resp_copy = resp1.model_copy()

    # Assert
    assert resp1 == resp2
    assert resp1 == resp_copy
    assert resp1 is not resp_copy


@pytest.mark.unit
def test_popular_recipes_response_required_fields() -> None:
    """Test PopularRecipesResponse enforces required fields."""
    # Arrange, Act, Assert
    with pytest.raises(ValidationError):
        PopularRecipesResponse()
    with pytest.raises(ValidationError):
        PopularRecipesResponse(
            recipes=None,
            limit=1,
            offset=0,
            count=0,
        )
    with pytest.raises(ValidationError):
        PopularRecipesResponse(
            recipes=[],
            limit=None,
            offset=0,
            count=0,
        )


@pytest.mark.unit
def test_popular_recipes_response_from_all(
    mock_web_recipe_schema_list: list[WebRecipe],
) -> None:
    """Test from_all classmethod paginates and handles count_only correctly."""
    # Arrange
    recipes = mock_web_recipe_schema_list
    limit = 2
    offset = 1
    pagination = PaginationParams(limit=limit, offset=offset, count_only=False)
    pagination_count_only = PaginationParams(
        limit=limit,
        offset=offset,
        count_only=True,
    )

    # Act
    paged = PopularRecipesResponse.from_all(recipes, pagination)
    count_only = PopularRecipesResponse.from_all(
        recipes,
        pagination_count_only,
    )

    # Assert
    assert isinstance(paged, PopularRecipesResponse)
    assert paged.limit == limit
    assert paged.offset == offset
    assert paged.count == len(recipes)
    assert paged.recipes == recipes[offset : offset + limit]
    assert count_only.recipes == []
    assert count_only.count == len(recipes)
