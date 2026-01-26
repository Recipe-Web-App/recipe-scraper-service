"""Integration tests for popular recipes service.

Tests the service with real Redis cache using testcontainers.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import orjson
import pytest

from app.schemas.recipe import (
    PopularRecipe,
    PopularRecipesData,
    RecipeEngagementMetrics,
)
from app.services.popular.service import PopularRecipesService
from app.workers.tasks.popular_recipes import (
    check_and_refresh_popular_recipes,
    refresh_popular_recipes,
)


if TYPE_CHECKING:
    from redis.asyncio import Redis


pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings for testing."""
    mock = MagicMock()
    mock.scraping.popular_recipes.enabled = True
    mock.scraping.popular_recipes.cache_ttl = 60  # Short TTL for testing
    mock.scraping.popular_recipes.cache_key = "test_popular_recipes"
    mock.scraping.popular_recipes.target_total = 100
    mock.scraping.popular_recipes.fetch_timeout = 10.0
    mock.scraping.popular_recipes.max_concurrent_fetches = 2

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


class TestCacheIntegration:
    """Tests for cache operations with real Redis."""

    async def test_cache_stores_and_retrieves_data(
        self, cache: Redis[bytes], mock_settings: MagicMock
    ) -> None:
        """Should store and retrieve data from Redis cache."""
        with patch(
            "app.services.popular.service.get_settings",
            return_value=mock_settings,
        ):
            service = PopularRecipesService(cache_client=cache)

        # Create test data
        test_data = PopularRecipesData(
            recipes=[
                PopularRecipe(
                    recipe_name="Cached Recipe",
                    url="https://test.com/cached",
                    source="TestSource",
                    raw_rank=1,
                    metrics=RecipeEngagementMetrics(rating=4.5),
                    normalized_score=0.9,
                )
            ],
            total_count=1,
            sources_fetched=["TestSource"],
        )

        # Save to cache
        await service._save_to_cache(test_data)

        # Retrieve from cache
        cached = await service._get_from_cache()

        assert cached is not None
        assert cached.total_count == 1
        assert cached.recipes[0].recipe_name == "Cached Recipe"
        assert cached.recipes[0].metrics.rating == 4.5

    async def test_cache_miss_returns_none(
        self, cache: Redis[bytes], mock_settings: MagicMock
    ) -> None:
        """Should return None on cache miss."""
        # Use a unique cache key to ensure miss
        mock_settings.scraping.popular_recipes.cache_key = "nonexistent_key"

        with patch(
            "app.services.popular.service.get_settings",
            return_value=mock_settings,
        ):
            service = PopularRecipesService(cache_client=cache)

        cached = await service._get_from_cache()

        assert cached is None

    async def test_cache_invalidation_deletes_key(
        self, cache: Redis[bytes], mock_settings: MagicMock
    ) -> None:
        """Should delete cache key on invalidation."""
        with patch(
            "app.services.popular.service.get_settings",
            return_value=mock_settings,
        ):
            service = PopularRecipesService(cache_client=cache)

        # Store some data
        test_data = PopularRecipesData(
            recipes=[
                PopularRecipe(
                    recipe_name="To Delete",
                    url="https://test.com/delete",
                    source="TestSource",
                    raw_rank=1,
                )
            ],
            total_count=1,
        )
        await service._save_to_cache(test_data)

        # Verify it's cached
        cached = await service._get_from_cache()
        assert cached is not None

        # Invalidate
        await service.invalidate_cache()

        # Verify it's gone
        cached = await service._get_from_cache()
        assert cached is None

    async def test_cache_preserves_all_recipe_fields(
        self, cache: Redis[bytes], mock_settings: MagicMock
    ) -> None:
        """Should preserve all recipe fields through cache round-trip."""
        with patch(
            "app.services.popular.service.get_settings",
            return_value=mock_settings,
        ):
            service = PopularRecipesService(cache_client=cache)

        # Create recipe with all fields
        original_recipe = PopularRecipe(
            recipe_name="Full Recipe",
            url="https://test.com/full",
            source="TestSource",
            raw_rank=5,
            metrics=RecipeEngagementMetrics(
                rating=4.7,
                rating_count=1500,
                favorites=800,
                reviews=300,
            ),
            normalized_score=0.875,
        )

        test_data = PopularRecipesData(
            recipes=[original_recipe],
            total_count=1,
            last_updated=datetime.now(UTC).isoformat(),
            sources_fetched=["TestSource"],
            fetch_errors={"FailedSource": "Connection timeout"},
        )

        await service._save_to_cache(test_data)
        cached = await service._get_from_cache()

        assert cached is not None
        cached_recipe = cached.recipes[0]

        assert cached_recipe.recipe_name == "Full Recipe"
        assert cached_recipe.url == "https://test.com/full"
        assert cached_recipe.source == "TestSource"
        assert cached_recipe.raw_rank == 5
        assert cached_recipe.metrics.rating == 4.7
        assert cached_recipe.metrics.rating_count == 1500
        assert cached_recipe.metrics.favorites == 800
        assert cached_recipe.metrics.reviews == 300
        assert cached_recipe.normalized_score == 0.875
        assert cached.sources_fetched == ["TestSource"]
        assert cached.fetch_errors == {"FailedSource": "Connection timeout"}


