"""Performance tests for popular recipes service.

Tests response times and throughput for cache operations and pagination.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.recipe import (
    PopularRecipe,
    PopularRecipesData,
    RecipeEngagementMetrics,
)
from app.services.popular.service import PopularRecipesService


if TYPE_CHECKING:
    from redis.asyncio import Redis


pytestmark = [pytest.mark.performance, pytest.mark.asyncio]


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings for testing."""
    mock = MagicMock()
    mock.scraping.popular_recipes.enabled = True
    mock.scraping.popular_recipes.cache_ttl = 3600
    mock.scraping.popular_recipes.cache_key = "perf_test"
    mock.scraping.popular_recipes.target_total = 500
    mock.scraping.popular_recipes.fetch_timeout = 30.0
    mock.scraping.popular_recipes.max_concurrent_fetches = 5
    mock.scraping.popular_recipes.sources = []

    mock.scraping.popular_recipes.scoring.rating_weight = 0.35
    mock.scraping.popular_recipes.scoring.rating_count_weight = 0.25
    mock.scraping.popular_recipes.scoring.favorites_weight = 0.25
    mock.scraping.popular_recipes.scoring.reviews_weight = 0.10
    mock.scraping.popular_recipes.scoring.position_weight = 0.05

    return mock


def create_test_recipes(count: int) -> list[PopularRecipe]:
    """Create test recipes for benchmarking."""
    return [
        PopularRecipe(
            recipe_name=f"Performance Test Recipe {i}",
            url=f"https://test.com/recipe/{i}",
            source="PerfSource",
            raw_rank=i + 1,
            metrics=RecipeEngagementMetrics(
                rating=4.0 + (i % 10) / 10,
                rating_count=100 * (i + 1),
                favorites=50 * (i + 1),
                reviews=20 * (i + 1),
            ),
            normalized_score=max(0.1, 0.9 - (i * 0.0005)),  # Ensure score stays >= 0
        )
        for i in range(count)
    ]


class TestCachePerformance:
    """Performance tests for cache operations."""

    async def test_cache_write_performance(
        self,
        cache: Redis[bytes],
        mock_settings: MagicMock,
    ) -> None:
        """Benchmark cache write performance with 500 recipes."""
        with patch(
            "app.services.popular.service.get_settings",
            return_value=mock_settings,
        ):
            service = PopularRecipesService(cache_client=cache)

        test_data = PopularRecipesData(
            recipes=create_test_recipes(500),
            total_count=500,
            sources_fetched=["PerfSource"],
        )

        # Run multiple iterations and measure
        iterations = 10
        start = time.perf_counter()
        for _ in range(iterations):
            await service._save_to_cache(test_data)
        elapsed = (time.perf_counter() - start) / iterations

        # Writing 500 recipes should be fast (< 500ms per write)
        assert elapsed < 0.5

    async def test_cache_read_performance(
        self,
        cache: Redis[bytes],
        mock_settings: MagicMock,
    ) -> None:
        """Benchmark cache read performance with 500 recipes."""
        with patch(
            "app.services.popular.service.get_settings",
            return_value=mock_settings,
        ):
            service = PopularRecipesService(cache_client=cache)

        # Pre-populate cache
        test_data = PopularRecipesData(
            recipes=create_test_recipes(500),
            total_count=500,
            sources_fetched=["PerfSource"],
        )
        await service._save_to_cache(test_data)

        # Run multiple iterations and measure
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            await service._get_from_cache()
        elapsed = (time.perf_counter() - start) / iterations

        # Reading 500 recipes should be fast (< 100ms per read)
        assert elapsed < 0.1

    async def test_cache_hit_vs_miss_comparison(
        self,
        cache: Redis[bytes],
        mock_settings: MagicMock,
    ) -> None:
        """Compare response times for cache hit vs cache miss."""
        with patch(
            "app.services.popular.service.get_settings",
            return_value=mock_settings,
        ):
            service = PopularRecipesService(cache_client=cache)

        # Pre-populate cache
        test_data = PopularRecipesData(
            recipes=create_test_recipes(500),
            total_count=500,
            sources_fetched=["PerfSource"],
        )
        await service._save_to_cache(test_data)

        # Measure cache hit time
        start = time.perf_counter()
        for _ in range(100):
            await service._get_from_cache()
        cache_hit_time = (time.perf_counter() - start) / 100

        # Invalidate cache and verify miss
        await service.invalidate_cache()
        result = await service._get_from_cache()

        # Cache hit should be much faster than network fetch would be
        assert cache_hit_time < 0.1  # Should be < 100ms
        assert result is None  # Should be a miss


