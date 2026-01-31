"""End-to-end tests for allergen endpoints.

Tests verify that common ingredients (flour, butter, eggs, chicken)
return valid allergen data from the full stack including:
- API routing and authentication
- AllergenService with caching
- AllergenRepository (PostgreSQL)

These tests use real testcontainers for PostgreSQL and Redis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from app.api.dependencies import get_allergen_service
from app.auth.dependencies import CurrentUser, get_current_user
from app.database.repositories.allergen import AllergenRepository
from app.schemas.enums import Allergen
from app.services.allergen.constants import ALLERGEN_CACHE_KEY_PREFIX
from app.services.allergen.service import AllergenService


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
async def allergen_cache_client(redis_url: str) -> AsyncGenerator[Redis[bytes]]:
    """Create a Redis client for allergen caching."""
    client: Redis[bytes] = Redis.from_url(redis_url, decode_responses=False)
    await client.flushdb()
    try:
        yield client
    finally:
        await client.aclose()  # type: ignore[attr-defined]


@pytest.fixture
async def allergen_repository(nutrition_db_pool: Pool) -> AllergenRepository:
    """Create AllergenRepository with test database pool.

    Uses nutrition_db_pool which includes allergen schema and seed data.
    """
    return AllergenRepository(pool=nutrition_db_pool)


@pytest.fixture
async def allergen_service(
    allergen_cache_client: Redis[bytes],
    allergen_repository: AllergenRepository,
) -> AsyncGenerator[AllergenService]:
    """Create AllergenService with real Redis and PostgreSQL."""
    svc = AllergenService(
        cache_client=allergen_cache_client,
        repository=allergen_repository,
        off_client=None,  # Disable Open Food Facts for E2E tests
    )
    await svc.initialize()
    yield svc
    await svc.shutdown()


@pytest.fixture
async def allergen_e2e_client(
    app: FastAPI,
    allergen_service: AllergenService,
) -> AsyncGenerator[AsyncClient]:
    """Create client with real allergen service for E2E tests."""

    async def mock_get_current_user() -> CurrentUser:
        return MOCK_USER

    async def mock_get_allergen() -> AllergenService:
        return allergen_service

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_allergen_service] = mock_get_allergen

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_allergen_service, None)


class TestCommonIngredientsAllergenE2E:
    """E2E tests verifying common ingredients return valid allergen data."""

    async def test_flour_returns_gluten_and_wheat_allergens(
        self,
        allergen_e2e_client: AsyncClient,
    ) -> None:
        """Should return GLUTEN and WHEAT allergens for flour."""
        response = await allergen_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/allergens"
        )

        assert response.status_code == 200

        data = response.json()
        assert data["ingredientName"] == "flour"
        assert data["dataSource"] == "USDA"

        allergen_types = [a["allergen"] for a in data["allergens"]]
        assert "GLUTEN" in allergen_types
        assert "WHEAT" in allergen_types

    async def test_butter_returns_milk_allergen(
        self,
        allergen_e2e_client: AsyncClient,
    ) -> None:
        """Should return MILK allergen for butter."""
        response = await allergen_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/allergens"
        )

        assert response.status_code == 200

        data = response.json()
        assert data["ingredientName"] == "butter"

        allergen_types = [a["allergen"] for a in data["allergens"]]
        assert "MILK" in allergen_types

    async def test_eggs_returns_eggs_allergen(
        self,
        allergen_e2e_client: AsyncClient,
    ) -> None:
        """Should return EGGS allergen for eggs."""
        response = await allergen_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/eggs/allergens"
        )

        assert response.status_code == 200

        data = response.json()
        assert data["ingredientName"] == "eggs"

        allergen_types = [a["allergen"] for a in data["allergens"]]
        assert "EGGS" in allergen_types

    async def test_chicken_allergen_response(
        self,
        allergen_e2e_client: AsyncClient,
    ) -> None:
        """Should handle chicken appropriately based on data source.

        Chicken may return:
        - 404 if no allergen data found in DB or OFF
        - 200 with allergens if OFF returns data
        - 200 with empty allergens if profile exists but no allergens
        """
        response = await allergen_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/chicken/allergens"
        )

        # Chicken typically has no common allergens, but OFF may return data
        if response.status_code == 200:
            data = response.json()
            # Verify valid response structure
            assert "ingredientName" in data
            assert "allergens" in data
            assert isinstance(data["allergens"], list)
        else:
            # 404 is also valid if no allergen data found
            assert response.status_code == 404

    async def test_unknown_ingredient_returns_404(
        self,
        allergen_e2e_client: AsyncClient,
    ) -> None:
        """Should return 404 for ingredient not in database."""
        response = await allergen_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/unicorn-meat/allergens"
        )

        assert response.status_code == 404

        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "INGREDIENT_NOT_FOUND" in data["message"]


class TestAllergenCachingE2E:
    """E2E tests for allergen caching behavior."""

    async def test_second_request_uses_cache(
        self,
        allergen_e2e_client: AsyncClient,
        allergen_cache_client: Redis[bytes],
    ) -> None:
        """Should cache allergen data after first request."""
        # First request - should hit database
        response1 = await allergen_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/allergens"
        )
        assert response1.status_code == 200

        # Verify cache was populated
        cache_key = f"{ALLERGEN_CACHE_KEY_PREFIX}:flour"
        cached_data = await allergen_cache_client.get(cache_key)
        assert cached_data is not None, "Data should be cached after first request"

        # Second request - should use cache
        response2 = await allergen_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/allergens"
        )
        assert response2.status_code == 200

        # Both responses should return same data
        assert response1.json()["allergens"] == response2.json()["allergens"]

    async def test_case_insensitive_cache_lookup(
        self,
        allergen_e2e_client: AsyncClient,
        allergen_cache_client: Redis[bytes],
    ) -> None:
        """Should use cache regardless of case."""
        # First request with lowercase
        response1 = await allergen_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/allergens"
        )
        assert response1.status_code == 200

        # Verify cache key is normalized (lowercase)
        cache_key = f"{ALLERGEN_CACHE_KEY_PREFIX}:flour"
        assert await allergen_cache_client.exists(cache_key) == 1

        # Second request with uppercase - should hit same cache
        response2 = await allergen_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/FLOUR/allergens"
        )
        assert response2.status_code == 200

        # Should return same allergen data
        assert response1.json()["allergens"] == response2.json()["allergens"]


class TestAllergenDataQualityE2E:
    """E2E tests for allergen data quality."""

    async def test_allergen_presence_type_is_valid(
        self,
        allergen_e2e_client: AsyncClient,
    ) -> None:
        """Should return valid presence types for all allergens."""
        response = await allergen_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/allergens"
        )

        assert response.status_code == 200

        data = response.json()
        valid_presence_types = {"CONTAINS", "MAY_CONTAIN", "TRACES"}

        for allergen_info in data["allergens"]:
            assert allergen_info["presenceType"] in valid_presence_types, (
                f"Invalid presence type: {allergen_info['presenceType']}"
            )

    async def test_confidence_scores_are_valid(
        self,
        allergen_e2e_client: AsyncClient,
    ) -> None:
        """Should return valid confidence scores (0.0 to 1.0)."""
        response = await allergen_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/allergens"
        )

        assert response.status_code == 200

        data = response.json()
        for allergen_info in data["allergens"]:
            if allergen_info.get("confidenceScore") is not None:
                score = allergen_info["confidenceScore"]
                assert 0.0 <= score <= 1.0, f"Invalid confidence score: {score}"

    @pytest.mark.parametrize(
        ("ingredient", "expected_allergens"),
        [
            ("flour", [Allergen.GLUTEN, Allergen.WHEAT]),
            ("butter", [Allergen.MILK]),
            ("eggs", [Allergen.EGGS]),
        ],
    )
    async def test_expected_allergens_present(
        self,
        allergen_e2e_client: AsyncClient,
        ingredient: str,
        expected_allergens: list[Allergen],
    ) -> None:
        """Should return expected allergens for common ingredients."""
        response = await allergen_e2e_client.get(
            f"/api/v1/recipe-scraper/ingredients/{ingredient}/allergens"
        )

        assert response.status_code == 200

        data = response.json()
        actual_allergens = {a["allergen"] for a in data["allergens"]}

        for expected in expected_allergens:
            assert expected.value in actual_allergens, (
                f"Missing expected allergen {expected.value} for {ingredient}"
            )


class TestAllergenFuzzyMatchingE2E:
    """E2E tests for fuzzy matching behavior.

    Note: These tests depend on pg_trgm extension being available.
    """

    async def test_exact_match_takes_priority(
        self,
        allergen_e2e_client: AsyncClient,
    ) -> None:
        """Exact match should be prioritized over fuzzy matches."""
        response = await allergen_e2e_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/allergens"
        )

        assert response.status_code == 200

        data = response.json()
        assert data["ingredientName"] == "flour"