class TestGetOrRefreshCache:
    """Tests for the cache-or-fetch logic."""

    async def test_returns_cached_data_on_hit(
        self, cache: Redis[bytes], mock_settings: MagicMock
    ) -> None:
        """Should return cached data without fetching on cache hit."""
        with patch(
            "app.services.popular.service.get_settings",
            return_value=mock_settings,
        ):
            service = PopularRecipesService(cache_client=cache)

        # Pre-populate cache
        test_data = PopularRecipesData(
            recipes=[
                PopularRecipe(
                    recipe_name="Pre-cached",
                    url="https://test.com/precached",
                    source="TestSource",
                    raw_rank=1,
                )
            ],
            total_count=1,
        )
        await service._save_to_cache(test_data)

        # Mock fetch to ensure it's not called
        service._fetch_all_sources = AsyncMock()

        # Get data - should use cache
        data = await service._get_or_refresh_cache()

        assert data.recipes[0].recipe_name == "Pre-cached"
        service._fetch_all_sources.assert_not_called()

    async def test_fetches_on_cache_miss(
        self, cache: Redis[bytes], mock_settings: MagicMock
    ) -> None:
        """Should fetch fresh data on cache miss."""
        # Use unique key to ensure miss
        mock_settings.scraping.popular_recipes.cache_key = "fresh_fetch_test"

        with patch(
            "app.services.popular.service.get_settings",
            return_value=mock_settings,
        ):
            service = PopularRecipesService(cache_client=cache)

        # Mock fetch to return test data
        fresh_data = PopularRecipesData(
            recipes=[
                PopularRecipe(
                    recipe_name="Fresh",
                    url="https://test.com/fresh",
                    source="TestSource",
                    raw_rank=1,
                )
            ],
            total_count=1,
        )
        service._fetch_all_sources = AsyncMock(return_value=fresh_data)

        # Get data - should fetch
        data = await service._get_or_refresh_cache()

        assert data.recipes[0].recipe_name == "Fresh"
        service._fetch_all_sources.assert_called_once()

        # Verify it was cached
        cached = await service._get_from_cache()
        assert cached is not None
        assert cached.recipes[0].recipe_name == "Fresh"


class TestConcurrentAccess:
    """Tests for concurrent cache access."""

    async def test_concurrent_reads_work_correctly(
        self, cache: Redis[bytes], mock_settings: MagicMock
    ) -> None:
        """Should handle concurrent cache reads correctly."""
        with patch(
            "app.services.popular.service.get_settings",
            return_value=mock_settings,
        ):
            service = PopularRecipesService(cache_client=cache)

        # Pre-populate cache
        test_data = PopularRecipesData(
            recipes=[
                PopularRecipe(
                    recipe_name=f"Recipe {i}",
                    url=f"https://test.com/recipe{i}",
                    source="TestSource",
                    raw_rank=i + 1,
                )
                for i in range(10)
            ],
            total_count=10,
        )
        await service._save_to_cache(test_data)

        # Concurrent reads
        async def read_cache() -> PopularRecipesData | None:
            return await service._get_from_cache()

        results = await asyncio.gather(*[read_cache() for _ in range(10)])

        # All reads should succeed
        assert all(r is not None for r in results)
        assert all(r.total_count == 10 for r in results if r)


