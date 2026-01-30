"""End-to-end tests for nutritional-info endpoints.

Tests verify that common ingredients (flour, butter, eggs, chicken, rice)
return valid nutritional data from the full stack including:
- API routing and authentication
- NutritionService with caching
- NutritionRepository (PostgreSQL)
- UnitConverter for quantity scaling

These tests use real testcontainers for PostgreSQL and Redis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from app.api.dependencies import get_nutrition_service
from app.auth.dependencies import CurrentUser, get_current_user
from app.database.repositories.nutrition import NutritionRepository
from app.services.nutrition.service import NutritionService


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from asyncpg import Pool
    from fastapi import FastAPI


pytestmark = pytest.mark.e2e


# Mock user with recipe:read permission
MOCK_USER = CurrentUser(
    id="e2e-test-user",
    roles=["user"],
    permissions=["recipe:read"],
)


@pytest.fixture
async def nutrition_cache_client(redis_url: str) -> AsyncGenerator[Redis[bytes]]:
    """Create a Redis client for nutrition caching."""
    client: Redis[bytes] = Redis.from_url(redis_url, decode_responses=False)
    await client.flushdb()
    try:
        yield client
    finally:
        await client.aclose()  # type: ignore[attr-defined]


@pytest.fixture
async def nutrition_repository(nutrition_db_pool: Pool) -> NutritionRepository:
    """Create NutritionRepository with test database pool."""
    return NutritionRepository(pool=nutrition_db_pool)


@pytest.fixture
async def nutrition_service(
    nutrition_cache_client: Redis[bytes],
    nutrition_repository: NutritionRepository,
) -> AsyncGenerator[NutritionService]:
    """Create NutritionService with real Redis and PostgreSQL."""
    svc = NutritionService(
        cache_client=nutrition_cache_client,
        repository=nutrition_repository,
    )
    await svc.initialize()
    yield svc
    await svc.shutdown()


@pytest.fixture
async def nutrition_e2e_client(
    app: FastAPI,
    nutrition_service: NutritionService,
) -> AsyncGenerator[AsyncClient]:
    """Create client with real nutrition service for E2E tests."""

    async def mock_get_current_user() -> CurrentUser:
        return MOCK_USER

    async def mock_get_nutrition() -> NutritionService:
        return nutrition_service

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_nutrition_service] = mock_get_nutrition

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_nutrition_service, None)


class TestCommonIngredientsNutritionE2E:
    """E2E tests verifying common ingredients return valid nutrition data."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("ingredient_name", "expected_min_calories"),
        [
            ("flour", 300),  # ~364 kcal/100g
            ("butter", 650),  # ~717 kcal/100g
            ("eggs", 120),  # ~155 kcal/100g
            ("chicken", 100),  # ~165 kcal/100g
            ("rice", 100),  # ~130 kcal/100g
        ],
    )
    async def test_common_ingredient_returns_valid_calories(
        self,
        nutrition_e2e_client: AsyncClient,
        ingredient_name: str,
        expected_min_calories: float,
    ) -> None:
        """Should return valid calorie data for common ingredient."""
        response = await nutrition_e2e_client.get(
            f"/api/v1/recipe-scraper/ingredients/{ingredient_name}/nutritional-info"
        )

        assert response.status_code == 200

        data = response.json()

        # Validate response structure
        assert "quantity" in data
        assert data["quantity"]["amount"] == 100.0
        assert data["quantity"]["measurement"] == "G"

        # Validate macronutrients present
        assert "macroNutrients" in data
        assert "calories" in data["macroNutrients"]
        assert data["macroNutrients"]["calories"]["amount"] >= expected_min_calories
        assert data["macroNutrients"]["calories"]["measurement"] == "KILOCALORIE"

    @pytest.mark.asyncio
    async def test_flour_full_nutrition_profile(
        self,
        nutrition_e2e_client: AsyncClient,
    ) -> None:
        """Should return complete nutrition profile for flour."""
        response = await nutrition_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/nutritional-info"
        )

        assert response.status_code == 200

        data = response.json()

        # Check USDA description
        assert "usdaFoodDescription" in data
        assert "flour" in data["usdaFoodDescription"].lower()

        # Check all macro categories
        macros = data["macroNutrients"]
        assert "calories" in macros
        assert "carbs" in macros
        assert "protein" in macros
        assert "fats" in macros
        assert "fiber" in macros

        # Flour-specific values (per 100g)
        assert macros["calories"]["amount"] >= 360
        assert macros["carbs"]["amount"] >= 70
        assert macros["protein"]["amount"] >= 10

        # Check vitamins and minerals present
        assert "vitamins" in data
        assert "minerals" in data

    @pytest.mark.asyncio
    async def test_butter_with_custom_quantity(
        self,
        nutrition_e2e_client: AsyncClient,
    ) -> None:
        """Should correctly scale butter nutrition for 1 tbsp (14.2g)."""
        response = await nutrition_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/nutritional-info",
            params={"amount": 1, "measurement": "TBSP"},
        )

        assert response.status_code == 200

        data = response.json()

        # 1 tbsp butter = 14.2g
        assert data["quantity"]["amount"] == 1
        assert data["quantity"]["measurement"] == "TBSP"

        # 1 tbsp butter ~= 102 kcal (717 * 14.2 / 100)
        calories = data["macroNutrients"]["calories"]["amount"]
        assert 90 <= calories <= 120, f"Expected ~102 kcal, got {calories}"

    @pytest.mark.asyncio
    async def test_eggs_with_piece_unit(
        self,
        nutrition_e2e_client: AsyncClient,
    ) -> None:
        """Should correctly scale egg nutrition for 1 large egg (50g)."""
        response = await nutrition_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/eggs/nutritional-info",
            params={"amount": 1, "measurement": "PIECE"},
        )

        assert response.status_code == 200

        data = response.json()

        # 1 large egg = 50g
        assert data["quantity"]["amount"] == 1
        assert data["quantity"]["measurement"] == "PIECE"

        # 1 egg ~= 78 kcal (155 * 50 / 100)
        calories = data["macroNutrients"]["calories"]["amount"]
        assert 70 <= calories <= 90, f"Expected ~78 kcal, got {calories}"

        # 1 egg ~= 6.5g protein
        protein = data["macroNutrients"]["protein"]["amount"]
        assert 5.5 <= protein <= 7.5, f"Expected ~6.5g protein, got {protein}"

    @pytest.mark.asyncio
    async def test_chicken_high_protein_content(
        self,
        nutrition_e2e_client: AsyncClient,
    ) -> None:
        """Should return high protein content for chicken breast."""
        response = await nutrition_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/chicken/nutritional-info"
        )

        assert response.status_code == 200

        data = response.json()
        macros = data["macroNutrients"]

        # Chicken breast is high protein, low carb
        assert macros["protein"]["amount"] >= 30, "Chicken should be high protein"
        assert macros["carbs"]["amount"] <= 1, "Chicken should have minimal carbs"

    @pytest.mark.asyncio
    async def test_rice_carbohydrate_content(
        self,
        nutrition_e2e_client: AsyncClient,
    ) -> None:
        """Should return appropriate carbohydrate content for cooked rice."""
        response = await nutrition_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/rice/nutritional-info"
        )

        assert response.status_code == 200

        data = response.json()
        macros = data["macroNutrients"]

        # Cooked rice is primarily carbohydrates
        assert macros["carbs"]["amount"] >= 25, "Rice should be carb-heavy"
        assert macros["protein"]["amount"] <= 5, "Rice has moderate protein"

    @pytest.mark.asyncio
    async def test_rice_with_cup_measurement(
        self,
        nutrition_e2e_client: AsyncClient,
    ) -> None:
        """Should correctly scale rice for 1 cup (158g cooked)."""
        response = await nutrition_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/rice/nutritional-info",
            params={"amount": 1, "measurement": "CUP"},
        )

        assert response.status_code == 200

        data = response.json()

        # 1 cup cooked rice = 158g
        assert data["quantity"]["amount"] == 1
        assert data["quantity"]["measurement"] == "CUP"

        # 1 cup rice ~= 205 kcal (130 * 158 / 100)
        calories = data["macroNutrients"]["calories"]["amount"]
        assert 180 <= calories <= 230, f"Expected ~205 kcal, got {calories}"


