"""Integration tests for ingredient shopping info API endpoint.

Tests cover:
- Full endpoint flow with mocked services
- Authentication and authorization
- Error handling with real middleware stack
- Query parameter validation
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_shopping_service
from app.auth.dependencies import CurrentUser, get_current_user
from app.schemas.enums import IngredientUnit
from app.schemas.ingredient import Quantity
from app.schemas.shopping import IngredientShoppingInfoResponse
from app.services.nutrition.exceptions import ConversionError
from app.services.shopping.exceptions import IngredientNotFoundError


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
def sample_shopping_result() -> IngredientShoppingInfoResponse:
    """Create sample shopping result with all data."""
    return IngredientShoppingInfoResponse(
        ingredient_name="flour",
        quantity=Quantity(amount=100.0, measurement=IngredientUnit.G),
        estimated_price="0.18",
        price_confidence=0.85,
        data_source="USDA_FVP",
        currency="USD",
    )


@pytest.fixture
def mock_shopping_service(
    sample_shopping_result: IngredientShoppingInfoResponse,
) -> MagicMock:
    """Create mock shopping service."""
    mock = MagicMock()
    mock.get_ingredient_shopping_info = AsyncMock(return_value=sample_shopping_result)
    mock.initialize = AsyncMock()
    mock.shutdown = AsyncMock()
    return mock


@pytest.fixture
async def ingredient_shopping_client(
    app: FastAPI,
    mock_shopping_service: MagicMock,
) -> AsyncGenerator[AsyncClient]:
    """Create client with shopping service mocked."""

    async def mock_get_current_user() -> CurrentUser:
        return MOCK_USER

    async def mock_get_shopping() -> MagicMock:
        return mock_shopping_service

    # Set dependency overrides
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_shopping_service] = mock_get_shopping

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_shopping_service, None)


class TestGetIngredientShoppingInfoEndpoint:
    """Integration tests for GET /ingredients/{id}/shopping-info endpoint."""

    @pytest.mark.asyncio
    async def test_get_shopping_info_success(
        self,
        ingredient_shopping_client: AsyncClient,
        mock_shopping_service: MagicMock,
    ) -> None:
        """Should return 200 with shopping data."""
        response = await ingredient_shopping_client.get(
            "/api/v1/recipe-scraper/ingredients/101/shopping-info"
        )

        assert response.status_code == 200

        data = response.json()
        assert data["ingredientName"] == "flour"
        assert data["estimatedPrice"] == "0.18"
        assert data["priceConfidence"] == 0.85
        assert data["dataSource"] == "USDA_FVP"

        # Verify service was called
        mock_shopping_service.get_ingredient_shopping_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_shopping_info_with_quantity(
        self,
        ingredient_shopping_client: AsyncClient,
        mock_shopping_service: MagicMock,
    ) -> None:
        """Should pass quantity parameters to service."""
        response = await ingredient_shopping_client.get(
            "/api/v1/recipe-scraper/ingredients/101/shopping-info",
            params={"amount": 250.0, "measurement": "G"},
        )

        assert response.status_code == 200

        # Verify service was called with quantity
        call_args = mock_shopping_service.get_ingredient_shopping_info.call_args
        assert call_args.kwargs["ingredient_id"] == 101
        assert call_args.kwargs["quantity"].amount == 250.0
        assert call_args.kwargs["quantity"].measurement == IngredientUnit.G

    @pytest.mark.asyncio
    async def test_returns_400_for_partial_quantity_params(
        self,
        ingredient_shopping_client: AsyncClient,
    ) -> None:
        """Should return 400 when only amount or measurement provided."""
        # Only amount
        response = await ingredient_shopping_client.get(
            "/api/v1/recipe-scraper/ingredients/101/shopping-info",
            params={"amount": 250.0},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "INVALID_QUANTITY_PARAMS" in data["message"]

    @pytest.mark.asyncio
    async def test_returns_400_for_only_measurement(
        self,
        ingredient_shopping_client: AsyncClient,
    ) -> None:
        """Should return 400 when only measurement provided."""
        response = await ingredient_shopping_client.get(
            "/api/v1/recipe-scraper/ingredients/101/shopping-info",
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
        mock_service.get_ingredient_shopping_info = AsyncMock(
            side_effect=IngredientNotFoundError(
                "Ingredient not found", ingredient_id=999
            )
        )

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_shopping() -> MagicMock:
            return mock_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_shopping_service] = mock_get_shopping

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/ingredients/999/shopping-info"
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_shopping_service, None)

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "INGREDIENT_NOT_FOUND" in data["message"]

    @pytest.mark.asyncio
    async def test_returns_422_for_conversion_error(
        self,
        app: FastAPI,
    ) -> None:
        """Should return 422 when unit conversion fails."""
        mock_service = MagicMock()
        mock_service.get_ingredient_shopping_info = AsyncMock(
            side_effect=ConversionError("Cannot convert PIECE to G for flour")
        )

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_shopping() -> MagicMock:
            return mock_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_shopping_service] = mock_get_shopping

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/ingredients/101/shopping-info",
                    params={"amount": 2.0, "measurement": "PIECE"},
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_shopping_service, None)

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "CONVERSION_ERROR" in data["message"]

    @pytest.mark.asyncio
    async def test_includes_middleware_headers(
        self,
        ingredient_shopping_client: AsyncClient,
    ) -> None:
        """Should include middleware headers in response."""
        response = await ingredient_shopping_client.get(
            "/api/v1/recipe-scraper/ingredients/101/shopping-info"
        )

        assert response.status_code == 200
        assert "x-request-id" in response.headers
        assert "x-process-time" in response.headers


class TestIngredientShoppingInfoAuthentication:
    """Tests for authentication on ingredient shopping info endpoint."""

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
                "/api/v1/recipe-scraper/ingredients/101/shopping-info"
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_403_without_permission(
        self,
        app: FastAPI,
        mock_shopping_service: MagicMock,
    ) -> None:
        """Should return 403 when user lacks required permission."""
        user_without_permission = CurrentUser(
            id="test-user-no-perms",
            roles=[],
            permissions=[],
        )

        async def mock_get_current_user() -> CurrentUser:
            return user_without_permission

        async def mock_get_shopping() -> MagicMock:
            return mock_shopping_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_shopping_service] = mock_get_shopping

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/ingredients/101/shopping-info"
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_shopping_service, None)

        assert response.status_code == 403
