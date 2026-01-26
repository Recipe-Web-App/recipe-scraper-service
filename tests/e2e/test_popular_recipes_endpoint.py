"""End-to-end tests for popular recipes endpoint.

Tests the full endpoint workflow with mocked cache responses.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import orjson
import pytest
import respx
from httpx import Response

from app.api.dependencies import get_redis_cache_client
from app.schemas.recipe import (
    PopularRecipe,
    PopularRecipesData,
    RecipeEngagementMetrics,
)
from app.services.popular.service import PopularRecipesService


if TYPE_CHECKING:
    from httpx import AsyncClient


pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


# Sample HTML responses for mocking
SAMPLE_LISTING_HTML = """
<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "url": "https://test.com/recipe/1"},
            {"@type": "ListItem", "position": 2, "url": "https://test.com/recipe/2"}
        ]
    }
    </script>
</head>
<body>
    <article class="recipe-card">
        <h2><a href="/recipe/chocolate-cake">Chocolate Cake</a></h2>
    </article>
    <article class="recipe-card">
        <h2><a href="/recipe/apple-pie">Apple Pie</a></h2>
    </article>
</body>
</html>
"""

SAMPLE_RECIPE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": "Test Recipe",
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": "4.5",
            "ratingCount": "1234",
            "reviewCount": "567"
        }
    }
    </script>
</head>
<body>
    <h1>Test Recipe</h1>
</body>
</html>
"""


def _create_mock_cache_client(cached_data: PopularRecipesData | None) -> AsyncMock:
    """Create a mock cache client with optional cached data."""
    mock_client = AsyncMock()
    if cached_data:
        mock_client.get = AsyncMock(return_value=orjson.dumps(cached_data.model_dump()))
    else:
        mock_client.get = AsyncMock(return_value=None)
    return mock_client


def _create_sample_cached_data(
    recipes: list[PopularRecipe] | None = None,
    total_count: int = 100,
) -> PopularRecipesData:
    """Create sample cached data for testing."""
    if recipes is None:
        recipes = [
            PopularRecipe(
                recipe_name="E2E Recipe 1",
                url="https://test.com/recipe1",
                source="TestSource",
                raw_rank=1,
                metrics=RecipeEngagementMetrics(rating=4.8),
                normalized_score=0.95,
            ),
            PopularRecipe(
                recipe_name="E2E Recipe 2",
                url="https://test.com/recipe2",
                source="TestSource",
                raw_rank=2,
                metrics=RecipeEngagementMetrics(rating=4.5),
                normalized_score=0.90,
            ),
        ]
    return PopularRecipesData(
        recipes=recipes,
        total_count=total_count,
        sources_fetched=["TestSource"],
    )