class TestNutritionCachingE2E:
    """E2E tests for nutrition caching behavior."""

    @pytest.mark.asyncio
    async def test_second_request_uses_cache(
        self,
        nutrition_e2e_client: AsyncClient,
        nutrition_cache_client: Redis[bytes],
    ) -> None:
        """Should cache nutrition data after first request."""
        # First request - should hit database
        response1 = await nutrition_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/nutritional-info"
        )
        assert response1.status_code == 200

        # Verify cache was populated
        cache_key = "nutrition:flour"
        cached_data = await nutrition_cache_client.get(cache_key)
        assert cached_data is not None, "Data should be cached after first request"

        # Second request - should use cache
        response2 = await nutrition_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/nutritional-info"
        )
        assert response2.status_code == 200

        # Both responses should return same data
        assert (
            response1.json()["macroNutrients"]["calories"]["amount"]
            == response2.json()["macroNutrients"]["calories"]["amount"]
        )


class TestNutritionErrorHandlingE2E:
    """E2E tests for error handling."""

    @pytest.mark.asyncio
    async def test_returns_404_for_nonexistent_ingredient(
        self,
        nutrition_e2e_client: AsyncClient,
    ) -> None:
        """Should return 404 for ingredient not in database."""
        response = await nutrition_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/unicorn-meat/nutritional-info"
        )

        assert response.status_code == 404

        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "INGREDIENT_NOT_FOUND" in data["message"]

    @pytest.mark.asyncio
    async def test_returns_400_for_partial_quantity_params(
        self,
        nutrition_e2e_client: AsyncClient,
    ) -> None:
        """Should return 400 when only amount or measurement provided."""
        # Only amount
        response1 = await nutrition_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/nutritional-info",
            params={"amount": 100},
        )
        assert response1.status_code == 400

        # Only measurement
        response2 = await nutrition_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/nutritional-info",
            params={"measurement": "G"},
        )
        assert response2.status_code == 400
