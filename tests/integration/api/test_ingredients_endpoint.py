"""Integration tests for ingredients API endpoint.

Tests cover:
- Full endpoint flow with mocked services
- Authentication and authorization
- Error handling with real middleware stack
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
    """Create sample nutrition response for testing."""
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


@pytest.fixture
def mock_nutrition_service(
    sample_nutrition_response: IngredientNutritionalInfoResponse,
) -> MagicMock:
    """Create mock nutrition service."""
    mock = MagicMock()
    mock.get_ingredient_nutrition = AsyncMock(return_value=sample_nutrition_response)
    mock.initialize = AsyncMock()
    mock.shutdown = AsyncMock()
    return mock


@pytest.fixture
async def ingredient_client(
    app: FastAPI,
    mock_nutrition_service: MagicMock,
) -> AsyncGenerator[AsyncClient]:
    """Create client with nutrition service mocked via dependency overrides."""

    async def mock_get_current_user() -> CurrentUser:
        return MOCK_USER

    async def mock_get_nutrition_service() -> MagicMock:
        return mock_nutrition_service

    # Set dependency overrides
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_nutrition_service] = mock_get_nutrition_service

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
    async def test_get_nutrition_success(
        self,
        ingredient_client: AsyncClient,
        mock_nutrition_service: MagicMock,
    ) -> None:
        """Should return nutrition data successfully."""
        response = await ingredient_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/nutritional-info"
        )

        assert response.status_code == 200

        data = response.json()
        assert "quantity" in data
        assert "macroNutrients" in data
        assert "vitamins" in data
        assert "minerals" in data

        # Verify service was called with correct parameters
        mock_nutrition_service.get_ingredient_nutrition.assert_called_once()
        call_args = mock_nutrition_service.get_ingredient_nutrition.call_args
        assert call_args.kwargs["name"] == "flour"
        assert call_args.kwargs["quantity"].amount == 100.0
        assert call_args.kwargs["quantity"].measurement == IngredientUnit.G

    @pytest.mark.asyncio
    async def test_get_nutrition_with_custom_quantity(
        self,
        ingredient_client: AsyncClient,
        mock_nutrition_service: MagicMock,
    ) -> None:
        """Should accept custom amount and measurement query parameters."""
        response = await ingredient_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/nutritional-info",
            params={"amount": 250, "measurement": "G"},
        )

        assert response.status_code == 200

        call_args = mock_nutrition_service.get_ingredient_nutrition.call_args
        assert call_args.kwargs["quantity"].amount == 250.0
        assert call_args.kwargs["quantity"].measurement == IngredientUnit.G

    @pytest.mark.asyncio
    async def test_get_nutrition_with_volume_measurement(
        self,
        ingredient_client: AsyncClient,
        mock_nutrition_service: MagicMock,
    ) -> None:
        """Should accept volume-based measurements."""
        response = await ingredient_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/nutritional-info",
            params={"amount": 2, "measurement": "CUP"},
        )

        assert response.status_code == 200

        call_args = mock_nutrition_service.get_ingredient_nutrition.call_args
        assert call_args.kwargs["quantity"].amount == 2.0
        assert call_args.kwargs["quantity"].measurement == IngredientUnit.CUP

    @pytest.mark.asyncio
    async def test_includes_middleware_headers(
        self,
        ingredient_client: AsyncClient,
    ) -> None:
        """Should include middleware headers in response."""
        response = await ingredient_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/nutritional-info"
        )

        assert response.status_code == 200

        # Check for middleware headers
        assert "x-request-id" in response.headers
        assert "x-process-time" in response.headers

    @pytest.mark.asyncio
    async def test_response_structure(
        self,
        ingredient_client: AsyncClient,
    ) -> None:
        """Should return properly structured response."""
        response = await ingredient_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/nutritional-info"
        )

        assert response.status_code == 200

        data = response.json()

        # Verify quantity structure
        assert "quantity" in data
        assert "amount" in data["quantity"]
        assert "measurement" in data["quantity"]

        # Verify macros structure
        assert "macroNutrients" in data
        macros = data["macroNutrients"]
        assert "calories" in macros
        assert "carbs" in macros
        assert "protein" in macros

        # Verify nutrient value structure
        assert "amount" in macros["calories"]
        assert "measurement" in macros["calories"]

    @pytest.mark.asyncio
    async def test_returns_400_for_partial_quantity_only_amount(
        self,
        ingredient_client: AsyncClient,
    ) -> None:
        """Should return 400 when only amount is provided."""
        response = await ingredient_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/nutritional-info",
            params={"amount": 250},
        )

        assert response.status_code == 400

        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "INVALID_QUANTITY_PARAMS" in data["message"]

    @pytest.mark.asyncio
    async def test_returns_400_for_partial_quantity_only_measurement(
        self,
        ingredient_client: AsyncClient,
    ) -> None:
        """Should return 400 when only measurement is provided."""
        response = await ingredient_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/nutritional-info",
            params={"measurement": "CUP"},
        )

        assert response.status_code == 400

        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "INVALID_QUANTITY_PARAMS" in data["message"]

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_ingredient(
        self,
        app: FastAPI,
    ) -> None:
        """Should return 404 when ingredient not found."""
        mock_service = MagicMock()
        mock_service.get_ingredient_nutrition = AsyncMock(return_value=None)

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_nutrition_service() -> MagicMock:
            return mock_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_nutrition_service] = mock_get_nutrition_service

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/ingredients/unknown_ingredient/nutritional-info"
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_nutrition_service, None)

        assert response.status_code == 404

        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "INGREDIENT_NOT_FOUND" in data["message"]
        assert "unknown_ingredient" in data["message"]

    @pytest.mark.asyncio
    async def test_returns_422_for_conversion_error(
        self,
        app: FastAPI,
    ) -> None:
        """Should return 422 when unit conversion fails."""
        mock_service = MagicMock()
        mock_service.get_ingredient_nutrition = AsyncMock(
            side_effect=ConversionError("Cannot convert PIECE to grams")
        )

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_nutrition_service() -> MagicMock:
            return mock_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_nutrition_service] = mock_get_nutrition_service

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/ingredients/flour/nutritional-info",
                    params={"amount": 1, "measurement": "PIECE"},
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_nutrition_service, None)

        assert response.status_code == 422

        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "CONVERSION_ERROR" in data["message"]

    @pytest.mark.asyncio
    async def test_returns_422_for_invalid_measurement(
        self,
        app: FastAPI,
        mock_nutrition_service: MagicMock,
    ) -> None:
        """Should return 422 for invalid measurement enum value."""

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_nutrition_service() -> MagicMock:
            return mock_nutrition_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_nutrition_service] = mock_get_nutrition_service

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/ingredients/flour/nutritional-info",
                    params={"amount": 100, "measurement": "INVALID_UNIT"},
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_nutrition_service, None)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_returns_422_for_negative_amount(
        self,
        app: FastAPI,
        mock_nutrition_service: MagicMock,
    ) -> None:
        """Should return 422 for negative amount value."""

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_nutrition_service() -> MagicMock:
            return mock_nutrition_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_nutrition_service] = mock_get_nutrition_service

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/ingredients/flour/nutritional-info",
                    params={"amount": -10, "measurement": "G"},
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_nutrition_service, None)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_url_encoded_ingredient_id(
        self,
        ingredient_client: AsyncClient,
        mock_nutrition_service: MagicMock,
    ) -> None:
        """Should handle URL-encoded ingredient IDs."""
        response = await ingredient_client.get(
            "/api/v1/recipe-scraper/ingredients/all%20purpose%20flour/nutritional-info"
        )

        assert response.status_code == 200

        call_args = mock_nutrition_service.get_ingredient_nutrition.call_args
        assert call_args.kwargs["name"] == "all purpose flour"


class TestIngredientEndpointAuthentication:
    """Tests for authentication on ingredients endpoint."""

    @pytest.mark.asyncio
    async def test_returns_401_without_auth(
        self,
        app: FastAPI,
    ) -> None:
        """Should return 401 when not authenticated."""
        # Don't override get_current_user - let it fail authentication
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
        mock_nutrition_service: MagicMock,
    ) -> None:
        """Should return 403 when user lacks required permission."""
        # User without recipe:read permission
        user_without_permission = CurrentUser(
            id="test-user-no-perms",
            roles=[],  # No roles
            permissions=[],  # No permissions
        )

        async def mock_get_current_user() -> CurrentUser:
            return user_without_permission

        async def mock_get_nutrition_service() -> MagicMock:
            return mock_nutrition_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_nutrition_service] = mock_get_nutrition_service

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
