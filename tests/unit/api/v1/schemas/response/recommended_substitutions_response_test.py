"""Unit tests for the RecommendedSubstitutionsResponse schema and its logic."""

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.common.ingredient import Ingredient, Quantity
from app.api.v1.schemas.common.pagination_params import PaginationParams
from app.api.v1.schemas.response.recommended_substitutions_response import (
    IngredientSubstitution,
    RecommendedSubstitutionsResponse,
)
from app.enums.ingredient_unit_enum import IngredientUnitEnum


@pytest.mark.unit
def test_recommended_substitutions_response_instantiation(
    mock_recommended_substitutions_response_schema: RecommendedSubstitutionsResponse,
) -> None:
    """Test RecommendedSubstitutionsResponse can be instantiated with all fields."""
    # Arrange
    resp = mock_recommended_substitutions_response_schema

    # Act
    result = RecommendedSubstitutionsResponse(**resp.model_dump())

    # Assert
    assert result == resp
    assert isinstance(result.ingredient, Ingredient)
    assert isinstance(result.recommended_substitutions, list)
    assert isinstance(result.limit, int)
    assert isinstance(result.offset, int)
    assert isinstance(result.count, int)


@pytest.mark.unit
def test_recommended_substitutions_response_serialization(
    mock_recommended_substitutions_response_schema: RecommendedSubstitutionsResponse,
) -> None:
    """Test model_dump produces a serializable dict with all fields."""
    # Arrange
    resp = mock_recommended_substitutions_response_schema

    # Act
    data = resp.model_dump()

    # Assert
    assert isinstance(data, dict)
    assert "ingredient" in data
    assert "recommended_substitutions" in data
    assert "limit" in data
    assert "offset" in data
    assert "count" in data


@pytest.mark.unit
def test_recommended_substitutions_response_deserialization(
    mock_recommended_substitutions_response_schema: RecommendedSubstitutionsResponse,
) -> None:
    """Test model_validate reconstructs a RecommendedSubstitutionsResponse from dict."""
    # Arrange
    resp = mock_recommended_substitutions_response_schema
    data = resp.model_dump()

    # Act
    result = RecommendedSubstitutionsResponse.model_validate(data)

    # Assert
    assert isinstance(result, RecommendedSubstitutionsResponse)
    assert result == resp


@pytest.mark.unit
def test_recommended_substitutions_response_equality_and_copy(
    mock_recommended_substitutions_response_schema: RecommendedSubstitutionsResponse,
) -> None:
    """Test equality and model_copy for RecommendedSubstitutionsResponse objects."""
    # Arrange
    resp1 = mock_recommended_substitutions_response_schema
    resp2 = RecommendedSubstitutionsResponse(**resp1.model_dump())

    # Act
    resp_copy = resp1.model_copy()

    # Assert
    assert resp1 == resp2
    assert resp1 == resp_copy
    assert resp1 is not resp_copy


@pytest.mark.unit
def test_recommended_substitutions_response_required_fields(
    mock_ingredient_substitution_schema_list: list[IngredientSubstitution],
) -> None:
    """Test RecommendedSubstitutionsResponse enforces required fields."""
    # Arrange
    ingredient = Ingredient(ingredient_id=1, name="Test", quantity=None)
    # Act & Assert
    with pytest.raises(ValidationError):
        RecommendedSubstitutionsResponse()
    with pytest.raises(ValidationError):
        RecommendedSubstitutionsResponse(
            ingredient=None,
            recommended_substitutions=mock_ingredient_substitution_schema_list,
            limit=1,
            offset=0,
            count=0,
        )
    with pytest.raises(ValidationError):
        RecommendedSubstitutionsResponse(
            ingredient=ingredient,
            recommended_substitutions=None,
            limit=1,
            offset=0,
            count=0,
        )


@pytest.mark.unit
def test_recommended_substitutions_response_from_all(
    mock_ingredient_substitution_schema_list: list[IngredientSubstitution],
) -> None:
    """Test from_all classmethod paginates and handles count_only correctly."""
    # Arrange
    ingredient = Ingredient(
        ingredient_id=1,
        name="Test",
        quantity=Quantity(amount=1.0, measurement=IngredientUnitEnum.G),
    )
    substitutions = mock_ingredient_substitution_schema_list
    limit = 2
    offset = 1
    pagination = PaginationParams(limit=limit, offset=offset, count_only=False)
    pagination_count_only = PaginationParams(
        limit=limit,
        offset=offset,
        count_only=True,
    )

    # Act
    paged = RecommendedSubstitutionsResponse.from_all(
        ingredient,
        substitutions,
        pagination,
    )
    count_only = RecommendedSubstitutionsResponse.from_all(
        ingredient,
        substitutions,
        pagination_count_only,
    )

    # Assert
    assert isinstance(paged, RecommendedSubstitutionsResponse)
    assert paged.ingredient == ingredient
    assert paged.limit == limit
    assert paged.offset == offset
    assert paged.count == len(substitutions)
    assert paged.recommended_substitutions == substitutions[offset : offset + limit]
    assert count_only.recommended_substitutions == []
    assert count_only.count == len(substitutions)


@pytest.mark.unit
def test_adjust_substitute_quantities(
    mock_ingredient_substitution_schema_list: list[IngredientSubstitution],
) -> None:
    """Test adjust_substitute_quantities sets correct quantities for substitutes."""
    # Arrange
    ingredient = Ingredient(
        ingredient_id=1,
        name="Test",
        quantity=Quantity(amount=2.0, measurement=IngredientUnitEnum.G),
    )
    resp = RecommendedSubstitutionsResponse(
        ingredient=ingredient,
        recommended_substitutions=mock_ingredient_substitution_schema_list,
        limit=2,
        offset=0,
        count=len(mock_ingredient_substitution_schema_list),
    )
    adjustment_quantity = Quantity(amount=5.0, measurement=IngredientUnitEnum.G)

    # Act
    resp.adjust_substitute_quantities(adjustment_quantity)

    # Assert
    for sub in resp.recommended_substitutions:
        assert sub.quantity is not None
        assert sub.quantity.measurement == adjustment_quantity.measurement
        assert isinstance(sub.quantity.amount, float)
