"""Unit tests for the PairingSuggestionsResponse schema and its logic."""

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.common.pagination_params import PaginationParams
from app.api.v1.schemas.common.web_recipe import WebRecipe
from app.api.v1.schemas.response.pairing_suggestions_response import (
    PairingSuggestionsResponse,
)


@pytest.mark.unit
def test_pairing_suggestions_response_instantiation(
    mock_pairing_suggestions_response_schema: PairingSuggestionsResponse,
) -> None:
    """Test PairingSuggestionsResponse can be instantiated with all fields."""
    # Arrange
    resp = mock_pairing_suggestions_response_schema

    # Act
    result = PairingSuggestionsResponse(**resp.model_dump())

    # Assert
    assert result == resp
    assert isinstance(result.pairing_suggestions, list)
    assert isinstance(result.recipe_id, int)
    assert isinstance(result.limit, int)
    assert isinstance(result.offset, int)
    assert isinstance(result.count, int)


@pytest.mark.unit
def test_pairing_suggestions_response_serialization(
    mock_pairing_suggestions_response_schema: PairingSuggestionsResponse,
) -> None:
    """Test model_dump produces a serializable dict with all fields."""
    # Arrange
    resp = mock_pairing_suggestions_response_schema

    # Act
    data = resp.model_dump()

    # Assert
    assert isinstance(data, dict)
    assert "recipe_id" in data
    assert "pairing_suggestions" in data
    assert "limit" in data
    assert "offset" in data
    assert "count" in data


@pytest.mark.unit
def test_pairing_suggestions_response_deserialization(
    mock_pairing_suggestions_response_schema: PairingSuggestionsResponse,
) -> None:
    """Test model_validate reconstructs a PairingSuggestionsResponse from dict."""
    # Arrange
    resp = mock_pairing_suggestions_response_schema
    data = resp.model_dump()

    # Act
    result = PairingSuggestionsResponse.model_validate(data)

    # Assert
    assert isinstance(result, PairingSuggestionsResponse)
    assert result == resp


@pytest.mark.unit
def test_pairing_suggestions_response_equality_and_copy(
    mock_pairing_suggestions_response_schema: PairingSuggestionsResponse,
) -> None:
    """Test equality and model_copy for PairingSuggestionsResponse objects."""
    # Arrange
    resp1 = mock_pairing_suggestions_response_schema
    resp2 = PairingSuggestionsResponse(**resp1.model_dump())

    # Act
    resp_copy = resp1.model_copy()

    # Assert
    assert resp1 == resp2
    assert resp1 == resp_copy
    assert resp1 is not resp_copy


@pytest.mark.unit
def test_pairing_suggestions_response_required_fields() -> None:
    """Test PairingSuggestionsResponse enforces required fields."""
    # Arrange, Act, Assert
    with pytest.raises(ValidationError):
        PairingSuggestionsResponse()
    with pytest.raises(ValidationError):
        PairingSuggestionsResponse(
            recipe_id=None,
            pairing_suggestions=[],
            limit=1,
            offset=0,
            count=0,
        )
    with pytest.raises(ValidationError):
        PairingSuggestionsResponse(
            recipe_id=1,
            pairing_suggestions=None,
            limit=1,
            offset=0,
            count=0,
        )


@pytest.mark.unit
def test_pairing_suggestions_response_from_all(
    mock_web_recipe_schema_list: list[WebRecipe],
) -> None:
    """Test from_all classmethod paginates and handles count_only correctly."""
    # Arrange
    recipe_id = 42
    recipes = mock_web_recipe_schema_list
    pagination = PaginationParams(limit=2, offset=1, count_only=False)
    pagination_count_only = PaginationParams(limit=2, offset=1, count_only=True)
    limit = 2
    offset = 1

    # Act
    paged = PairingSuggestionsResponse.from_all(recipe_id, recipes, pagination)
    count_only = PairingSuggestionsResponse.from_all(
        recipe_id,
        recipes,
        pagination_count_only,
    )

    # Assert
    assert isinstance(paged, PairingSuggestionsResponse)
    assert paged.recipe_id == recipe_id
    assert paged.limit == limit
    assert paged.offset == offset
    assert paged.count == len(recipes)
    assert paged.pairing_suggestions == recipes[offset : offset + limit]
    assert count_only.pairing_suggestions == []
    assert count_only.count == len(recipes)
