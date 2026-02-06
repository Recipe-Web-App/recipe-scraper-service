"""Integration tests for ingredient nutritional info API endpoint.

Tests cover:
- Full endpoint flow with mocked services
- Authentication and authorization
- Error handling (400, 404, 422)
- Query parameter validation
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_nutrition_service
from app.auth.dependencies import CurrentUser, get_current_user
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


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import FastAPI


pytestmark = pytest.mark.integration


# Mock user for authenticated tests
MOCK_USER = CurrentUser(
    id="test-user-123",
    roles=["user"],
    permissions=["recipe:read"],
)


@pytest.fixture
def sample_nutrition_response() -> IngredientNutritionalInfoResponse:
    """Create sample nutrition response with all nutrient categories."""
    return IngredientNutritionalInfoResponse(
        quantity=Quantity(amount=100.0, measurement=IngredientUnit.G),
        usda_food_description="Flour, wheat, all-purpose, enriched",
        macro_nutrients=MacroNutrients(
            calories=NutrientValue(amount=364.0, measurement=NutrientUnit.KILOCALORIE),
            carbs=NutrientValue(amount=76.3, measurement=NutrientUnit.GRAM),
            protein=NutrientValue(amount=10.3, measurement=NutrientUnit.GRAM),
            cholesterol=NutrientValue(amount=0.0, measurement=NutrientUnit.MILLIGRAM),
            sodium=NutrientValue(amount=2.0, measurement=NutrientUnit.MILLIGRAM),
            fiber=NutrientValue(amount=2.7, measurement=NutrientUnit.GRAM),
            sugar=NutrientValue(amount=0.3, measurement=NutrientUnit.GRAM),
            fats=Fats(
                total=NutrientValue(amount=1.0, measurement=NutrientUnit.GRAM),
                saturated=NutrientValue(amount=0.2, measurement=NutrientUnit.GRAM),
            ),
        ),
        vitamins=Vitamins(
            vitamin_a=NutrientValue(amount=0.0, measurement=NutrientUnit.MICROGRAM),
            vitamin_c=NutrientValue(amount=0.0, measurement=NutrientUnit.MILLIGRAM),
            vitamin_d=NutrientValue(amount=0.0, measurement=NutrientUnit.MICROGRAM),
        ),
        minerals=Minerals(
            calcium=NutrientValue(amount=15.0, measurement=NutrientUnit.MILLIGRAM),
            iron=NutrientValue(amount=4.6, measurement=NutrientUnit.MILLIGRAM),
            potassium=NutrientValue(amount=107.0, measurement=NutrientUnit.MILLIGRAM),
        ),
    )


@pytest.fixture
def sample_scaled_nutrition_response() -> IngredientNutritionalInfoResponse:
    """Create sample nutrition response for custom quantity (250g flour)."""
    return IngredientNutritionalInfoResponse(
        quantity=Quantity(amount=250.0, measurement=IngredientUnit.G),
        usda_food_description="Flour, wheat, all-purpose, enriched",
        macro_nutrients=MacroNutrients(
            calories=NutrientValue(amount=910.0, measurement=NutrientUnit.KILOCALORIE),
            carbs=NutrientValue(amount=190.75, measurement=NutrientUnit.GRAM),
            protein=NutrientValue(amount=25.75, measurement=NutrientUnit.GRAM),
            fats=Fats(
                total=NutrientValue(amount=2.5, measurement=NutrientUnit.GRAM),
            ),
        ),
    )


@pytest.fixture
def mock_nutrition_service(
    sample_nutrition_response: IngredientNutritionalInfoResponse,
) -> MagicMock:
    """Create mock nutrition service returning sample data."""
    mock = MagicMock()
    mock.get_ingredient_nutrition = AsyncMock(return_value=sample_nutrition_response)
    mock.initialize = AsyncMock()
    mock.shutdown = AsyncMock()
    return mock


@pytest.fixture
async def ingredient_nutrition_client(
    app: FastAPI,
    mock_nutrition_service: MagicMock,
) -> AsyncGenerator[AsyncClient]:
    """Create client with nutrition service mocked."""

    async def mock_get_current_user() -> CurrentUser:
        return MOCK_USER

    async def mock_get_nutrition() -> MagicMock:
        return mock_nutrition_service

    # Set dependency overrides
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_nutrition_service] = mock_get_nutrition

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_nutrition_service, None)


class TestGetIngredientNutritionalInfoEndpoint:
    """Integration tests for GET /ingredients/{id}/nutritional-info endpoint."""

    @pytest.mark.asyncio
    async def test_get_nutrition_success_default_quantity(
        self,
        ingredient_nutrition_client: AsyncClient,
        mock_nutrition_service: MagicMock,
    ) -> None:
        """Should return 200 with nutrition data for 100g (default)."""
        response = await ingredient_nutrition_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/nutritional-info"
        )

        assert response.status_code == 200

        data = response.json()
        assert "quantity" in data
        assert data["quantity"]["amount"] == 100.0
        assert data["quantity"]["measurement"] == "G"
        assert "macroNutrients" in data
        assert "calories" in data["macroNutrients"]

        # Verify service was called with default quantity
        mock_nutrition_service.get_ingredient_nutrition.assert_called_once()
        call_args = mock_nutrition_service.get_ingredient_nutrition.call_args
        assert call_args.kwargs["name"] == "flour"
        assert call_args.kwargs["quantity"].amount == 100.0
        assert call_args.kwargs["quantity"].measurement == IngredientUnit.G

    @pytest.mark.asyncio
    async def test_get_nutrition_success_custom_quantity(
        self,
        app: FastAPI,
        sample_scaled_nutrition_response: IngredientNutritionalInfoResponse,
    ) -> None:
        """Should return 200 with scaled nutrition for custom amount/measurement."""
        mock_service = MagicMock()
        mock_service.get_ingredient_nutrition = AsyncMock(
            return_value=sample_scaled_nutrition_response
        )

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_nutrition() -> MagicMock:
            return mock_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_nutrition_service] = mock_get_nutrition

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/ingredients/flour/nutritional-info",
                    params={"amount": 250, "measurement": "G"},
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_nutrition_service, None)

        assert response.status_code == 200

        data = response.json()
        assert data["quantity"]["amount"] == 250.0
        assert data["quantity"]["measurement"] == "G"
        assert data["macroNutrients"]["calories"]["amount"] == 910.0

        # Verify service was called with custom quantity
        mock_service.get_ingredient_nutrition.assert_called_once()
        call_args = mock_service.get_ingredient_nutrition.call_args
        assert call_args.kwargs["quantity"].amount == 250.0

    @pytest.mark.asyncio
    async def test_returns_400_for_amount_without_measurement(
        self,
        ingredient_nutrition_client: AsyncClient,
        mock_nutrition_service: MagicMock,
    ) -> None:
        """Should return 400 when only amount is provided without measurement."""
        response = await ingredient_nutrition_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/nutritional-info",
            params={"amount": 100},
        )

        assert response.status_code == 400

        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "INVALID_QUANTITY_PARAMS" in data["message"]

        # Service should not be called
        mock_nutrition_service.get_ingredient_nutrition.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_400_for_measurement_without_amount(
        self,
        ingredient_nutrition_client: AsyncClient,
        mock_nutrition_service: MagicMock,
    ) -> None:
        """Should return 400 when only measurement is provided without amount."""
        response = await ingredient_nutrition_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/nutritional-info",
            params={"measurement": "G"},
        )

        assert response.status_code == 400

        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "INVALID_QUANTITY_PARAMS" in data["message"]

        # Service should not be called
        mock_nutrition_service.get_ingredient_nutrition.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_ingredient(
        self,
        app: FastAPI,
    ) -> None:
        """Should return 404 when ingredient not found in database."""
        mock_service = MagicMock()
        mock_service.get_ingredient_nutrition = AsyncMock(return_value=None)

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_nutrition() -> MagicMock:
            return mock_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_nutrition_service] = mock_get_nutrition

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/ingredients/unknown-ingredient/nutritional-info"
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_nutrition_service, None)

        assert response.status_code == 404

        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "INGREDIENT_NOT_FOUND" in data["message"]
        assert "unknown-ingredient" in data["message"]

    @pytest.mark.asyncio
    async def test_returns_422_for_invalid_unit_conversion(
        self,
        app: FastAPI,
    ) -> None:
        """Should return 422 when unit conversion fails."""
        mock_service = MagicMock()
        mock_service.get_ingredient_nutrition = AsyncMock(
            side_effect=ConversionError(
                "Cannot convert PIECE to grams without portion data"
            )
        )

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_nutrition() -> MagicMock:
            return mock_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_nutrition_service] = mock_get_nutrition

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/ingredients/eggs/nutritional-info",
                    params={"amount": 2, "measurement": "PIECE"},
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_nutrition_service, None)

        assert response.status_code == 422

        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "CONVERSION_ERROR" in data["message"]

    @pytest.mark.asyncio
    async def test_includes_usda_food_description(
        self,
        ingredient_nutrition_client: AsyncClient,
    ) -> None:
        """Should include USDA food description in response when available."""
        response = await ingredient_nutrition_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/nutritional-info"
        )

        assert response.status_code == 200

        data = response.json()
        assert "usdaFoodDescription" in data
        assert data["usdaFoodDescription"] == "Flour, wheat, all-purpose, enriched"

    @pytest.mark.asyncio
    async def test_includes_all_nutrient_categories(
        self,
        ingredient_nutrition_client: AsyncClient,
    ) -> None:
        """Should include all nutrient categories when available."""
        response = await ingredient_nutrition_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/nutritional-info"
        )

        assert response.status_code == 200

        data = response.json()
        assert "macroNutrients" in data
        assert "vitamins" in data
        assert "minerals" in data

        # Check macro structure
        macros = data["macroNutrients"]
        assert "calories" in macros
        assert "carbs" in macros
        assert "protein" in macros
        assert "fats" in macros

    @pytest.mark.asyncio
    async def test_includes_middleware_headers(
        self,
        ingredient_nutrition_client: AsyncClient,
    ) -> None:
        """Should include middleware headers in response."""
        response = await ingredient_nutrition_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/nutritional-info"
        )

        assert response.status_code == 200
        assert "x-request-id" in response.headers
        assert "x-process-time" in response.headers

    @pytest.mark.asyncio
    async def test_accepts_different_measurement_units(
        self,
        ingredient_nutrition_client: AsyncClient,
        mock_nutrition_service: MagicMock,
    ) -> None:
        """Should accept various valid measurement units."""
        for unit in ["G", "KG", "OZ", "LB", "CUP", "TBSP", "TSP"]:
            response = await ingredient_nutrition_client.get(
                "/api/v1/recipe-scraper/ingredients/flour/nutritional-info",
                params={"amount": 1, "measurement": unit},
            )

            assert response.status_code == 200, f"Failed for unit: {unit}"


class TestIngredientNutritionalInfoAuthentication:
    """Tests for authentication on ingredient nutritional info endpoint."""

    @pytest.mark.asyncio
    async def test_returns_401_without_auth(
        self,
        app: FastAPI,
    ) -> None:
        """Should return 401 when not authenticated."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/v1/recipe-scraper/ingredients/flour/nutritional-info"
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_403_without_permission(
        self,
        app: FastAPI,
    ) -> None:
        """Should return 403 when user lacks required permission."""
        mock_service = MagicMock()
        mock_service.get_ingredient_nutrition = AsyncMock(return_value=None)

        user_without_permission = CurrentUser(
            id="test-user-no-perms",
            roles=[],
            permissions=[],
        )

        async def mock_get_current_user() -> CurrentUser:
            return user_without_permission

        async def mock_get_nutrition() -> MagicMock:
            return mock_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_nutrition_service] = mock_get_nutrition

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/ingredients/flour/nutritional-info"
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_nutrition_service, None)

        assert response.status_code == 403