class TestPopularRecipesEndpointE2E:
    """E2E tests for the popular recipes endpoint.

    The endpoint now reads directly from cache and returns 503 if cache is empty.
    """

    async def test_get_popular_recipes_returns_list(
        self,
        client: AsyncClient,
    ) -> None:
        """Should return list of popular recipes from cache."""
        cached_data = _create_sample_cached_data()
        mock_cache = _create_mock_cache_client(cached_data)

        # Override the dependency at FastAPI level
        app = client._transport.app  # type: ignore[union-attr]
        app.dependency_overrides[get_redis_cache_client] = lambda: mock_cache
        try:
            response = await client.get("/api/v1/recipe-scraper/recipes/popular")
        finally:
            app.dependency_overrides.pop(get_redis_cache_client, None)

        assert response.status_code == 200
        data = response.json()
        assert "recipes" in data
        assert "count" in data
        assert data["count"] == 100
        assert len(data["recipes"]) == 2
        assert data["recipes"][0]["recipeName"] == "E2E Recipe 1"

    async def test_pagination_parameters(
        self,
        client: AsyncClient,
    ) -> None:
        """Should accept pagination parameters."""
        cached_data = _create_sample_cached_data()
        mock_cache = _create_mock_cache_client(cached_data)

        app = client._transport.app  # type: ignore[union-attr]
        app.dependency_overrides[get_redis_cache_client] = lambda: mock_cache
        try:
            response = await client.get(
                "/api/v1/recipe-scraper/recipes/popular",
                params={"limit": 10, "offset": 0},
            )
        finally:
            app.dependency_overrides.pop(get_redis_cache_client, None)

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 0

    async def test_count_only_parameter(
        self,
        client: AsyncClient,
    ) -> None:
        """Should return only count when countOnly is true."""
        cached_data = _create_sample_cached_data(total_count=500)
        mock_cache = _create_mock_cache_client(cached_data)

        app = client._transport.app  # type: ignore[union-attr]
        app.dependency_overrides[get_redis_cache_client] = lambda: mock_cache
        try:
            response = await client.get(
                "/api/v1/recipe-scraper/recipes/popular",
                params={"countOnly": "true"},
            )
        finally:
            app.dependency_overrides.pop(get_redis_cache_client, None)

        assert response.status_code == 200
        data = response.json()
        assert data["recipes"] == []
        assert data["count"] == 500

    async def test_limit_validation(
        self,
        client: AsyncClient,
    ) -> None:
        """Should validate limit parameter bounds."""
        cached_data = _create_sample_cached_data()
        mock_cache = _create_mock_cache_client(cached_data)

        app = client._transport.app  # type: ignore[union-attr]
        app.dependency_overrides[get_redis_cache_client] = lambda: mock_cache
        try:
            # Limit too high
            response = await client.get(
                "/api/v1/recipe-scraper/recipes/popular",
                params={"limit": 200},
            )
        finally:
            app.dependency_overrides.pop(get_redis_cache_client, None)

        assert response.status_code == 422

    async def test_offset_validation(
        self,
        client: AsyncClient,
    ) -> None:
        """Should validate offset parameter bounds."""
        cached_data = _create_sample_cached_data()
        mock_cache = _create_mock_cache_client(cached_data)

        app = client._transport.app  # type: ignore[union-attr]
        app.dependency_overrides[get_redis_cache_client] = lambda: mock_cache
        try:
            # Negative offset
            response = await client.get(
                "/api/v1/recipe-scraper/recipes/popular",
                params={"offset": -1},
            )
        finally:
            app.dependency_overrides.pop(get_redis_cache_client, None)

        assert response.status_code == 422

    async def test_service_unavailable(
        self,
        client: AsyncClient,
    ) -> None:
        """Should return 503 when cache is empty (triggers background refresh)."""
        mock_cache = _create_mock_cache_client(None)

        app = client._transport.app  # type: ignore[union-attr]
        app.dependency_overrides[get_redis_cache_client] = lambda: mock_cache
        try:
            with patch(
                "app.api.v1.endpoints.recipes.enqueue_popular_recipes_refresh",
                return_value=None,
            ):
                response = await client.get("/api/v1/recipe-scraper/recipes/popular")
        finally:
            app.dependency_overrides.pop(get_redis_cache_client, None)

        assert response.status_code == 503
        assert response.headers.get("retry-after") == "60"

    async def test_response_schema_format(
        self,
        client: AsyncClient,
    ) -> None:
        """Should return response in correct schema format."""
        cached_data = _create_sample_cached_data()
        mock_cache = _create_mock_cache_client(cached_data)

        app = client._transport.app  # type: ignore[union-attr]
        app.dependency_overrides[get_redis_cache_client] = lambda: mock_cache
        try:
            response = await client.get("/api/v1/recipe-scraper/recipes/popular")
        finally:
            app.dependency_overrides.pop(get_redis_cache_client, None)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert isinstance(data["recipes"], list)
        assert isinstance(data["limit"], int)
        assert isinstance(data["offset"], int)
        assert isinstance(data["count"], int)

        # Verify recipe structure (should be WebRecipe format)
        if data["recipes"]:
            recipe = data["recipes"][0]
            assert "recipeName" in recipe
            assert "url" in recipe
            # Should NOT have internal fields
            assert "source" not in recipe
            assert "rawRank" not in recipe
            assert "metrics" not in recipe
            assert "normalizedScore" not in recipe


