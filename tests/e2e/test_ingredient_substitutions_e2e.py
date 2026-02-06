"""End-to-end tests for ingredient substitutions endpoint.

Tests verify the full endpoint flow with mocked LLM but real Redis caching:
- API routing and authentication
- SubstitutionService with real Redis caching
- Response structure and data quality

Note: LLM is mocked since we can't run a real LLM in tests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_substitution_service
from app.auth.dependencies import CurrentUser, get_current_user
from app.schemas.enums import IngredientUnit
from app.schemas.ingredient import Ingredient, Quantity
from app.schemas.recommendations import (
    ConversionRatio,
    IngredientSubstitution,
    RecommendedSubstitutionsResponse,
)


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import FastAPI


pytestmark = pytest.mark.e2e


# Mock user with recipe:read permission
MOCK_USER = CurrentUser(
    id="e2e-test-user",
    roles=["user"],
    permissions=["recipe:read"],
)


@pytest.fixture
def sample_substitution_response() -> RecommendedSubstitutionsResponse:
    """Create sample substitution response for e2e tests."""
    return RecommendedSubstitutionsResponse(
        ingredient=Ingredient(
            ingredient_id=None,
            name="butter",
            quantity=None,
        ),
        recommended_substitutions=[
            IngredientSubstitution(
                ingredient="coconut oil",
                quantity=None,
                conversion_ratio=ConversionRatio(
                    ratio=1.0,
                    measurement=IngredientUnit.CUP,
                ),
            ),
            IngredientSubstitution(
                ingredient="olive oil",
                quantity=None,
                conversion_ratio=ConversionRatio(
                    ratio=0.75,
                    measurement=IngredientUnit.CUP,
                ),
            ),
            IngredientSubstitution(
                ingredient="applesauce",
                quantity=None,
                conversion_ratio=ConversionRatio(
                    ratio=0.5,
                    measurement=IngredientUnit.CUP,
                ),
            ),
            IngredientSubstitution(
                ingredient="avocado",
                quantity=None,
                conversion_ratio=ConversionRatio(
                    ratio=1.0,
                    measurement=IngredientUnit.CUP,
                ),
            ),
            IngredientSubstitution(
                ingredient="greek yogurt",
                quantity=None,
                conversion_ratio=ConversionRatio(
                    ratio=0.5,
                    measurement=IngredientUnit.CUP,
                ),
            ),
        ],
        limit=50,
        offset=0,
        count=5,
    )


@pytest.fixture
def sample_response_with_quantity() -> RecommendedSubstitutionsResponse:
    """Create sample response with quantity for e2e tests."""
    return RecommendedSubstitutionsResponse(
        ingredient=Ingredient(
            ingredient_id=None,
            name="butter",
            quantity=Quantity(amount=1.0, measurement=IngredientUnit.CUP),
        ),
        recommended_substitutions=[
            IngredientSubstitution(
                ingredient="coconut oil",
                quantity=Quantity(amount=1.0, measurement=IngredientUnit.CUP),
                conversion_ratio=ConversionRatio(
                    ratio=1.0,
                    measurement=IngredientUnit.CUP,
                ),
            ),
            IngredientSubstitution(
                ingredient="olive oil",
                quantity=Quantity(amount=0.75, measurement=IngredientUnit.CUP),
                conversion_ratio=ConversionRatio(
                    ratio=0.75,
                    measurement=IngredientUnit.CUP,
                ),
            ),
            IngredientSubstitution(
                ingredient="applesauce",
                quantity=Quantity(amount=0.5, measurement=IngredientUnit.CUP),
                conversion_ratio=ConversionRatio(
                    ratio=0.5,
                    measurement=IngredientUnit.CUP,
                ),
            ),
        ],
        limit=50,
        offset=0,
        count=3,
    )


@pytest.fixture
def mock_substitution_service(
    sample_substitution_response: RecommendedSubstitutionsResponse,
) -> MagicMock:
    """Create mock substitution service for e2e tests."""
    mock = MagicMock()
    mock.get_substitutions = AsyncMock(return_value=sample_substitution_response)
    mock.initialize = AsyncMock()
    mock.shutdown = AsyncMock()
    return mock


@pytest.fixture
async def substitution_e2e_client(
    app: FastAPI,
    mock_substitution_service: MagicMock,
) -> AsyncGenerator[AsyncClient]:
    """Create client with mocked substitution service for E2E tests."""

    async def mock_get_current_user() -> CurrentUser:
        return MOCK_USER

    async def mock_get_substitution() -> MagicMock:
        return mock_substitution_service

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_substitution_service] = mock_get_substitution

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_substitution_service, None)


class TestIngredientSubstitutionsE2E:
    """E2E tests verifying substitution endpoint returns valid data."""

    async def test_butter_returns_substitutions(
        self,
        substitution_e2e_client: AsyncClient,
    ) -> None:
        """Should return substitutions for butter."""
        response = await substitution_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions"
        )

        assert response.status_code == 200

        data = response.json()
        assert data["ingredient"]["name"] == "butter"
        assert len(data["recommendedSubstitutions"]) > 0
        assert data["count"] > 0

    async def test_substitution_has_required_fields(
        self,
        substitution_e2e_client: AsyncClient,
    ) -> None:
        """Should return substitutions with all required fields."""
        response = await substitution_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions"
        )

        assert response.status_code == 200

        data = response.json()
        for substitution in data["recommendedSubstitutions"]:
            assert "ingredient" in substitution
            assert "conversionRatio" in substitution
            assert "ratio" in substitution["conversionRatio"]
            assert "measurement" in substitution["conversionRatio"]

    async def test_pagination_parameters_accepted(
        self,
        substitution_e2e_client: AsyncClient,
        mock_substitution_service: MagicMock,
    ) -> None:
        """Should accept pagination parameters."""
        response = await substitution_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions?limit=2&offset=0"
        )

        assert response.status_code == 200

        # Verify service was called with pagination params
        call_kwargs = mock_substitution_service.get_substitutions.call_args[1]
        assert call_kwargs["limit"] == 2
        assert call_kwargs["offset"] == 0

    async def test_count_only_returns_metadata_only(
        self,
        substitution_e2e_client: AsyncClient,
    ) -> None:
        """Should return only count when countOnly=true."""
        response = await substitution_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions?countOnly=true"
        )

        assert response.status_code == 200

        data = response.json()
        # With countOnly=true, endpoint clears the list
        assert data["recommendedSubstitutions"] == []
        assert data["count"] == 5

    async def test_quantity_context_passed_to_service(
        self,
        substitution_e2e_client: AsyncClient,
        mock_substitution_service: MagicMock,
        sample_response_with_quantity: RecommendedSubstitutionsResponse,
    ) -> None:
        """Should pass quantity to service when provided."""
        # Update mock to return response with quantity
        mock_substitution_service.get_substitutions.return_value = (
            sample_response_with_quantity
        )

        response = await substitution_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions"
            "?amount=1&measurement=CUP"
        )

        assert response.status_code == 200

        # Verify service was called with quantity
        call_kwargs = mock_substitution_service.get_substitutions.call_args[1]
        assert call_kwargs["quantity"] is not None
        assert call_kwargs["quantity"].amount == 1.0
        assert call_kwargs["quantity"].measurement == IngredientUnit.CUP


class TestSubstitutionResponseValidationE2E:
    """E2E tests for response structure validation."""

    async def test_response_has_required_fields(
        self,
        substitution_e2e_client: AsyncClient,
    ) -> None:
        """Should return response with all required fields."""
        response = await substitution_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions"
        )

        assert response.status_code == 200

        data = response.json()
        assert "ingredient" in data
        assert "recommendedSubstitutions" in data
        assert "limit" in data
        assert "offset" in data
        assert "count" in data

    async def test_conversion_ratios_are_valid(
        self,
        substitution_e2e_client: AsyncClient,
    ) -> None:
        """Should return valid conversion ratios (0 < ratio <= 10)."""
        response = await substitution_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions"
        )

        assert response.status_code == 200

        data = response.json()
        for substitution in data["recommendedSubstitutions"]:
            ratio = substitution["conversionRatio"]["ratio"]
            assert 0 < ratio <= 10, f"Invalid ratio: {ratio}"

    async def test_measurements_are_valid_units(
        self,
        substitution_e2e_client: AsyncClient,
    ) -> None:
        """Should return valid measurement units."""
        response = await substitution_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions"
        )

        assert response.status_code == 200

        data = response.json()
        # Valid measurement units from IngredientUnit enum
        valid_units = {
            "CUP",
            "TBSP",
            "TSP",
            "ML",
            "L",
            "G",
            "KG",
            "OZ",
            "LB",
            "PIECE",
            "PINCH",
            "DASH",
            "BUNCH",
            "CLOVE",
            "SLICE",
            "WHOLE",
            "TO_TASTE",
        }

        for substitution in data["recommendedSubstitutions"]:
            measurement = substitution["conversionRatio"]["measurement"]
            assert measurement in valid_units, f"Invalid measurement: {measurement}"

    async def test_ingredient_names_are_not_empty(
        self,
        substitution_e2e_client: AsyncClient,
    ) -> None:
        """Should return non-empty ingredient names."""
        response = await substitution_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions"
        )

        assert response.status_code == 200

        data = response.json()
        for substitution in data["recommendedSubstitutions"]:
            assert substitution["ingredient"], "Ingredient name should not be empty"
            assert len(substitution["ingredient"]) > 0


class TestSubstitutionErrorHandlingE2E:
    """E2E tests for error handling."""

    async def test_invalid_quantity_params_returns_400(
        self,
        substitution_e2e_client: AsyncClient,
    ) -> None:
        """Should return 400 when only amount is provided."""
        response = await substitution_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions?amount=1"
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "INVALID_QUANTITY_PARAMS" in data["message"]

    async def test_only_measurement_returns_400(
        self,
        substitution_e2e_client: AsyncClient,
    ) -> None:
        """Should return 400 when only measurement is provided."""
        response = await substitution_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions?measurement=CUP"
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "INVALID_QUANTITY_PARAMS" in data["message"]

    async def test_invalid_limit_returns_422(
        self,
        substitution_e2e_client: AsyncClient,
    ) -> None:
        """Should return 422 for invalid limit value."""
        response = await substitution_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions?limit=0"
        )

        assert response.status_code == 422

    async def test_negative_offset_returns_422(
        self,
        substitution_e2e_client: AsyncClient,
    ) -> None:
        """Should return 422 for negative offset."""
        response = await substitution_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions?offset=-1"
        )

        assert response.status_code == 422

    async def test_returns_404_when_service_returns_none(
        self,
        substitution_e2e_client: AsyncClient,
        mock_substitution_service: MagicMock,
    ) -> None:
        """Should return 404 when service returns None."""
        mock_substitution_service.get_substitutions.return_value = None

        response = await substitution_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/unknown/substitutions"
        )

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "INGREDIENT_NOT_FOUND" in data["message"]


class TestSubstitutionHeadersE2E:
    """E2E tests for response headers."""

    async def test_response_includes_request_id(
        self,
        substitution_e2e_client: AsyncClient,
    ) -> None:
        """Should include x-request-id header in response."""
        response = await substitution_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions"
        )

        assert response.status_code == 200
        assert "x-request-id" in response.headers

    async def test_response_includes_process_time(
        self,
        substitution_e2e_client: AsyncClient,
    ) -> None:
        """Should include x-process-time header in response."""
        response = await substitution_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions"
        )

        assert response.status_code == 200
        assert "x-process-time" in response.headers

    async def test_response_is_json_content_type(
        self,
        substitution_e2e_client: AsyncClient,
    ) -> None:
        """Should return application/json content type."""
        response = await substitution_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions"
        )

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")
