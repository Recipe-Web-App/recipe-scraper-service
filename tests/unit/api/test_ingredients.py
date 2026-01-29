"""Unit tests for ingredients endpoint.

Tests cover:
- Get nutritional info endpoint
- Query parameter validation
- Error handling for various failure scenarios
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.dependencies import get_nutrition_service
from app.api.v1.endpoints.ingredients import get_ingredient_nutritional_info
from app.schemas.enums import IngredientUnit, NutrientUnit
from app.schemas.ingredient import Quantity
from app.schemas.nutrition import (
    Fats,
    IngredientNutritionalInfoResponse,
    MacroNutrients,
    Minerals,
    NutrientValue,
    Vitamins,
)
from app.services.nutrition.exceptions import ConversionError


pytestmark = pytest.mark.unit


class TestGetIngredientNutritionalInfo:
    """Tests for get_ingredient_nutritional_info endpoint."""

    @pytest.fixture
    def mock_user(self) -> MagicMock:
        """Create a mock authenticated user."""
        user = MagicMock()
        user.id = "user-123"
        return user

    @pytest.fixture
    def mock_nutrition_service(self) -> MagicMock:
        """Create a mock nutrition service."""
        return MagicMock()

    @pytest.fixture
    def sample_nutrition_response(self) -> IngredientNutritionalInfoResponse:
        """Create sample nutrition response."""
        return IngredientNutritionalInfoResponse(
            quantity=Quantity(amount=100.0, measurement=IngredientUnit.G),
            usda_food_description="Wheat flour, white, all-purpose",
            macro_nutrients=MacroNutrients(
                calories=NutrientValue(
                    amount=364.0,
                    measurement=NutrientUnit.KILOCALORIE,
                ),
                carbs=NutrientValue(amount=76.3, measurement=NutrientUnit.GRAM),
                protein=NutrientValue(amount=10.3, measurement=NutrientUnit.GRAM),
                fiber=NutrientValue(amount=2.7, measurement=NutrientUnit.GRAM),
                sugar=NutrientValue(amount=0.3, measurement=NutrientUnit.GRAM),
                fats=Fats(
                    total=NutrientValue(amount=1.0, measurement=NutrientUnit.GRAM),
                ),
            ),
            vitamins=Vitamins(
                vitamin_b6=NutrientValue(
                    amount=44.0,
                    measurement=NutrientUnit.MICROGRAM,
                ),
            ),
            minerals=Minerals(
                calcium=NutrientValue(amount=15.0, measurement=NutrientUnit.MILLIGRAM),
                iron=NutrientValue(amount=4.6, measurement=NutrientUnit.MILLIGRAM),
            ),
        )

    @pytest.mark.asyncio
    async def test_returns_nutrition_with_default_quantity(
        self,
        mock_user: MagicMock,
        mock_nutrition_service: MagicMock,
        sample_nutrition_response: IngredientNutritionalInfoResponse,
    ) -> None:
        """Should return nutrition data with default 100g quantity."""
        mock_nutrition_service.get_ingredient_nutrition = AsyncMock(
            return_value=sample_nutrition_response
        )

        result = await get_ingredient_nutritional_info(
            ingredient_id="flour",
            user=mock_user,
            nutrition_service=mock_nutrition_service,
            amount=None,
            measurement=None,
        )

        assert result == sample_nutrition_response
        mock_nutrition_service.get_ingredient_nutrition.assert_called_once()
        call_args = mock_nutrition_service.get_ingredient_nutrition.call_args
        assert call_args.kwargs["name"] == "flour"
        assert call_args.kwargs["quantity"].amount == 100.0
        assert call_args.kwargs["quantity"].measurement == IngredientUnit.G

    @pytest.mark.asyncio
    async def test_returns_nutrition_with_custom_quantity(
        self,
        mock_user: MagicMock,
        mock_nutrition_service: MagicMock,
        sample_nutrition_response: IngredientNutritionalInfoResponse,
    ) -> None:
        """Should return nutrition data scaled to custom quantity."""
        mock_nutrition_service.get_ingredient_nutrition = AsyncMock(
            return_value=sample_nutrition_response
        )

        result = await get_ingredient_nutritional_info(
            ingredient_id="flour",
            user=mock_user,
            nutrition_service=mock_nutrition_service,
            amount=250.0,
            measurement=IngredientUnit.G,
        )

        assert result == sample_nutrition_response
        call_args = mock_nutrition_service.get_ingredient_nutrition.call_args
        assert call_args.kwargs["quantity"].amount == 250.0
        assert call_args.kwargs["quantity"].measurement == IngredientUnit.G

    @pytest.mark.asyncio
    async def test_accepts_volume_measurement(
        self,
        mock_user: MagicMock,
        mock_nutrition_service: MagicMock,
        sample_nutrition_response: IngredientNutritionalInfoResponse,
    ) -> None:
        """Should accept volume-based measurements."""
        mock_nutrition_service.get_ingredient_nutrition = AsyncMock(
            return_value=sample_nutrition_response
        )

        result = await get_ingredient_nutritional_info(
            ingredient_id="flour",
            user=mock_user,
            nutrition_service=mock_nutrition_service,
            amount=2.0,
            measurement=IngredientUnit.CUP,
        )

        assert result == sample_nutrition_response
        call_args = mock_nutrition_service.get_ingredient_nutrition.call_args
        assert call_args.kwargs["quantity"].amount == 2.0
        assert call_args.kwargs["quantity"].measurement == IngredientUnit.CUP

    @pytest.mark.asyncio
    async def test_raises_400_when_only_amount_provided(
        self,
        mock_user: MagicMock,
        mock_nutrition_service: MagicMock,
    ) -> None:
        """Should raise 400 when only amount is provided."""
        with pytest.raises(HTTPException) as exc_info:
            await get_ingredient_nutritional_info(
                ingredient_id="flour",
                user=mock_user,
                nutrition_service=mock_nutrition_service,
                amount=100.0,
                measurement=None,
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "INVALID_QUANTITY_PARAMS"
        assert "Both 'amount' and 'measurement'" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_raises_400_when_only_measurement_provided(
        self,
        mock_user: MagicMock,
        mock_nutrition_service: MagicMock,
    ) -> None:
        """Should raise 400 when only measurement is provided."""
        with pytest.raises(HTTPException) as exc_info:
            await get_ingredient_nutritional_info(
                ingredient_id="flour",
                user=mock_user,
                nutrition_service=mock_nutrition_service,
                amount=None,
                measurement=IngredientUnit.CUP,
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "INVALID_QUANTITY_PARAMS"

    @pytest.mark.asyncio
    async def test_raises_404_when_ingredient_not_found(
        self,
        mock_user: MagicMock,
        mock_nutrition_service: MagicMock,
    ) -> None:
        """Should raise 404 when ingredient not found."""
        mock_nutrition_service.get_ingredient_nutrition = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_ingredient_nutritional_info(
                ingredient_id="unknown_ingredient",
                user=mock_user,
                nutrition_service=mock_nutrition_service,
                amount=None,
                measurement=None,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error"] == "INGREDIENT_NOT_FOUND"
        assert "unknown_ingredient" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_raises_422_when_conversion_fails(
        self,
        mock_user: MagicMock,
        mock_nutrition_service: MagicMock,
    ) -> None:
        """Should raise 422 when unit conversion fails."""
        mock_nutrition_service.get_ingredient_nutrition = AsyncMock(
            side_effect=ConversionError("Cannot convert PIECE to grams for flour")
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_ingredient_nutritional_info(
                ingredient_id="flour",
                user=mock_user,
                nutrition_service=mock_nutrition_service,
                amount=1.0,
                measurement=IngredientUnit.PIECE,
            )

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["error"] == "CONVERSION_ERROR"
        assert "Unable to convert quantity" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_handles_ingredient_id_with_spaces(
        self,
        mock_user: MagicMock,
        mock_nutrition_service: MagicMock,
        sample_nutrition_response: IngredientNutritionalInfoResponse,
    ) -> None:
        """Should handle ingredient IDs with spaces."""
        mock_nutrition_service.get_ingredient_nutrition = AsyncMock(
            return_value=sample_nutrition_response
        )

        result = await get_ingredient_nutritional_info(
            ingredient_id="all purpose flour",
            user=mock_user,
            nutrition_service=mock_nutrition_service,
            amount=None,
            measurement=None,
        )

        assert result == sample_nutrition_response
        call_args = mock_nutrition_service.get_ingredient_nutrition.call_args
        assert call_args.kwargs["name"] == "all purpose flour"


class TestGetNutritionServiceDependency:
    """Tests for nutrition service dependency."""

    @pytest.mark.asyncio
    async def test_returns_service_from_app_state(self) -> None:
        """Should return service from app state."""
        mock_request = MagicMock()
        mock_service = MagicMock()
        mock_request.app.state.nutrition_service = mock_service

        result = await get_nutrition_service(mock_request)

        assert result is mock_service

    @pytest.mark.asyncio
    async def test_raises_503_when_service_not_available(self) -> None:
        """Should raise 503 when nutrition service not in app state."""
        mock_request = MagicMock()
        mock_request.app.state.nutrition_service = None

        with pytest.raises(HTTPException) as exc_info:
            await get_nutrition_service(mock_request)

        assert exc_info.value.status_code == 503
        assert "Nutrition service not available" in exc_info.value.detail