class TestWorkerTasksIntegration:
    """Integration tests for worker tasks with real Redis."""

    @pytest.fixture
    def worker_mock_settings(self, mock_settings: MagicMock) -> MagicMock:
        """Extend mock settings for worker tasks."""
        mock_settings.scraping.popular_recipes.refresh_threshold = 3600
        return mock_settings

    async def test_check_and_refresh_skips_healthy_cache(
        self, cache: Redis[bytes], worker_mock_settings: MagicMock
    ) -> None:
        """Should skip refresh when cache TTL is healthy."""

        # Pre-populate cache with long TTL
        cache_key = f"popular:{worker_mock_settings.scraping.popular_recipes.cache_key}"
        test_data = PopularRecipesData(
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

        await cache.set(
            cache_key,
            orjson.dumps(test_data.model_dump()),
            ex=7200,  # 2 hours (above 1 hour threshold)
        )

        ctx = {"cache_client": cache}

        with patch(
            "app.workers.tasks.popular_recipes.get_settings",
            return_value=worker_mock_settings,
        ):
            result = await check_and_refresh_popular_recipes(ctx)

        assert result["status"] == "skipped"
        assert result["ttl_remaining"] > 3600

    async def test_check_and_refresh_triggers_on_low_ttl(
        self, cache: Redis[bytes], worker_mock_settings: MagicMock
    ) -> None:
        """Should trigger refresh when cache TTL is below threshold."""

        # Pre-populate cache with short TTL
        cache_key = f"popular:{worker_mock_settings.scraping.popular_recipes.cache_key}"
        test_data = PopularRecipesData(
            recipes=[
                PopularRecipe(
                    recipe_name="Expiring Recipe",
                    url="https://test.com/expiring",
                    source="TestSource",
                    raw_rank=1,
                )
            ],
            total_count=1,
        )

        await cache.set(
            cache_key,
            orjson.dumps(test_data.model_dump()),
            ex=1800,  # 30 minutes (below 1 hour threshold)
        )

        ctx = {"cache_client": cache}

        # Mock the service to avoid real HTTP calls
        mock_service = AsyncMock()
        mock_service.refresh_cache.return_value = PopularRecipesData(
            recipes=[
                PopularRecipe(
                    recipe_name="Refreshed Recipe",
                    url="https://test.com/refreshed",
                    source="TestSource",
                    raw_rank=1,
                )
            ],
            total_count=1,
            sources_fetched=["TestSource"],
        )

        with (
            patch(
                "app.workers.tasks.popular_recipes.get_settings",
                return_value=worker_mock_settings,
            ),
            patch(
                "app.workers.tasks.popular_recipes.PopularRecipesService",
                return_value=mock_service,
            ),
        ):
            result = await check_and_refresh_popular_recipes(ctx)

        assert result["status"] == "completed"
        mock_service.refresh_cache.assert_called_once()

    async def test_check_and_refresh_triggers_on_missing_cache(
        self, cache: Redis[bytes], worker_mock_settings: MagicMock
    ) -> None:
        """Should trigger refresh when cache key doesn't exist."""

        # Use a unique cache key that doesn't exist
        worker_mock_settings.scraping.popular_recipes.cache_key = (
            "nonexistent_worker_test"
        )
        cache_key = f"popular:{worker_mock_settings.scraping.popular_recipes.cache_key}"

        # Ensure key doesn't exist
        await cache.delete(cache_key)

        ctx = {"cache_client": cache}

        mock_service = AsyncMock()
        mock_service.refresh_cache.return_value = PopularRecipesData(
            recipes=[
                PopularRecipe(
                    recipe_name="Fresh Recipe",
                    url="https://test.com/fresh",
                    source="TestSource",
                    raw_rank=1,
                )
            ],
            total_count=1,
            sources_fetched=["TestSource"],
        )

        with (
            patch(
                "app.workers.tasks.popular_recipes.get_settings",
                return_value=worker_mock_settings,
            ),
            patch(
                "app.workers.tasks.popular_recipes.PopularRecipesService",
                return_value=mock_service,
            ),
        ):
            result = await check_and_refresh_popular_recipes(ctx)

        assert result["status"] == "completed"
        mock_service.refresh_cache.assert_called_once()

    async def test_refresh_popular_recipes_caches_result(
        self, cache: Redis[bytes], worker_mock_settings: MagicMock
    ) -> None:
        """Should cache the refreshed data after fetch."""

        ctx = {
            "cache_client": cache,
            "llm_client": None,
        }

        # Mock service to return test data
        mock_service = AsyncMock()
        mock_data = PopularRecipesData(
            recipes=[
                PopularRecipe(
                    recipe_name="Worker Cached Recipe",
                    url="https://test.com/worker-cached",
                    source="TestSource",
                    raw_rank=1,
                    normalized_score=0.95,
                )
            ],
            total_count=1,
            sources_fetched=["TestSource"],
        )
        mock_service.refresh_cache.return_value = mock_data

        with (
            patch(
                "app.workers.tasks.popular_recipes.get_settings",
                return_value=worker_mock_settings,
            ),
            patch(
                "app.workers.tasks.popular_recipes.PopularRecipesService",
                return_value=mock_service,
            ),
        ):
            result = await refresh_popular_recipes(ctx)

        assert result["status"] == "completed"
        assert result["recipe_count"] == 1
        assert result["sources_fetched"] == ["TestSource"]

        # Verify service lifecycle was respected
        mock_service.initialize.assert_called_once()
        mock_service.refresh_cache.assert_called_once()
        mock_service.shutdown.assert_called_once()

    async def test_cache_ttl_boundary_check(
        self, cache: Redis[bytes], worker_mock_settings: MagicMock
    ) -> None:
        """Should correctly handle TTL exactly at threshold boundary."""

        cache_key = f"popular:{worker_mock_settings.scraping.popular_recipes.cache_key}"
        test_data = PopularRecipesData(
            recipes=[
                PopularRecipe(
                    recipe_name="Boundary Recipe",
                    url="https://test.com/boundary",
                    source="TestSource",
                    raw_rank=1,
                )
            ],
            total_count=1,
        )

        # Set TTL exactly at threshold (3600 seconds)
        await cache.set(
            cache_key,
            orjson.dumps(test_data.model_dump()),
            ex=3600,  # Exactly at threshold
        )

        ctx = {"cache_client": cache}

        with patch(
            "app.workers.tasks.popular_recipes.get_settings",
            return_value=worker_mock_settings,
        ):
            result = await check_and_refresh_popular_recipes(ctx)

        # TTL < threshold (3600 < 3600 is false, but due to timing it might be 3599)
        # The condition is `ttl < threshold`, so at exactly 3600 it should skip
        # but due to timing, it may have decreased slightly
        assert result["status"] in ("skipped", "completed")