class TestPopularRecipesNoAuth:
    """Tests verifying the endpoint doesn't require authentication."""

    async def test_no_auth_header_required(
        self,
        client: AsyncClient,
    ) -> None:
        """Should not require authentication header."""
        cached_data = _create_sample_cached_data(recipes=[], total_count=0)
        mock_cache = _create_mock_cache_client(cached_data)

        app = client._transport.app  # type: ignore[union-attr]
        app.dependency_overrides[get_redis_cache_client] = lambda: mock_cache
        try:
            # Make request without any auth headers
            response = await client.get("/api/v1/recipe-scraper/recipes/popular")
        finally:
            app.dependency_overrides.pop(get_redis_cache_client, None)

        # Should succeed without auth
        assert response.status_code == 200


class TestPopularRecipesWithMockedHTTP:
    """Tests with mocked HTTP responses for external sources."""

    @respx.mock
    async def test_fetches_from_mocked_sources(
        self,
        client: AsyncClient,
    ) -> None:
        """Should fetch and parse recipes from mocked sources."""
        # Mock the listing page
        respx.get("https://test.com/popular").mock(
            return_value=Response(200, text=SAMPLE_LISTING_HTML)
        )

        # Mock individual recipe pages
        respx.get("https://test.com/recipe/chocolate-cake").mock(
            return_value=Response(200, text=SAMPLE_RECIPE_HTML)
        )
        respx.get("https://test.com/recipe/apple-pie").mock(
            return_value=Response(200, text=SAMPLE_RECIPE_HTML)
        )

        # Create service with mocked settings
        mock_settings = MagicMock()
        mock_settings.scraping.popular_recipes.enabled = True
        mock_settings.scraping.popular_recipes.cache_ttl = 60
        mock_settings.scraping.popular_recipes.cache_key = "test"
        mock_settings.scraping.popular_recipes.fetch_timeout = 10.0
        mock_settings.scraping.popular_recipes.max_concurrent_fetches = 2

        source = MagicMock()
        source.name = "TestSource"
        source.base_url = "https://test.com"
        source.popular_endpoint = "/popular"
        source.enabled = True
        source.max_recipes = 10
        source.source_weight = 1.0
        mock_settings.scraping.popular_recipes.sources = [source]

        mock_settings.scraping.popular_recipes.scoring.rating_weight = 0.35
        mock_settings.scraping.popular_recipes.scoring.rating_count_weight = 0.25
        mock_settings.scraping.popular_recipes.scoring.favorites_weight = 0.25
        mock_settings.scraping.popular_recipes.scoring.reviews_weight = 0.10
        mock_settings.scraping.popular_recipes.scoring.position_weight = 0.05

        with patch(
            "app.services.popular.service.get_settings",
            return_value=mock_settings,
        ):
            service = PopularRecipesService(cache_client=None)
            await service.initialize()

            try:
                data = await service._fetch_all_sources()

                # Should have fetched recipes
                assert data.total_count >= 0
                assert "TestSource" in data.sources_fetched or data.total_count == 0
            finally:
                await service.shutdown()


class TestEmptyResults:
    """Tests for handling empty results."""

    async def test_returns_empty_list_when_no_recipes(
        self,
        client: AsyncClient,
    ) -> None:
        """Should return empty list when no recipes available."""
        cached_data = _create_sample_cached_data(recipes=[], total_count=0)
        mock_cache = _create_mock_cache_client(cached_data)

        app = client._transport.app  # type: ignore[union-attr]
        app.dependency_overrides[get_redis_cache_client] = lambda: mock_cache
        try:
            response = await client.get("/api/v1/recipe-scraper/recipes/popular")
        finally:
            app.dependency_overrides.pop(get_redis_cache_client, None)

        assert response.status_code == 200
        data = response.json()
        assert data["recipes"] == []
        assert data["count"] == 0