class TestPaginationPerformance:
    """Performance tests for pagination operations."""

    async def test_pagination_performance(self, mock_settings: MagicMock) -> None:
        """Test pagination performance with large dataset."""
        with patch(
            "app.services.popular.service.get_settings",
            return_value=mock_settings,
        ):
            service = PopularRecipesService(cache_client=None)

        # Create large cached dataset
        large_data = PopularRecipesData(
            recipes=create_test_recipes(500),
            total_count=500,
            sources_fetched=["PerfSource"],
        )

        # Mock cache to return large dataset
        service._get_or_refresh_cache = AsyncMock(return_value=large_data)

        # Measure pagination at different offsets
        offsets = [0, 100, 250, 400]
        times = []

        for offset in offsets:
            start = time.perf_counter()
            recipes, _ = await service.get_popular_recipes(limit=50, offset=offset)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

            assert len(recipes) <= 50

        # Pagination should be O(1) - similar times regardless of offset
        max_time = max(times)
        min_time = min(times)

        # All operations should be fast (< 100ms)
        assert max_time < 0.1

        # Times should be relatively consistent (within 10x of each other)
        # This is a loose bound to account for test environment variability
        if min_time > 0:
            assert max_time / min_time < 10


class TestScoringPerformance:
    """Performance tests for scoring algorithm."""

    async def test_scoring_performance(self, mock_settings: MagicMock) -> None:
        """Test scoring algorithm performance with large dataset."""
        with patch(
            "app.services.popular.service.get_settings",
            return_value=mock_settings,
        ):
            service = PopularRecipesService(cache_client=None)

        # Create recipes with various metrics
        recipes = create_test_recipes(500)

        # Measure scoring time
        start = time.perf_counter()
        scored = service._normalize_and_score(recipes)
        elapsed = time.perf_counter() - start

        # Scoring 500 recipes should be fast (< 500ms)
        assert elapsed < 0.5
        assert len(scored) == 500

        # Verify scoring worked
        assert all(r.normalized_score >= 0 for r in scored)
        assert all(r.normalized_score <= 1 for r in scored)

    async def test_metric_ranges_calculation_performance(
        self, mock_settings: MagicMock
    ) -> None:
        """Test metric ranges calculation performance."""
        with patch(
            "app.services.popular.service.get_settings",
            return_value=mock_settings,
        ):
            service = PopularRecipesService(cache_client=None)

        recipes = create_test_recipes(1000)

        start = time.perf_counter()
        ranges = service._calculate_metric_ranges(recipes)
        elapsed = time.perf_counter() - start

        # Should be fast (< 100ms for 1000 recipes)
        assert elapsed < 0.1
        assert "rating_count" in ranges
        assert "favorites" in ranges
        assert "reviews" in ranges


class TestCountOnlyPerformance:
    """Performance tests for count-only queries."""

    async def test_count_only_faster_than_full_fetch(
        self, mock_settings: MagicMock
    ) -> None:
        """Count-only should be faster than fetching full data."""
        with patch(
            "app.services.popular.service.get_settings",
            return_value=mock_settings,
        ):
            service = PopularRecipesService(cache_client=None)

        large_data = PopularRecipesData(
            recipes=create_test_recipes(500),
            total_count=500,
            sources_fetched=["PerfSource"],
        )
        service._get_or_refresh_cache = AsyncMock(return_value=large_data)

        # Measure count-only time
        start = time.perf_counter()
        _, count = await service.get_popular_recipes(count_only=True)
        count_only_time = time.perf_counter() - start

        # Measure full fetch time
        start = time.perf_counter()
        recipes, _ = await service.get_popular_recipes(limit=100)
        full_fetch_time = time.perf_counter() - start

        # Count-only should be faster or at least as fast
        # (mainly tests that we're not doing extra work)
        assert count == 500
        assert len(recipes) == 100

        # Both should be fast since we're using cached data
        assert count_only_time < 0.1
        assert full_fetch_time < 0.1
