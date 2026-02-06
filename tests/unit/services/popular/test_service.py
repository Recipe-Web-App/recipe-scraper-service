"""Unit tests for PopularRecipesService."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.schemas.recipe import (
    PopularRecipe,
    PopularRecipesData,
)
from app.services.popular.exceptions import (
    PopularRecipesFetchError,
)
from app.services.popular.service import PopularRecipesService


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings."""
    mock = MagicMock()
    mock.scraping.popular_recipes.enabled = True
    mock.scraping.popular_recipes.cache_ttl = 86400
    mock.scraping.popular_recipes.cache_key = "popular_recipes"
    mock.scraping.popular_recipes.target_total = 500
    mock.scraping.popular_recipes.fetch_timeout = 30.0
    mock.scraping.popular_recipes.max_concurrent_fetches = 5

    # Source config
    source = MagicMock()
    source.name = "TestSource"
    source.base_url = "https://test.com"
    source.popular_endpoint = "/popular"
    source.enabled = True
    source.max_recipes = 10
    source.source_weight = 1.0
    mock.scraping.popular_recipes.sources = [source]

    # Scoring weights
    mock.scraping.popular_recipes.scoring.rating_weight = 0.35
    mock.scraping.popular_recipes.scoring.rating_count_weight = 0.25
    mock.scraping.popular_recipes.scoring.favorites_weight = 0.25
    mock.scraping.popular_recipes.scoring.reviews_weight = 0.10
    mock.scraping.popular_recipes.scoring.position_weight = 0.05

    return mock


@pytest.fixture
def service(mock_settings: MagicMock) -> PopularRecipesService:
    """Create a PopularRecipesService instance."""
    with patch("app.services.popular.service.get_settings", return_value=mock_settings):
        return PopularRecipesService(cache_client=None)


class TestServiceInitialization:
    """Tests for service initialization and shutdown."""

    @pytest.mark.asyncio
    async def test_initialize_creates_http_client(
        self, service: PopularRecipesService
    ) -> None:
        """Should create HTTP client on initialization."""
        await service.initialize()

        assert service._http_client is not None

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_closes_http_client(
        self, service: PopularRecipesService
    ) -> None:
        """Should close HTTP client on shutdown."""
        await service.initialize()
        assert service._http_client is not None

        await service.shutdown()
        assert service._http_client is None


class TestGetPopularRecipes:
    """Tests for get_popular_recipes method."""

    @pytest.mark.asyncio
    async def test_returns_recipes_with_pagination(
        self, service: PopularRecipesService
    ) -> None:
        """Should return paginated recipes."""
        # Create mock cached data
        cached_data = PopularRecipesData(
            recipes=[
                PopularRecipe(
                    recipe_name=f"Recipe {i}",
                    url=f"https://test.com/recipe/{i}",
                    source="TestSource",
                    raw_rank=i + 1,  # raw_rank must be >= 1
                    normalized_score=1.0 - i * 0.1,
                )
                for i in range(10)
            ],
            total_count=10,
            sources_fetched=["TestSource"],
        )

        # Mock _get_or_refresh_cache to return cached data
        service._get_or_refresh_cache = AsyncMock(return_value=cached_data)

        recipes, total = await service.get_popular_recipes(limit=5, offset=0)

        assert len(recipes) == 5
        assert total == 10
        assert recipes[0].recipe_name == "Recipe 0"

    @pytest.mark.asyncio
    async def test_returns_count_only(self, service: PopularRecipesService) -> None:
        """Should return only count when count_only is True."""
        cached_data = PopularRecipesData(
            recipes=[
                PopularRecipe(
                    recipe_name="Recipe",
                    url="https://test.com/recipe",
                    source="TestSource",
                    raw_rank=1,
                )
            ],
            total_count=100,
        )

        service._get_or_refresh_cache = AsyncMock(return_value=cached_data)

        recipes, total = await service.get_popular_recipes(count_only=True)

        assert recipes == []
        assert total == 100

    @pytest.mark.asyncio
    async def test_handles_offset_pagination(
        self, service: PopularRecipesService
    ) -> None:
        """Should handle offset correctly."""
        cached_data = PopularRecipesData(
            recipes=[
                PopularRecipe(
                    recipe_name=f"Recipe {i}",
                    url=f"https://test.com/recipe/{i}",
                    source="TestSource",
                    raw_rank=i + 1,  # raw_rank must be >= 1
                )
                for i in range(10)
            ],
            total_count=10,
        )

        service._get_or_refresh_cache = AsyncMock(return_value=cached_data)

        recipes, total = await service.get_popular_recipes(limit=5, offset=5)

        assert len(recipes) == 5
        assert total == 10
        assert recipes[0].recipe_name == "Recipe 5"


