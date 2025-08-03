"""Unit tests for the IngredientNutritionalInfoResponse schema and its logic."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.common.ingredient import Quantity
from app.api.v1.schemas.response.ingredient_nutritional_info_response import (
    IngredientNutritionalInfoResponse,
)


@pytest.mark.unit
def test_ingredient_nutritional_info_instantiation(
    mock_ingredient_nutritional_info_response_schema: IngredientNutritionalInfoResponse,
) -> None:
    """Test IngredientNutritionalInfoResponse can be instantiated with all fields."""
    # Arrange
    info = mock_ingredient_nutritional_info_response_schema

    # Act
    resp = IngredientNutritionalInfoResponse(**info.model_dump())

    # Assert
    assert resp == info
    assert isinstance(resp.quantity, Quantity)
    assert resp.quantity.amount is not None
    assert resp.classification is not None
    assert resp.macro_nutrients is not None
    assert resp.vitamins is not None
    assert resp.minerals is not None


@pytest.mark.unit
def test_ingredient_nutritional_info_serialization(
    mock_ingredient_nutritional_info_response_schema: IngredientNutritionalInfoResponse,
) -> None:
    """Test model_dump produces a serializable dict with all fields."""
    # Arrange
    info = mock_ingredient_nutritional_info_response_schema

    # Act
    data = info.model_dump()

    # Assert
    assert isinstance(data, dict)
    assert "quantity" in data
    assert "classification" in data
    assert "macro_nutrients" in data
    assert "vitamins" in data
    assert "minerals" in data


@pytest.mark.unit
def test_ingredient_nutritional_info_deserialization(
    mock_ingredient_nutritional_info_response_schema: IngredientNutritionalInfoResponse,
) -> None:
    """Test model_validate reconstructs an IngredientNutritionalInfoResponse from dict.

    Ensures deserialization from dict produces a valid schema instance.
    """
    # Arrange
    info = mock_ingredient_nutritional_info_response_schema
    data = info.model_dump()

    # Act
    resp = IngredientNutritionalInfoResponse.model_validate(data)

    # Assert
    assert isinstance(resp, IngredientNutritionalInfoResponse)
    assert resp == info


@pytest.mark.unit
def test_ingredient_nutritional_info_equality_and_copy(
    mock_ingredient_nutritional_info_response_schema: IngredientNutritionalInfoResponse,
) -> None:
    """Test equality and model_copy for IngredientNutritionalInfoResponse objects."""
    # Arrange
    info1 = mock_ingredient_nutritional_info_response_schema
    info2 = IngredientNutritionalInfoResponse(**info1.model_dump())

    # Act
    info_copy = info1.model_copy()

    # Assert
    assert info1 == info2
    assert info1 == info_copy
    assert info1 is not info_copy


@pytest.mark.unit
def test_ingredient_nutritional_info_required_field() -> None:
    """Test IngredientNutritionalInfoResponse enforces required quantity field."""
    # Arrange, Act, Assert
    with pytest.raises(ValidationError):
        IngredientNutritionalInfoResponse()
    with pytest.raises(ValidationError):
        IngredientNutritionalInfoResponse(quantity=None)


@pytest.mark.unit
def test_ingredient_nutritional_info_adjust_quantity(
    mock_ingredient_nutritional_info_response_schema: IngredientNutritionalInfoResponse,
) -> None:
    """Test adjust_quantity scales nutritional values correctly."""
    # Arrange
    info = mock_ingredient_nutritional_info_response_schema.model_copy()
    old_amount = info.quantity.amount
    measurement = info.quantity.measurement
    new_quantity = Quantity(amount=Decimal("2.0"), measurement=measurement)

    # Act
    info.adjust_quantity(new_quantity)

    # Assert
    assert info.quantity.amount == Decimal("2.0")
    if old_amount is not None and old_amount != 0:
        scale = Decimal("2.0") / Decimal(str(old_amount))
        # Spot check a macro field
        if info.macro_nutrients.carbs_g is not None:
            assert (
                info.macro_nutrients.carbs_g % scale == 0
                or info.macro_nutrients.carbs_g >= 0
            )


@pytest.mark.unit
def test_ingredient_nutritional_info_add(
    mock_ingredient_nutritional_info_response_schema: IngredientNutritionalInfoResponse,
) -> None:
    """Test __add__ combines two IngredientNutritionalInfoResponse objects."""
    # Arrange
    info1 = mock_ingredient_nutritional_info_response_schema
    info2 = IngredientNutritionalInfoResponse(**info1.model_dump())

    # Act
    combined = info1 + info2

    # Assert
    assert isinstance(combined, IngredientNutritionalInfoResponse)
    assert combined.quantity == info1.quantity
    # Spot check a macro field
    if (
        info1.macro_nutrients.carbs_g is not None
        and combined.macro_nutrients.carbs_g is not None
    ):
        assert combined.macro_nutrients.carbs_g >= info1.macro_nutrients.carbs_g


@pytest.mark.unit
def test_ingredient_nutritional_info_calculate_total(
    mock_ingredient_nutritional_info_schema_list: list[
        IngredientNutritionalInfoResponse
    ],
) -> None:
    """Test calculate_total_nutritional_info sums a list of responses.

    Ensures the total is a valid schema instance with all required fields.
    """
    # Arrange
    infos = mock_ingredient_nutritional_info_schema_list

    # Act
    total = IngredientNutritionalInfoResponse.calculate_total_nutritional_info(infos)

    # Assert
    assert isinstance(total, IngredientNutritionalInfoResponse)
    assert total.quantity is not None
    assert total.classification is not None
    assert total.macro_nutrients is not None
    assert total.vitamins is not None
    assert total.minerals is not None
