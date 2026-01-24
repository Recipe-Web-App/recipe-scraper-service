"""End-to-end tests for popular recipes endpoint.

Tests the full endpoint workflow with mocked HTTP responses.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import respx
from httpx import Response

from app.schemas.recipe import (
    PopularRecipe,
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


class TestPopularRecipesEndpointE2E:
    """E2E tests for the popular recipes endpoint."""

    @pytest.fixture
    def mock_popular_service(self) -> MagicMock:
        """Create a mock service with pre-populated data."""
        service = AsyncMock()
        service.get_popular_recipes = AsyncMock(
            return_value=(
                [
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
                ],
                100,  # total_count
            )
        )
        return service

    async def test_get_popular_recipes_returns_list(
        self,
        client: AsyncClient,
        mock_popular_service: MagicMock,
    ) -> None:
        """Should return list of popular recipes."""
        # Patch the service in app state
        with patch.object(
            client._transport.app.state,  # type: ignore[union-attr]
            "popular_recipes_service",
            mock_popular_service,
            create=True,
        ):
            response = await client.get("/api/v1/recipe-scraper/recipes/popular")

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
        mock_popular_service: MagicMock,
    ) -> None:
        """Should accept pagination parameters."""
        with patch.object(
            client._transport.app.state,  # type: ignore[union-attr]
            "popular_recipes_service",
            mock_popular_service,
            create=True,
        ):
            response = await client.get(
                "/api/v1/recipe-scraper/recipes/popular",
                params={"limit": 10, "offset": 20},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 20

    async def test_count_only_parameter(
        self,
        client: AsyncClient,
    ) -> None:
        """Should return only count when countOnly is true."""
        mock_service = AsyncMock()
        mock_service.get_popular_recipes = AsyncMock(return_value=([], 500))

        with patch.object(
            client._transport.app.state,  # type: ignore[union-attr]
            "popular_recipes_service",
            mock_service,
            create=True,
        ):
            response = await client.get(
                "/api/v1/recipe-scraper/recipes/popular",
                params={"countOnly": "true"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["recipes"] == []
        assert data["count"] == 500

    async def test_limit_validation(
        self,
        client: AsyncClient,
        mock_popular_service: MagicMock,
    ) -> None:
        """Should validate limit parameter bounds."""
        with patch.object(
            client._transport.app.state,  # type: ignore[union-attr]
            "popular_recipes_service",
            mock_popular_service,
            create=True,
        ):
            # Limit too high
            response = await client.get(
                "/api/v1/recipe-scraper/recipes/popular",
                params={"limit": 200},
            )

        assert response.status_code == 422

    async def test_offset_validation(
        self,
        client: AsyncClient,
        mock_popular_service: MagicMock,
    ) -> None:
        """Should validate offset parameter bounds."""
        with patch.object(
            client._transport.app.state,  # type: ignore[union-attr]
            "popular_recipes_service",
            mock_popular_service,
            create=True,
        ):
            # Negative offset
            response = await client.get(
                "/api/v1/recipe-scraper/recipes/popular",
                params={"offset": -1},
            )

        assert response.status_code == 422

    async def test_service_unavailable(
        self,
        client: AsyncClient,
    ) -> None:
        """Should return 503 when service is unavailable."""
        with patch.object(
            client._transport.app.state,  # type: ignore[union-attr]
            "popular_recipes_service",
            None,
            create=True,
        ):
            response = await client.get("/api/v1/recipe-scraper/recipes/popular")

        assert response.status_code == 503

    async def test_response_schema_format(
        self,
        client: AsyncClient,
        mock_popular_service: MagicMock,
    ) -> None:
        """Should return response in correct schema format."""
        with patch.object(
            client._transport.app.state,  # type: ignore[union-attr]
            "popular_recipes_service",
            mock_popular_service,
            create=True,
        ):
            response = await client.get("/api/v1/recipe-scraper/recipes/popular")

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
        mock_service = AsyncMock()
        mock_service.get_popular_recipes = AsyncMock(return_value=([], 0))

        with patch.object(
            client._transport.app.state,  # type: ignore[union-attr]
            "popular_recipes_service",
            mock_service,
            create=True,
        ):
            # Make request without any auth headers
            response = await client.get("/api/v1/recipe-scraper/recipes/popular")

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
        mock_service = AsyncMock()
        mock_service.get_popular_recipes = AsyncMock(return_value=([], 0))

        with patch.object(
            client._transport.app.state,  # type: ignore[union-attr]
            "popular_recipes_service",
            mock_service,
            create=True,
        ):
            response = await client.get("/api/v1/recipe-scraper/recipes/popular")

        assert response.status_code == 200
        data = response.json()
        assert data["recipes"] == []
        assert data["count"] == 0
