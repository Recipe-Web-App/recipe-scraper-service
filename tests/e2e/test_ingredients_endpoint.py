"""End-to-end tests for the ingredients endpoints.

Tests verify the full ingredient shopping info flow with authentication
and service mocking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_shopping_service
from app.auth.providers import set_auth_provider, shutdown_auth_provider
from app.auth.providers.header import HeaderAuthProvider
from app.core.config import Settings
from app.core.config.settings import (
    ApiSettings,
    AppSettings,
    AuthSettings,
    LoggingSettings,
    ObservabilitySettings,
    RateLimitingSettings,
    RedisSettings,
    ServerSettings,
)
from app.core.config.settings import (
    get_settings as _get_settings,
)
from app.factory import create_app
from app.schemas.enums import IngredientUnit
from app.schemas.ingredient import Quantity
from app.schemas.shopping import IngredientShoppingInfoResponse


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import FastAPI


pytestmark = pytest.mark.e2e


@pytest.fixture
def ingredients_test_settings(redis_url: str) -> Settings:
    """Create test settings for ingredient tests."""
    parts = redis_url.replace("redis://", "").split(":")
    redis_host = parts[0]
    redis_port = int(parts[1])

    return Settings(
        APP_ENV="test",
        JWT_SECRET_KEY="e2e-test-jwt-secret-key-for-ingredients",
        REDIS_PASSWORD="",
        app=AppSettings(
            name="e2e-ingredient-test-app",
            version="0.0.1-e2e",
            debug=True,
        ),
        server=ServerSettings(
            host="0.0.0.0",
            port=8000,
        ),
        api=ApiSettings(
            cors_origins=["http://localhost:3000"],
        ),
        auth=AuthSettings(
            mode="header",
        ),
        redis=RedisSettings(
            host=redis_host,
            port=redis_port,
            cache_db=0,
            queue_db=1,
            rate_limit_db=2,
        ),
        rate_limiting=RateLimitingSettings(
            default="100/minute",
            auth="10/minute",
        ),
        logging=LoggingSettings(
            level="DEBUG",
            format="json",
        ),
        observability=ObservabilitySettings(),
    )


@pytest.fixture
async def ingredients_app(
    ingredients_test_settings: Settings,
) -> AsyncGenerator[FastAPI]:
    """Create FastAPI app for ingredient tests."""
    _get_settings.cache_clear()

    provider = HeaderAuthProvider(
        user_id_header="X-User-ID",
        roles_header="X-User-Roles",
        permissions_header="X-User-Permissions",
        default_roles=[],
    )
    await provider.initialize()
    set_auth_provider(provider)

    try:
        with (
            patch(
                "app.observability.metrics.get_settings",
                return_value=ingredients_test_settings,
            ),
            patch(
                "app.observability.tracing.get_settings",
                return_value=ingredients_test_settings,
            ),
            patch(
                "app.core.config.get_settings",
                return_value=ingredients_test_settings,
            ),
            patch(
                "app.core.config.settings.get_settings",
                return_value=ingredients_test_settings,
            ),
        ):
            app = create_app(ingredients_test_settings)
            yield app
    finally:
        await shutdown_auth_provider()
        _get_settings.cache_clear()


@pytest.fixture
async def ingredients_client(
    ingredients_app: FastAPI,
) -> AsyncGenerator[AsyncClient]:
    """Create async HTTP client for ingredient testing."""
    async with AsyncClient(
        transport=ASGITransport(app=ingredients_app),
        base_url="http://test",
    ) as ac:
        yield ac


def auth_headers(
    user_id: str = "e2e-test-user",
    roles: str = "user",
    permissions: str = "recipe:read",
) -> dict[str, str]:
    """Create auth headers for header-based authentication."""
    return {
        "Authorization": "Bearer ignored-in-header-mode",
        "X-User-ID": user_id,
        "X-User-Roles": roles,
        "X-User-Permissions": permissions,
    }


class TestIngredientShoppingInfoE2E:
    """E2E tests for the GET /ingredients/{id}/shopping-info endpoint."""

    async def test_get_shopping_info_full_flow(
        self,
        ingredients_client: AsyncClient,
    ) -> None:
        """Test the complete shopping info retrieval flow."""
        ingredient_id = 101

        # Mock shopping result
        mock_shopping_result = IngredientShoppingInfoResponse(
            ingredient_name="flour",
            quantity=Quantity(amount=100.0, measurement=IngredientUnit.G),
            estimated_price="0.18",
            price_confidence=0.85,
            data_source="USDA_FVP",
            currency="USD",
        )

        mock_shopping_service = MagicMock()
        mock_shopping_service.get_ingredient_shopping_info = AsyncMock(
            return_value=mock_shopping_result
        )

        # Override shopping service
        ingredients_client._transport.app.dependency_overrides[get_shopping_service] = (
            lambda: mock_shopping_service
        )

        try:
            response = await ingredients_client.get(
                f"/api/v1/recipe-scraper/ingredients/{ingredient_id}/shopping-info",
                headers=auth_headers(),
            )
        finally:
            ingredients_client._transport.app.dependency_overrides.pop(
                get_shopping_service, None
            )

        assert response.status_code == 200
        data = response.json()

        assert data["ingredientName"] == "flour"
        assert data["estimatedPrice"] == "0.18"
        assert data["priceConfidence"] == 0.85
        assert data["dataSource"] == "USDA_FVP"

    async def test_get_shopping_info_with_quantity(
        self,
        ingredients_client: AsyncClient,
    ) -> None:
        """Test shopping info with custom quantity."""
        ingredient_id = 101

        mock_shopping_result = IngredientShoppingInfoResponse(
            ingredient_name="flour",
            quantity=Quantity(amount=250.0, measurement=IngredientUnit.G),
            estimated_price="0.45",
            price_confidence=0.85,
            data_source="USDA_FVP",
            currency="USD",
        )

        mock_shopping_service = MagicMock()
        mock_shopping_service.get_ingredient_shopping_info = AsyncMock(
            return_value=mock_shopping_result
        )

        ingredients_client._transport.app.dependency_overrides[get_shopping_service] = (
            lambda: mock_shopping_service
        )

        try:
            response = await ingredients_client.get(
                f"/api/v1/recipe-scraper/ingredients/{ingredient_id}/shopping-info",
                params={"amount": 250.0, "measurement": "G"},
                headers=auth_headers(),
            )
        finally:
            ingredients_client._transport.app.dependency_overrides.pop(
                get_shopping_service, None
            )

        assert response.status_code == 200
        data = response.json()
        assert data["quantity"]["amount"] == 250.0
        assert data["estimatedPrice"] == "0.45"

    async def test_shopping_info_unauthorized(
        self,
        ingredients_client: AsyncClient,
    ) -> None:
        """Test that unauthenticated requests are rejected."""
        response = await ingredients_client.get(
            "/api/v1/recipe-scraper/ingredients/101/shopping-info",
        )

        assert response.status_code == 401

    async def test_shopping_info_forbidden_without_permission(
        self,
        ingredients_client: AsyncClient,
    ) -> None:
        """Test that requests without recipe:read permission are rejected."""
        response = await ingredients_client.get(
            "/api/v1/recipe-scraper/ingredients/101/shopping-info",
            headers=auth_headers(roles="", permissions="recipe:create"),
        )

        assert response.status_code == 403

    async def test_shopping_info_invalid_params(
        self,
        ingredients_client: AsyncClient,
    ) -> None:
        """Test that partial quantity params return 400."""
        # Mock shopping service (needed for dependency resolution)
        mock_shopping_service = MagicMock()
        ingredients_client._transport.app.dependency_overrides[get_shopping_service] = (
            lambda: mock_shopping_service
        )

        try:
            response = await ingredients_client.get(
                "/api/v1/recipe-scraper/ingredients/101/shopping-info",
                params={"amount": 250.0},  # Missing measurement
                headers=auth_headers(),
            )
        finally:
            ingredients_client._transport.app.dependency_overrides.pop(
                get_shopping_service, None
            )

        assert response.status_code == 400
        data = response.json()
        assert "INVALID_QUANTITY_PARAMS" in data["message"]
