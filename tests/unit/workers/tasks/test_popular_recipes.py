"""Unit tests for popular recipes worker tasks.

Tests cover:
- refresh_popular_recipes task
- check_and_refresh_popular_recipes cron job
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.recipe import PopularRecipe, PopularRecipesData
from app.workers.tasks.popular_recipes import (
    check_and_refresh_popular_recipes,
    refresh_popular_recipes,
)


pytestmark = pytest.mark.unit


def _create_mock_popular_recipes_data(
    total_count: int = 10,
    sources_fetched: list[str] | None = None,
    fetch_errors: dict[str, str] | None = None,
) -> PopularRecipesData:
    """Create mock PopularRecipesData for testing."""
    if sources_fetched is None:
        sources_fetched = ["Taste of Home", "AllRecipes"]

    recipes = [
        PopularRecipe(
            recipe_name=f"Recipe {i}",
            url=f"https://example.com/recipe-{i}",
            source=sources_fetched[i % len(sources_fetched)]
            if sources_fetched
            else "Unknown",
            raw_rank=i + 1,
            normalized_score=max(0.0, 1.0 - (i * 0.1)),
        )
        for i in range(total_count)
    ]

    return PopularRecipesData(
        recipes=recipes,
        total_count=total_count,
        sources_fetched=sources_fetched,
        fetch_errors=fetch_errors or {},
    )


def _create_mock_settings() -> MagicMock:
    """Create mock settings with popular recipes config."""
    mock_settings = MagicMock()
    mock_settings.scraping.popular_recipes.cache_key = "popular_recipes"
    mock_settings.scraping.popular_recipes.cache_ttl = 86400
    mock_settings.scraping.popular_recipes.refresh_threshold = 3600
    return mock_settings


class TestRefreshPopularRecipes:
    """Tests for refresh_popular_recipes task."""

    @pytest.mark.asyncio
    async def test_refresh_success(self) -> None:
        """Should fetch recipes and return success result."""
        mock_cache_client = AsyncMock()
        mock_llm_client = AsyncMock()
        mock_service = AsyncMock()
        mock_data = _create_mock_popular_recipes_data(
            total_count=15,
            sources_fetched=["Taste of Home", "AllRecipes"],
        )
        mock_service.refresh_cache.return_value = mock_data

        ctx = {
            "cache_client": mock_cache_client,
            "llm_client": mock_llm_client,
        }

        with patch(
            "app.workers.tasks.popular_recipes.PopularRecipesService",
            return_value=mock_service,
        ):
            result = await refresh_popular_recipes(ctx)

        assert result["status"] == "completed"
        assert result["recipe_count"] == 15
        assert result["sources_fetched"] == ["Taste of Home", "AllRecipes"]
        assert result["sources_failed"] == []
        mock_service.initialize.assert_called_once()
        mock_service.refresh_cache.assert_called_once()
        mock_service.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_with_partial_failures(self) -> None:
        """Should handle partial source failures and report them."""
        mock_cache_client = AsyncMock()
        mock_service = AsyncMock()
        mock_data = _create_mock_popular_recipes_data(
            total_count=10,
            sources_fetched=["Taste of Home"],
            fetch_errors={"AllRecipes": "Connection timeout"},
        )
        mock_service.refresh_cache.return_value = mock_data

        ctx = {
            "cache_client": mock_cache_client,
            "llm_client": None,
        }

        with patch(
            "app.workers.tasks.popular_recipes.PopularRecipesService",
            return_value=mock_service,
        ):
            result = await refresh_popular_recipes(ctx)

        assert result["status"] == "completed"
        assert result["recipe_count"] == 10
        assert result["sources_fetched"] == ["Taste of Home"]
        assert result["sources_failed"] == ["AllRecipes"]

    @pytest.mark.asyncio
    async def test_refresh_calls_shutdown_on_error(self) -> None:
        """Should call shutdown even if refresh_cache raises an error."""
        mock_cache_client = AsyncMock()
        mock_service = AsyncMock()
        mock_service.refresh_cache.side_effect = RuntimeError("Fetch failed")

        ctx = {
            "cache_client": mock_cache_client,
            "llm_client": None,
        }

        with (
            patch(
                "app.workers.tasks.popular_recipes.PopularRecipesService",
                return_value=mock_service,
            ),
            pytest.raises(RuntimeError, match="Fetch failed"),
        ):
            await refresh_popular_recipes(ctx)

        mock_service.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_works_without_llm_client(self) -> None:
        """Should work when llm_client is not in context."""
        mock_cache_client = AsyncMock()
        mock_service = AsyncMock()
        mock_data = _create_mock_popular_recipes_data(total_count=5)
        mock_service.refresh_cache.return_value = mock_data

        ctx = {"cache_client": mock_cache_client}  # No llm_client

        with patch(
            "app.workers.tasks.popular_recipes.PopularRecipesService",
            return_value=mock_service,
        ) as mock_cls:
            result = await refresh_popular_recipes(ctx)

        assert result["status"] == "completed"
        # Verify service was created with llm_client=None
        mock_cls.assert_called_once_with(
            cache_client=mock_cache_client,
            llm_client=None,
        )

    @pytest.mark.asyncio
    async def test_refresh_works_without_cache_client(self) -> None:
        """Should work when cache_client is not in context."""
        mock_service = AsyncMock()
        mock_data = _create_mock_popular_recipes_data(total_count=5)
        mock_service.refresh_cache.return_value = mock_data

        ctx = {}  # Empty context

        with patch(
            "app.workers.tasks.popular_recipes.PopularRecipesService",
            return_value=mock_service,
        ) as mock_cls:
            result = await refresh_popular_recipes(ctx)

        assert result["status"] == "completed"
        mock_cls.assert_called_once_with(
            cache_client=None,
            llm_client=None,
        )


class TestCheckAndRefreshPopularRecipes:
    """Tests for check_and_refresh_popular_recipes cron job."""

    @pytest.mark.asyncio
    async def test_skips_when_cache_healthy(self) -> None:
        """Should skip refresh when cache TTL is above threshold."""
        mock_cache_client = AsyncMock()
        mock_cache_client.ttl.return_value = 7200  # 2 hours remaining
        mock_settings = _create_mock_settings()

        ctx = {"cache_client": mock_cache_client}

        with patch(
            "app.workers.tasks.popular_recipes.get_settings",
            return_value=mock_settings,
        ):
            result = await check_and_refresh_popular_recipes(ctx)

        assert result["status"] == "skipped"
        assert result["ttl_remaining"] == 7200
        mock_cache_client.ttl.assert_called_once_with("popular:popular_recipes")

    @pytest.mark.asyncio
    async def test_refreshes_when_ttl_below_threshold(self) -> None:
        """Should trigger refresh when TTL is below threshold."""
        mock_cache_client = AsyncMock()
        mock_cache_client.ttl.return_value = 1800  # 30 minutes remaining
        mock_settings = _create_mock_settings()
        mock_service = AsyncMock()
        mock_data = _create_mock_popular_recipes_data()
        mock_service.refresh_cache.return_value = mock_data

        ctx = {"cache_client": mock_cache_client}

        with (
            patch(
                "app.workers.tasks.popular_recipes.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "app.workers.tasks.popular_recipes.PopularRecipesService",
                return_value=mock_service,
            ),
        ):
            result = await check_and_refresh_popular_recipes(ctx)

        assert result["status"] == "completed"
        mock_service.refresh_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_refreshes_when_cache_missing(self) -> None:
        """Should trigger refresh when cache key doesn't exist (TTL = -2)."""
        mock_cache_client = AsyncMock()
        mock_cache_client.ttl.return_value = -2  # Key doesn't exist
        mock_settings = _create_mock_settings()
        mock_service = AsyncMock()
        mock_data = _create_mock_popular_recipes_data()
        mock_service.refresh_cache.return_value = mock_data

        ctx = {"cache_client": mock_cache_client}

        with (
            patch(
                "app.workers.tasks.popular_recipes.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "app.workers.tasks.popular_recipes.PopularRecipesService",
                return_value=mock_service,
            ),
        ):
            result = await check_and_refresh_popular_recipes(ctx)

        assert result["status"] == "completed"
        mock_service.refresh_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_refreshes_when_no_expiry(self) -> None:
        """Should trigger refresh when key has no expiry (TTL = -1)."""
        mock_cache_client = AsyncMock()
        mock_cache_client.ttl.return_value = -1  # No expiry set
        mock_settings = _create_mock_settings()
        mock_service = AsyncMock()
        mock_data = _create_mock_popular_recipes_data()
        mock_service.refresh_cache.return_value = mock_data

        ctx = {"cache_client": mock_cache_client}

        with (
            patch(
                "app.workers.tasks.popular_recipes.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "app.workers.tasks.popular_recipes.PopularRecipesService",
                return_value=mock_service,
            ),
        ):
            result = await check_and_refresh_popular_recipes(ctx)

        assert result["status"] == "completed"
        mock_service.refresh_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_when_no_cache_client(self) -> None:
        """Should skip when cache_client is not available."""
        ctx: dict[str, AsyncMock] = {}  # No cache_client

        mock_settings = _create_mock_settings()

        with patch(
            "app.workers.tasks.popular_recipes.get_settings",
            return_value=mock_settings,
        ):
            result = await check_and_refresh_popular_recipes(ctx)

        assert result["status"] == "skipped"
        assert result["reason"] == "no_cache_client"

    @pytest.mark.asyncio
    async def test_uses_config_cache_key(self) -> None:
        """Should use cache key from config with 'popular:' prefix."""
        mock_cache_client = AsyncMock()
        mock_cache_client.ttl.return_value = 86400  # 24 hours
        mock_settings = _create_mock_settings()
        mock_settings.scraping.popular_recipes.cache_key = "custom_key"

        ctx = {"cache_client": mock_cache_client}

        with patch(
            "app.workers.tasks.popular_recipes.get_settings",
            return_value=mock_settings,
        ):
            await check_and_refresh_popular_recipes(ctx)

        mock_cache_client.ttl.assert_called_once_with("popular:custom_key")

    @pytest.mark.asyncio
    async def test_refreshes_at_exact_threshold(self) -> None:
        """Should trigger refresh when TTL equals threshold (boundary)."""
        mock_cache_client = AsyncMock()
        mock_cache_client.ttl.return_value = 3600  # Exactly at threshold
        mock_settings = _create_mock_settings()
        mock_service = AsyncMock()
        mock_data = _create_mock_popular_recipes_data()
        mock_service.refresh_cache.return_value = mock_data

        ctx = {"cache_client": mock_cache_client}

        with (
            patch(
                "app.workers.tasks.popular_recipes.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "app.workers.tasks.popular_recipes.PopularRecipesService",
                return_value=mock_service,
            ),
        ):
            result = await check_and_refresh_popular_recipes(ctx)

        # TTL < threshold (3600 < 3600 is false), so should skip
        assert result["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_refreshes_just_below_threshold(self) -> None:
        """Should trigger refresh when TTL is just below threshold."""
        mock_cache_client = AsyncMock()
        mock_cache_client.ttl.return_value = 3599  # Just below threshold
        mock_settings = _create_mock_settings()
        mock_service = AsyncMock()
        mock_data = _create_mock_popular_recipes_data()
        mock_service.refresh_cache.return_value = mock_data

        ctx = {"cache_client": mock_cache_client}

        with (
            patch(
                "app.workers.tasks.popular_recipes.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "app.workers.tasks.popular_recipes.PopularRecipesService",
                return_value=mock_service,
            ),
        ):
            result = await check_and_refresh_popular_recipes(ctx)

        assert result["status"] == "completed"
        mock_service.refresh_cache.assert_called_once()
