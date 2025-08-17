"""Unit tests for the IngredientShoppingInfoResponse schema and its logic."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.common.ingredient import Quantity
from app.api.v1.schemas.response.ingredient_shopping_info_response import (
    IngredientShoppingInfoResponse,
)
from app.enums.ingredient_unit_enum import IngredientUnitEnum


@pytest.mark.unit
def test_ingredient_shopping_info_instantiation(
    mock_ingredient_shopping_info_response_schema: IngredientShoppingInfoResponse,
) -> None:
    """Test IngredientShoppingInfoResponse can be instantiated with all fields."""
    # Arrange
    info = mock_ingredient_shopping_info_response_schema

    # Act
    resp = IngredientShoppingInfoResponse(
        ingredient_name="Test Ingredient",
        quantity=Quantity(amount=1.50, measurement=IngredientUnitEnum.G),
        estimated_price=Decimal("2.50"),
    )

    # Assert
    assert resp == info
    assert isinstance(resp.ingredient_name, str)
    assert isinstance(resp.quantity, Quantity)
    assert isinstance(resp.estimated_price, Decimal)
    # Check the measurement unit
    assert resp.quantity.measurement == IngredientUnitEnum.G


@pytest.mark.unit
def test_ingredient_shopping_info_serialization(
    mock_ingredient_shopping_info_response_schema: IngredientShoppingInfoResponse,
) -> None:
    """Test model_dump produces a serializable dict with all fields."""
    # Arrange
    info = mock_ingredient_shopping_info_response_schema

    # Act
    data = info.model_dump()

    # Assert
    assert isinstance(data, dict)
    assert "ingredient_name" in data
    assert "quantity" in data
    assert "quantity" in data
    assert "estimated_price" in data


@pytest.mark.unit
def test_ingredient_shopping_info_deserialization(
    mock_ingredient_shopping_info_response_schema: IngredientShoppingInfoResponse,
) -> None:
    """Test model_validate reconstructs an IngredientShoppingInfoResponse from dict."""
    # Arrange
    info = mock_ingredient_shopping_info_response_schema
    data = info.model_dump()

    # Act
    resp = IngredientShoppingInfoResponse.model_validate(data)

    # Assert
    assert isinstance(resp, IngredientShoppingInfoResponse)
    assert resp == info


@pytest.mark.unit
def test_ingredient_shopping_info_equality_and_copy(
    mock_ingredient_shopping_info_response_schema: IngredientShoppingInfoResponse,
) -> None:
    """Test equality and model_copy for IngredientShoppingInfoResponse objects."""
    # Arrange
    info1 = mock_ingredient_shopping_info_response_schema
    info2 = IngredientShoppingInfoResponse(**info1.model_dump())

    # Act
    info_copy = info1.model_copy()

    # Assert
    assert info1 == info2
    assert info1 == info_copy
    assert info1 is not info_copy


@pytest.mark.unit
def test_ingredient_shopping_info_required_fields() -> None:
    """Test IngredientShoppingInfoResponse enforces required fields."""
    # Arrange, Act, Assert
    with pytest.raises(ValidationError):
        IngredientShoppingInfoResponse()

    # This should NOT raise an error since estimated_price is optional with default None
    response = IngredientShoppingInfoResponse(
        ingredient_name="Test",
        quantity=Quantity(amount=1.0, measurement=IngredientUnitEnum.G),
        estimated_price=None,
    )
    assert response.estimated_price is None

    with pytest.raises(ValidationError):
        IngredientShoppingInfoResponse(
            ingredient_name="Test",
            quantity=None,
            estimated_price=Decimal("1.00"),
        )


@pytest.mark.unit
def test_ingredient_shopping_info_price_validation() -> None:
    """Test price validation in IngredientShoppingInfoResponse."""
    # Arrange, Act, Assert
    with pytest.raises(ValidationError):
        IngredientShoppingInfoResponse(
            ingredient_name="Test",
            quantity=Quantity(amount=1.0, measurement=IngredientUnitEnum.G),
            estimated_price=Decimal("-1.00"),
        )


@pytest.mark.unit
def test_ingredient_shopping_info_quantity_validation() -> None:
    """Test quantity validation in IngredientShoppingInfoResponse."""
    # Arrange, Act, Assert
    with pytest.raises(ValidationError):
        IngredientShoppingInfoResponse(
            ingredient_name="Test",
            quantity=Quantity(amount=-1.0, measurement=IngredientUnitEnum.G),
            estimated_price=Decimal("1.00"),
        )
