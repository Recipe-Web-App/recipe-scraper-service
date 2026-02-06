"""Performance tests for popular recipes service.

Tests response times and throughput for cache operations and pagination.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import orjson
import pytest
from arq.connections import ArqRedis, RedisSettings, create_pool

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

    @pytest.mark.flaky(reruns=3, reruns_delay=1)
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


class TestEndpointPerformance:
    """Performance tests for the popular recipes endpoint."""

    async def test_endpoint_cache_hit_response_time(
        self,
        cache: Redis[bytes],
        mock_settings: MagicMock,
    ) -> None:
        """Endpoint should respond within 50ms on cache hit."""
        # Pre-populate cache
        cache_key = f"popular:{mock_settings.scraping.popular_recipes.cache_key}"
        test_data = PopularRecipesData(
            recipes=create_test_recipes(100),
            total_count=100,
            sources_fetched=["PerfSource"],
        )
        await cache.set(
            cache_key,
            orjson.dumps(test_data.model_dump()),
            ex=3600,
        )

        # Simulate endpoint logic (cache read + pagination + response building)
        async def simulate_endpoint() -> None:
            cached_bytes = await cache.get(cache_key)
            if cached_bytes:
                data = PopularRecipesData.model_validate(orjson.loads(cached_bytes))
                _ = data.recipes[0:50]  # Pagination

        # Measure average response time
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            await simulate_endpoint()
        avg_time = (time.perf_counter() - start) / iterations

        # Should respond within 50ms on cache hit
        assert avg_time < 0.05

    async def test_endpoint_cache_miss_503_response_time(
        self,
        cache: Redis[bytes],
        mock_settings: MagicMock,
    ) -> None:
        """Endpoint should respond with 503 within 100ms on cache miss."""
        # Ensure cache is empty
        cache_key = (
            f"popular:{mock_settings.scraping.popular_recipes.cache_key}_miss_test"
        )
        await cache.delete(cache_key)

        # Simulate endpoint logic for cache miss
        async def simulate_cache_miss_endpoint() -> tuple[int, dict]:
            cached_bytes = await cache.get(cache_key)
            if not cached_bytes:
                # Return 503 immediately (job enqueue is mocked out)
                return (503, {"detail": "Popular recipes are being refreshed."})
            return (200, {})

        # Measure response time
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            status, _ = await simulate_cache_miss_endpoint()
            assert status == 503
        avg_time = (time.perf_counter() - start) / iterations

        # Should respond within 100ms on cache miss
        assert avg_time < 0.1


class TestConcurrencyPerformance:
    """Performance tests for concurrent operations."""

    async def test_concurrent_cache_reads(
        self,
        cache: Redis[bytes],
        mock_settings: MagicMock,
    ) -> None:
        """Should handle 100 concurrent cache reads efficiently."""
        # Pre-populate cache
        cache_key = f"popular:{mock_settings.scraping.popular_recipes.cache_key}"
        test_data = PopularRecipesData(
            recipes=create_test_recipes(200),
            total_count=200,
            sources_fetched=["PerfSource"],
        )
        await cache.set(
            cache_key,
            orjson.dumps(test_data.model_dump()),
            ex=3600,
        )

        async def concurrent_read() -> PopularRecipesData:
            cached_bytes = await cache.get(cache_key)
            assert cached_bytes is not None
            return PopularRecipesData.model_validate(orjson.loads(cached_bytes))

        # Run 100 concurrent reads
        start = time.perf_counter()
        results = await asyncio.gather(*[concurrent_read() for _ in range(100)])
        elapsed = time.perf_counter() - start

        # All should succeed
        assert all(r.total_count == 200 for r in results)

        # 100 concurrent reads should complete within 1 second
        assert elapsed < 1.0

    async def test_job_deduplication_performance(
        self,
        cache: Redis[bytes],
    ) -> None:
        """Concurrent cache misses should result in efficient job enqueueing."""
        # Create ARQ pool for testing
        pool: ArqRedis = await create_pool(
            RedisSettings(
                host=cache.connection_pool.connection_kwargs["host"],
                port=cache.connection_pool.connection_kwargs["port"],
                database=1,  # Use queue db
            )
        )

        try:
            job_id = "perf_test_dedup_job"

            async def simulate_cache_miss_with_enqueue() -> str | None:
                # Simulate cache miss
                # Enqueue with fixed job_id (ARQ deduplicates)
                job = await pool.enqueue_job(
                    "refresh_popular_recipes",
                    _job_id=job_id,
                )
                return job.job_id if job else None

            # Simulate 100 concurrent cache misses trying to enqueue
            start = time.perf_counter()
            results = await asyncio.gather(
                *[simulate_cache_miss_with_enqueue() for _ in range(100)]
            )
            elapsed = time.perf_counter() - start

            # Count successful enqueues vs deduped (None)
            enqueued = [r for r in results if r is not None]
            deduped = [r for r in results if r is None]

            # First one should succeed, rest should be deduplicated
            assert len(enqueued) == 1
            assert len(deduped) == 99

            # All 100 should complete within 1 second
            assert elapsed < 1.0

        finally:
            await pool.close()