class TestCaching:
    """Tests for cache operations."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_data(
        self, service: PopularRecipesService, mock_settings: MagicMock
    ) -> None:
        """Should return cached data on cache hit."""
        mock_cache = AsyncMock()
        cached_data = PopularRecipesData(
            recipes=[
                PopularRecipe(
                    recipe_name="Cached Recipe",
                    url="https://test.com/cached",
                    source="TestSource",
                    raw_rank=1,
                )
            ],
            total_count=1,
        )
        mock_cache.get = AsyncMock(return_value=cached_data.model_dump_json().encode())

        with patch(
            "app.services.popular.service.get_settings", return_value=mock_settings
        ):
            service = PopularRecipesService(cache_client=mock_cache)

        data = await service._get_or_refresh_cache()

        assert data.total_count == 1
        assert data.recipes[0].recipe_name == "Cached Recipe"
        mock_cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_miss_fetches_fresh_data(
        self, service: PopularRecipesService
    ) -> None:
        """Should fetch fresh data on cache miss."""
        # Mock _get_from_cache to return None
        service._get_from_cache = AsyncMock(return_value=None)
        service._fetch_all_sources = AsyncMock(
            return_value=PopularRecipesData(
                recipes=[
                    PopularRecipe(
                        recipe_name="Fresh Recipe",
                        url="https://test.com/fresh",
                        source="TestSource",
                        raw_rank=1,
                    )
                ],
                total_count=1,
            )
        )
        service._save_to_cache = AsyncMock()

        data = await service._get_or_refresh_cache()

        assert data.total_count == 1
        assert data.recipes[0].recipe_name == "Fresh Recipe"
        service._fetch_all_sources.assert_called_once()
        service._save_to_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_cache_deletes_key(self, mock_settings: MagicMock) -> None:
        """Should delete cache key on invalidation."""
        mock_cache = AsyncMock()
        mock_cache.delete = AsyncMock()

        with patch(
            "app.services.popular.service.get_settings", return_value=mock_settings
        ):
            service = PopularRecipesService(cache_client=mock_cache)

        await service.invalidate_cache()

        mock_cache.delete.assert_called_once_with("popular:popular_recipes")


class TestFetchAllSources:
    """Tests for _fetch_all_sources method."""

    @pytest.mark.asyncio
    async def test_fetches_from_enabled_sources(
        self, service: PopularRecipesService
    ) -> None:
        """Should fetch from all enabled sources."""
        mock_recipes = [
            PopularRecipe(
                recipe_name="Recipe",
                url="https://test.com/recipe",
                source="TestSource",
                raw_rank=1,
            )
        ]
        service._fetch_source = AsyncMock(return_value=mock_recipes)
        service._normalize_and_score = MagicMock(return_value=mock_recipes)

        data = await service._fetch_all_sources()

        assert data.total_count == 1
        assert "TestSource" in data.sources_fetched
        assert data.fetch_errors == {}

    @pytest.mark.asyncio
    async def test_handles_source_fetch_error(
        self, service: PopularRecipesService
    ) -> None:
        """Should continue when a source fails to fetch."""
        service._fetch_source = AsyncMock(
            side_effect=PopularRecipesFetchError("Test error", source="TestSource")
        )

        data = await service._fetch_all_sources()

        assert data.total_count == 0
        assert "TestSource" in data.fetch_errors

    @pytest.mark.asyncio
    async def test_handles_partial_success(
        self, service: PopularRecipesService, mock_settings: MagicMock
    ) -> None:
        """Should return partial results when some sources fail."""
        # Add another source
        source2 = MagicMock()
        source2.name = "FailingSource"
        source2.base_url = "https://fail.com"
        source2.popular_endpoint = "/popular"
        source2.enabled = True
        source2.max_recipes = 10
        source2.source_weight = 0.9
        mock_settings.scraping.popular_recipes.sources.append(source2)

        mock_recipe = PopularRecipe(
            recipe_name="Recipe",
            url="https://test.com/recipe",
            source="TestSource",
            raw_rank=1,
        )

        async def mock_fetch(source: MagicMock) -> list[PopularRecipe]:
            if source.name == "FailingSource":
                msg = "Failed"
                raise PopularRecipesFetchError(msg, source="FailingSource")
            return [mock_recipe]

        service._fetch_source = AsyncMock(side_effect=mock_fetch)
        service._normalize_and_score = MagicMock(return_value=[mock_recipe])

        data = await service._fetch_all_sources()

        assert data.total_count == 1
        assert "TestSource" in data.sources_fetched
        assert "FailingSource" in data.fetch_errors
        assert data.partial_success is True

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_sources(
        self, service: PopularRecipesService
    ) -> None:
        """Should return empty data when no sources enabled."""
        service._config.sources = []

        data = await service._fetch_all_sources()

        assert data.total_count == 0
        assert data.recipes == []


class TestFetchSource:
    """Tests for _fetch_source method."""

    @pytest.mark.asyncio
    async def test_raises_when_http_client_not_initialized(
        self, service: PopularRecipesService
    ) -> None:
        """Should raise when HTTP client not initialized."""
        source = MagicMock()
        source.name = "TestSource"

        with pytest.raises(
            PopularRecipesFetchError, match="HTTP client not initialized"
        ):
            await service._fetch_source(source)

    @pytest.mark.asyncio
    async def test_raises_on_http_error(self, service: PopularRecipesService) -> None:
        """Should raise PopularRecipesFetchError on HTTP error."""
        await service.initialize()

        source = MagicMock()
        source.name = "TestSource"
        source.base_url = "https://test.com"
        source.popular_endpoint = "/popular"

        # Mock HTTP response with error
        mock_response = MagicMock()
        mock_response.status_code = 404
        service._http_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=mock_response,
            )
        )

        with pytest.raises(PopularRecipesFetchError):
            await service._fetch_source(source)

        await service.shutdown()


class TestRefreshCache:
    """Tests for refresh_cache method."""

    @pytest.mark.asyncio
    async def test_refresh_fetches_and_caches(
        self, service: PopularRecipesService
    ) -> None:
        """Should fetch fresh data and save to cache."""
        fresh_data = PopularRecipesData(
            recipes=[
                PopularRecipe(
                    recipe_name="Fresh Recipe",
                    url="https://test.com/fresh",
                    source="TestSource",
                    raw_rank=1,
                )
            ],
            total_count=1,
        )

        service._fetch_all_sources = AsyncMock(return_value=fresh_data)
        service._save_to_cache = AsyncMock()

        result = await service.refresh_cache()

        assert result.total_count == 1
        service._fetch_all_sources.assert_called_once()
        service._save_to_cache.assert_called_once()


class TestCacheOperations:
    """Tests for cache helper methods."""

    @pytest.mark.asyncio
    async def test_get_from_cache_returns_none_when_no_client(
        self, service: PopularRecipesService
    ) -> None:
        """Should return None when cache client is None."""
        service._cache_client = None

        result = await service._get_from_cache()

        assert result is None

    @pytest.mark.asyncio
    async def test_get_from_cache_handles_exception(
        self, mock_settings: MagicMock
    ) -> None:
        """Should handle cache read exceptions gracefully."""
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(side_effect=Exception("Cache error"))

        with patch(
            "app.services.popular.service.get_settings", return_value=mock_settings
        ):
            service = PopularRecipesService(cache_client=mock_cache)

        result = await service._get_from_cache()

        assert result is None

    @pytest.mark.asyncio
    async def test_save_to_cache_does_nothing_when_no_client(
        self, service: PopularRecipesService
    ) -> None:
        """Should not error when cache client is None."""
        service._cache_client = None
        data = PopularRecipesData(total_count=0)

        # Should not raise
        await service._save_to_cache(data)

    @pytest.mark.asyncio
    async def test_save_to_cache_handles_exception(
        self, mock_settings: MagicMock
    ) -> None:
        """Should handle cache write exceptions gracefully."""
        mock_cache = AsyncMock()
        mock_cache.setex = AsyncMock(side_effect=Exception("Cache error"))

        with patch(
            "app.services.popular.service.get_settings", return_value=mock_settings
        ):
            service = PopularRecipesService(cache_client=mock_cache)

        data = PopularRecipesData(total_count=0)

        # Should not raise
        await service._save_to_cache(data)

    @pytest.mark.asyncio
    async def test_invalidate_cache_does_nothing_when_no_client(
        self, service: PopularRecipesService
    ) -> None:
        """Should not error when cache client is None."""
        service._cache_client = None

        # Should not raise
        await service.invalidate_cache()


class TestFetchSourceExtended:
    """Additional tests for _fetch_source method."""

    @pytest.mark.asyncio
    async def test_handles_request_error(self, service: PopularRecipesService) -> None:
        """Should raise PopularRecipesFetchError on request error."""
        await service.initialize()

        source = MagicMock()
        source.name = "TestSource"
        source.base_url = "https://test.com"
        source.popular_endpoint = "/popular"

        assert service._http_client is not None
        service._http_client.get = AsyncMock(
            side_effect=httpx.RequestError("Connection failed")
        )

        with pytest.raises(PopularRecipesFetchError, match="Request failed"):
            await service._fetch_source(source)

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_raises_when_extractor_not_initialized(
        self, service: PopularRecipesService
    ) -> None:
        """Should raise when extractor not initialized."""
        from app.services.popular.exceptions import PopularRecipesParseError

        await service.initialize()
        # Force extractor to None
        service._extractor = None

        source = MagicMock()
        source.name = "TestSource"
        source.base_url = "https://test.com"
        source.popular_endpoint = "/popular"

        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = "<html><body>Test</body></html>"
        assert service._http_client is not None
        service._http_client.get = AsyncMock(return_value=mock_response)

        with pytest.raises(PopularRecipesParseError, match="Extractor not initialized"):
            await service._fetch_source(source)

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_handles_extractor_exception(
        self, service: PopularRecipesService
    ) -> None:
        """Should raise PopularRecipesParseError when extraction fails."""
        from app.services.popular.exceptions import PopularRecipesParseError

        await service.initialize()

        source = MagicMock()
        source.name = "TestSource"
        source.base_url = "https://test.com"
        source.popular_endpoint = "/popular"

        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = "<html><body>Test</body></html>"
        assert service._http_client is not None
        service._http_client.get = AsyncMock(return_value=mock_response)

        # Mock extractor to raise exception
        service._extractor.extract = AsyncMock(side_effect=Exception("Parse error"))

        with pytest.raises(PopularRecipesParseError, match="Failed to parse"):
            await service._fetch_source(source)

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_links_found(
        self, service: PopularRecipesService
    ) -> None:
        """Should return empty list when no recipe links found."""
        await service.initialize()

        source = MagicMock()
        source.name = "TestSource"
        source.base_url = "https://test.com"
        source.popular_endpoint = "/popular"

        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = "<html><body>Test</body></html>"
        assert service._http_client is not None
        service._http_client.get = AsyncMock(return_value=mock_response)

        # Mock extractor to return empty list
        service._extractor.extract = AsyncMock(return_value=[])

        result = await service._fetch_source(source)

        assert result == []
        await service.shutdown()

    @pytest.mark.asyncio
    async def test_processes_and_returns_recipes(
        self, service: PopularRecipesService
    ) -> None:
        """Should process links and return scored recipes."""
        await service.initialize()

        source = MagicMock()
        source.name = "TestSource"
        source.base_url = "https://test.com"
        source.popular_endpoint = "/popular"
        source.max_recipes = 10
        source.source_weight = 1.0

        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = "<html><body>Test</body></html>"
        assert service._http_client is not None
        service._http_client.get = AsyncMock(return_value=mock_response)

        # Mock extractor to return links
        service._extractor.extract = AsyncMock(
            return_value=[("Recipe 1", "https://test.com/recipe/1")]
        )

        # Mock fetch_recipe_details
        service._fetch_recipe_details = AsyncMock(
            return_value=[
                PopularRecipe(
                    recipe_name="Recipe 1",
                    url="https://test.com/recipe/1",
                    source="TestSource",
                    raw_rank=1,
                )
            ]
        )

        result = await service._fetch_source(source)

        assert len(result) == 1
        await service.shutdown()


class TestFetchRecipeDetails:
    """Tests for _fetch_recipe_details method."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_http_client(
        self, service: PopularRecipesService
    ) -> None:
        """Should return empty list when HTTP client is None."""
        service._http_client = None

        source = MagicMock()
        source.name = "TestSource"

        result = await service._fetch_recipe_details(
            [("Recipe", "https://test.com/recipe")], source
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_fetches_recipe_details(self, service: PopularRecipesService) -> None:
        """Should fetch and return recipe details."""
        await service.initialize()

        source = MagicMock()
        source.name = "TestSource"

        # Mock successful recipe page response with recipe schema
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.text = """
        <html>
        <head>
        <script type="application/ld+json">
        {"@type": "Recipe", "name": "Test Recipe"}
        </script>
        </head>
        <body>
        <div class="rating">4.5</div>
        </body>
        </html>
        """
        assert service._http_client is not None
        service._http_client.get = AsyncMock(return_value=mock_response)

        result = await service._fetch_recipe_details(
            [("Recipe 1", "https://test.com/recipe/1")], source
        )

        assert len(result) == 1
        assert result[0].recipe_name == "Recipe 1"
        await service.shutdown()

    @pytest.mark.asyncio
    async def test_skips_non_recipe_pages(self, service: PopularRecipesService) -> None:
        """Should skip pages that are not recipe pages."""
        await service.initialize()

        source = MagicMock()
        source.name = "TestSource"

        # Mock response without recipe schema
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.text = "<html><body>Not a recipe</body></html>"
        assert service._http_client is not None
        service._http_client.get = AsyncMock(return_value=mock_response)

        result = await service._fetch_recipe_details(
            [("Not Recipe", "https://test.com/category")], source
        )

        assert len(result) == 0
        await service.shutdown()

    @pytest.mark.asyncio
    async def test_handles_fetch_error_gracefully(
        self, service: PopularRecipesService
    ) -> None:
        """Should handle fetch errors gracefully and return recipe with default metrics."""
        await service.initialize()

        source = MagicMock()
        source.name = "TestSource"

        # Mock HTTP error
        assert service._http_client is not None
        service._http_client.get = AsyncMock(side_effect=Exception("Connection error"))

        result = await service._fetch_recipe_details(
            [("Recipe 1", "https://test.com/recipe/1")], source
        )

        # Should still return recipe with default metrics
        assert len(result) == 1
        assert result[0].recipe_name == "Recipe 1"
        await service.shutdown()


class TestScoring:
    """Tests for scoring methods."""

    def test_calculate_metric_ranges(self, service: PopularRecipesService) -> None:
        """Should calculate min-max ranges for metrics."""
        from app.schemas.recipe import RecipeEngagementMetrics

        recipes = [
            PopularRecipe(
                recipe_name="Recipe 1",
                url="https://test.com/1",
                source="Test",
                raw_rank=1,
                metrics=RecipeEngagementMetrics(
                    rating=4.5,
                    rating_count=100,
                    favorites=50,
                    reviews=10,
                ),
            ),
            PopularRecipe(
                recipe_name="Recipe 2",
                url="https://test.com/2",
                source="Test",
                raw_rank=2,
                metrics=RecipeEngagementMetrics(
                    rating=4.0,
                    rating_count=200,
                    favorites=100,
                    reviews=20,
                ),
            ),
        ]

        ranges = service._calculate_metric_ranges(recipes)

        assert ranges["rating_count"] == (100, 200)
        assert ranges["favorites"] == (50, 100)
        assert ranges["reviews"] == (10, 20)

    def test_calculate_max_positions(self, service: PopularRecipesService) -> None:
        """Should calculate max position per source."""
        recipes = [
            PopularRecipe(
                recipe_name="Recipe 1",
                url="https://test.com/1",
                source="Source1",
                raw_rank=1,
            ),
            PopularRecipe(
                recipe_name="Recipe 2",
                url="https://test.com/2",
                source="Source1",
                raw_rank=5,
            ),
            PopularRecipe(
                recipe_name="Recipe 3",
                url="https://test.com/3",
                source="Source2",
                raw_rank=3,
            ),
        ]

        max_positions = service._calculate_max_positions(recipes)

        assert max_positions["Source1"] == 5
        assert max_positions["Source2"] == 3

    def test_calculate_score_with_all_metrics(
        self, service: PopularRecipesService
    ) -> None:
        """Should calculate score with all metrics present."""
        from app.schemas.recipe import RecipeEngagementMetrics

        metrics = RecipeEngagementMetrics(
            rating=4.5,
            rating_count=150,
            favorites=75,
            reviews=15,
        )
        metric_ranges = {
            "rating_count": (100.0, 200.0),
            "favorites": (50.0, 100.0),
            "reviews": (10.0, 20.0),
        }

        score = service._calculate_score(
            metrics=metrics,
            position=1,
            max_position=10,
            source_weight=1.0,
            metric_ranges=metric_ranges,
        )

        # Score should be between 0 and 1
        assert 0.0 <= score <= 1.0
        # With good metrics and first position, score should be high
        assert score > 0.5

    def test_calculate_score_with_missing_metrics(
        self, service: PopularRecipesService
    ) -> None:
        """Should handle missing metrics gracefully."""
        from app.schemas.recipe import RecipeEngagementMetrics

        metrics = RecipeEngagementMetrics()  # All None
        metric_ranges: dict[str, tuple[float, float]] = {}

        score = service._calculate_score(
            metrics=metrics,
            position=1,
            max_position=10,
            source_weight=1.0,
            metric_ranges=metric_ranges,
        )

        # Should fall back to position-based scoring
        assert 0.0 <= score <= 1.0

    def test_calculate_score_with_same_metric_values(
        self, service: PopularRecipesService
    ) -> None:
        """Should handle case where all recipes have same metric values."""
        from app.schemas.recipe import RecipeEngagementMetrics

        metrics = RecipeEngagementMetrics(
            rating=4.0,
            rating_count=100,
        )
        # When min == max, normalized value should be 0.5
        metric_ranges = {
            "rating_count": (100.0, 100.0),  # Same min and max
        }

        score = service._calculate_score(
            metrics=metrics,
            position=1,
            max_position=10,
            source_weight=1.0,
            metric_ranges=metric_ranges,
        )

        assert 0.0 <= score <= 1.0

    def test_calculate_score_with_zero_max_position(
        self, service: PopularRecipesService
    ) -> None:
        """Should handle zero max_position."""
        from app.schemas.recipe import RecipeEngagementMetrics

        metrics = RecipeEngagementMetrics()
        metric_ranges: dict[str, tuple[float, float]] = {}

        score = service._calculate_score(
            metrics=metrics,
            position=1,
            max_position=0,  # Edge case
            source_weight=1.0,
            metric_ranges=metric_ranges,
        )

        assert 0.0 <= score <= 1.0

    def test_normalize_and_score_empty_list(
        self, service: PopularRecipesService
    ) -> None:
        """Should return empty list for empty input."""
        result = service._normalize_and_score([])
        assert result == []

    def test_normalize_and_score_calculates_scores(
        self, service: PopularRecipesService
    ) -> None:
        """Should calculate normalized scores for recipes."""
        from app.schemas.recipe import RecipeEngagementMetrics

        recipes = [
            PopularRecipe(
                recipe_name="Recipe 1",
                url="https://test.com/1",
                source="TestSource",
                raw_rank=1,
                metrics=RecipeEngagementMetrics(rating=5.0),
                normalized_score=0.0,
            ),
            PopularRecipe(
                recipe_name="Recipe 2",
                url="https://test.com/2",
                source="TestSource",
                raw_rank=2,
                metrics=RecipeEngagementMetrics(rating=3.0),
                normalized_score=0.0,
            ),
        ]

        result = service._normalize_and_score(recipes)

        # All recipes should have scores calculated
        for recipe in result:
            assert recipe.normalized_score > 0.0


class TestScoreSourceRecipes:
    """Tests for _score_source_recipes method."""

    def test_returns_empty_for_empty_list(self, service: PopularRecipesService) -> None:
        """Should return empty list for empty input."""
        source = MagicMock()
        source.source_weight = 1.0

        result = service._score_source_recipes([], source)

        assert result == []

    def test_scores_and_sorts_recipes(self, service: PopularRecipesService) -> None:
        """Should score and sort recipes by score descending."""
        from app.schemas.recipe import RecipeEngagementMetrics

        source = MagicMock()
        source.source_weight = 1.0

        recipes = [
            PopularRecipe(
                recipe_name="Low Score",
                url="https://test.com/1",
                source="Test",
                raw_rank=10,  # Low position
                metrics=RecipeEngagementMetrics(rating=2.0),
            ),
            PopularRecipe(
                recipe_name="High Score",
                url="https://test.com/2",
                source="Test",
                raw_rank=1,  # High position
                metrics=RecipeEngagementMetrics(rating=5.0),
            ),
        ]

        result = service._score_source_recipes(recipes, source)

        # Should be sorted by score descending
        assert result[0].recipe_name == "High Score"
        assert result[1].recipe_name == "Low Score"


class TestFetchAllSourcesExtended:
    """Additional tests for _fetch_all_sources method."""

    @pytest.mark.asyncio
    async def test_handles_generic_exception(
        self, service: PopularRecipesService
    ) -> None:
        """Should handle generic exceptions from sources."""
        service._fetch_source = AsyncMock(side_effect=Exception("Unexpected error"))

        data = await service._fetch_all_sources()

        assert data.total_count == 0
        assert "TestSource" in data.fetch_errors


class TestPopularRecipesData:
    """Tests for PopularRecipesData model."""

    def test_has_recipes_property(self) -> None:
        """Should correctly report whether data has recipes."""
        empty_data = PopularRecipesData()
        assert empty_data.has_recipes is False

        data_with_recipes = PopularRecipesData(
            recipes=[
                PopularRecipe(
                    recipe_name="Test",
                    url="https://test.com",
                    source="Test",
                    raw_rank=1,
                )
            ],
            total_count=1,
        )
        assert data_with_recipes.has_recipes is True

    def test_partial_success_property(self) -> None:
        """Should correctly identify partial success."""
        # Full success
        full_success = PopularRecipesData(
            recipes=[
                PopularRecipe(
                    recipe_name="Test",
                    url="https://test.com",
                    source="Test",
                    raw_rank=1,
                )
            ],
            total_count=1,
            sources_fetched=["Source1", "Source2"],
        )
        assert full_success.partial_success is False

        # Partial success
        partial = PopularRecipesData(
            recipes=[
                PopularRecipe(
                    recipe_name="Test",
                    url="https://test.com",
                    source="Test",
                    raw_rank=1,
                )
            ],
            total_count=1,
            sources_fetched=["Source1"],
            fetch_errors={"Source2": "Failed"},
        )
        assert partial.partial_success is True

        # Complete failure
        failure = PopularRecipesData(
            fetch_errors={"Source1": "Failed", "Source2": "Failed"},
        )
        assert failure.partial_success is False

    def test_last_updated_defaults_to_now(self) -> None:
        """Should default last_updated to current timestamp."""
        data = PopularRecipesData()

        # Should be a valid ISO timestamp
        parsed = datetime.fromisoformat(data.last_updated)
        assert parsed.tzinfo is not None
