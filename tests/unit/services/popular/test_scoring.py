"""Unit tests for popularity scoring algorithm."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.schemas.recipe import PopularRecipe, RecipeEngagementMetrics
from app.services.popular.service import PopularRecipesService


pytestmark = pytest.mark.unit


@pytest.fixture
def service() -> PopularRecipesService:
    """Create a PopularRecipesService instance for testing."""
    with patch("app.services.popular.service.get_settings") as mock_settings:
        # Mock the settings
        mock_config = MagicMock()
        mock_config.scraping.popular_recipes.enabled = True
        mock_config.scraping.popular_recipes.cache_ttl = 86400
        mock_config.scraping.popular_recipes.cache_key = "popular_recipes"
        mock_config.scraping.popular_recipes.target_total = 500
        mock_config.scraping.popular_recipes.fetch_timeout = 30.0
        mock_config.scraping.popular_recipes.max_concurrent_fetches = 5
        mock_config.scraping.popular_recipes.sources = []

        # Scoring weights
        mock_config.scraping.popular_recipes.scoring.rating_weight = 0.35
        mock_config.scraping.popular_recipes.scoring.rating_count_weight = 0.25
        mock_config.scraping.popular_recipes.scoring.favorites_weight = 0.25
        mock_config.scraping.popular_recipes.scoring.reviews_weight = 0.10
        mock_config.scraping.popular_recipes.scoring.position_weight = 0.05

        mock_settings.return_value = mock_config
        return PopularRecipesService(cache_client=None)


class TestCalculateScore:
    """Tests for the _calculate_score method."""

    def test_full_metrics_score(self, service: PopularRecipesService) -> None:
        """Should calculate score with all metrics present."""
        metrics = RecipeEngagementMetrics(
            rating=4.5,
            rating_count=1000,
            favorites=500,
            reviews=200,
        )
        metric_ranges: dict[str, tuple[float, float]] = {
            "rating_count": (0.0, 2000.0),
            "favorites": (0.0, 1000.0),
            "reviews": (0.0, 400.0),
        }

        score = service._calculate_score(
            metrics=metrics,
            position=1,
            max_position=100,
            source_weight=1.0,
            metric_ranges=metric_ranges,
        )

        # Score should be between 0 and 1
        assert 0.0 <= score <= 1.0
        # With good metrics, score should be relatively high
        assert score > 0.5

    def test_position_only_score(self, service: PopularRecipesService) -> None:
        """Should calculate score based on position when no metrics available."""
        metrics = RecipeEngagementMetrics()  # All None
        metric_ranges: dict[str, tuple[float, float]] = {}

        # First position should score higher than last
        first_score = service._calculate_score(
            metrics=metrics,
            position=1,
            max_position=100,
            source_weight=1.0,
            metric_ranges=metric_ranges,
        )

        last_score = service._calculate_score(
            metrics=metrics,
            position=100,
            max_position=100,
            source_weight=1.0,
            metric_ranges=metric_ranges,
        )

        assert first_score > last_score
        assert first_score > 0.9  # First position should be near 1.0
        assert last_score < 0.1  # Last position should be near 0.0

    def test_partial_metrics_score(self, service: PopularRecipesService) -> None:
        """Should handle partial metrics (some missing)."""
        metrics = RecipeEngagementMetrics(
            rating=4.0,
            rating_count=500,
            # favorites and reviews are None
        )
        metric_ranges: dict[str, tuple[float, float]] = {
            "rating_count": (0.0, 1000.0),
        }

        score = service._calculate_score(
            metrics=metrics,
            position=10,
            max_position=100,
            source_weight=1.0,
            metric_ranges=metric_ranges,
        )

        # Score should be valid
        assert 0.0 <= score <= 1.0

    def test_source_weight_impact(self, service: PopularRecipesService) -> None:
        """Source weight should scale the final score."""
        metrics = RecipeEngagementMetrics(rating=4.5)
        metric_ranges: dict[str, tuple[float, float]] = {}

        full_weight_score = service._calculate_score(
            metrics=metrics,
            position=1,
            max_position=10,
            source_weight=1.0,
            metric_ranges=metric_ranges,
        )

        half_weight_score = service._calculate_score(
            metrics=metrics,
            position=1,
            max_position=10,
            source_weight=0.5,
            metric_ranges=metric_ranges,
        )

        # Half weight should produce half the score
        assert abs(half_weight_score - full_weight_score * 0.5) < 0.01

    def test_rating_normalization(self, service: PopularRecipesService) -> None:
        """Rating should be normalized from 0-5 to 0-1."""
        high_rating = RecipeEngagementMetrics(rating=5.0)
        low_rating = RecipeEngagementMetrics(rating=1.0)
        metric_ranges: dict[str, tuple[float, float]] = {}

        high_score = service._calculate_score(
            metrics=high_rating,
            position=50,
            max_position=100,
            source_weight=1.0,
            metric_ranges=metric_ranges,
        )

        low_score = service._calculate_score(
            metrics=low_rating,
            position=50,
            max_position=100,
            source_weight=1.0,
            metric_ranges=metric_ranges,
        )

        assert high_score > low_score

    def test_min_max_normalization(self, service: PopularRecipesService) -> None:
        """Count metrics should be normalized using min-max scaling."""
        # Recipe with max values should score higher
        max_metrics = RecipeEngagementMetrics(
            rating=4.0,
            rating_count=1000,
            favorites=500,
            reviews=100,
        )

        min_metrics = RecipeEngagementMetrics(
            rating=4.0,
            rating_count=100,
            favorites=50,
            reviews=10,
        )

        metric_ranges: dict[str, tuple[float, float]] = {
            "rating_count": (100.0, 1000.0),
            "favorites": (50.0, 500.0),
            "reviews": (10.0, 100.0),
        }

        max_score = service._calculate_score(
            metrics=max_metrics,
            position=1,
            max_position=10,
            source_weight=1.0,
            metric_ranges=metric_ranges,
        )

        min_score = service._calculate_score(
            metrics=min_metrics,
            position=1,
            max_position=10,
            source_weight=1.0,
            metric_ranges=metric_ranges,
        )

        assert max_score > min_score

    def test_same_value_normalization(self, service: PopularRecipesService) -> None:
        """Should handle edge case where min equals max."""
        metrics = RecipeEngagementMetrics(
            rating=4.0,
            rating_count=500,
        )
        # All recipes have the same count
        metric_ranges: dict[str, tuple[float, float]] = {
            "rating_count": (500.0, 500.0),  # min == max
        }

        score = service._calculate_score(
            metrics=metrics,
            position=1,
            max_position=10,
            source_weight=1.0,
            metric_ranges=metric_ranges,
        )

        # Should not crash and should return valid score
        assert 0.0 <= score <= 1.0


class TestCalculateMetricRanges:
    """Tests for the _calculate_metric_ranges method."""

    def test_calculates_ranges_for_all_metrics(
        self, service: PopularRecipesService
    ) -> None:
        """Should calculate min-max ranges for all present metrics."""
        recipes = [
            PopularRecipe(
                recipe_name="Recipe 1",
                url="http://example.com/1",
                source="TestSource",
                raw_rank=1,
                metrics=RecipeEngagementMetrics(
                    rating_count=100, favorites=50, reviews=10
                ),
            ),
            PopularRecipe(
                recipe_name="Recipe 2",
                url="http://example.com/2",
                source="TestSource",
                raw_rank=2,
                metrics=RecipeEngagementMetrics(
                    rating_count=500, favorites=200, reviews=40
                ),
            ),
            PopularRecipe(
                recipe_name="Recipe 3",
                url="http://example.com/3",
                source="TestSource",
                raw_rank=3,
                metrics=RecipeEngagementMetrics(
                    rating_count=300, favorites=100, reviews=20
                ),
            ),
        ]

        ranges = service._calculate_metric_ranges(recipes)

        assert ranges["rating_count"] == (100, 500)
        assert ranges["favorites"] == (50, 200)
        assert ranges["reviews"] == (10, 40)

    def test_ignores_none_values(self, service: PopularRecipesService) -> None:
        """Should ignore None values when calculating ranges."""
        recipes = [
            PopularRecipe(
                recipe_name="Recipe 1",
                url="http://example.com/1",
                source="TestSource",
                raw_rank=1,
                metrics=RecipeEngagementMetrics(rating_count=100),
            ),
            PopularRecipe(
                recipe_name="Recipe 2",
                url="http://example.com/2",
                source="TestSource",
                raw_rank=2,
                metrics=RecipeEngagementMetrics(rating_count=None),  # None
            ),
            PopularRecipe(
                recipe_name="Recipe 3",
                url="http://example.com/3",
                source="TestSource",
                raw_rank=3,
                metrics=RecipeEngagementMetrics(rating_count=500),
            ),
        ]

        ranges = service._calculate_metric_ranges(recipes)

        assert ranges["rating_count"] == (100, 500)
        assert "favorites" not in ranges  # All None

    def test_empty_recipes_list(self, service: PopularRecipesService) -> None:
        """Should return empty ranges for empty recipe list."""
        ranges = service._calculate_metric_ranges([])

        assert ranges == {}


class TestCalculateMaxPositions:
    """Tests for the _calculate_max_positions method."""

    def test_calculates_max_per_source(self, service: PopularRecipesService) -> None:
        """Should calculate max position for each source."""
        recipes = [
            PopularRecipe(
                recipe_name="Recipe 1",
                url="http://example.com/1",
                source="Source A",
                raw_rank=1,
                metrics=RecipeEngagementMetrics(),
            ),
            PopularRecipe(
                recipe_name="Recipe 2",
                url="http://example.com/2",
                source="Source A",
                raw_rank=50,
                metrics=RecipeEngagementMetrics(),
            ),
            PopularRecipe(
                recipe_name="Recipe 3",
                url="http://example.com/3",
                source="Source B",
                raw_rank=25,
                metrics=RecipeEngagementMetrics(),
            ),
        ]

        max_positions = service._calculate_max_positions(recipes)

        assert max_positions["Source A"] == 50
        assert max_positions["Source B"] == 25

    def test_empty_recipes_list(self, service: PopularRecipesService) -> None:
        """Should return empty dict for empty recipe list."""
        max_positions = service._calculate_max_positions([])

        assert max_positions == {}


class TestNormalizeAndScore:
    """Tests for the _normalize_and_score method."""

    def test_scores_all_recipes(self, service: PopularRecipesService) -> None:
        """Should calculate normalized scores for all recipes."""
        # Need to patch sources for source weights
        service._config.sources = [
            MagicMock(name="TestSource", source_weight=1.0),
        ]

        recipes = [
            PopularRecipe(
                recipe_name="Recipe 1",
                url="http://example.com/1",
                source="TestSource",
                raw_rank=1,
                metrics=RecipeEngagementMetrics(rating=4.5, rating_count=1000),
                normalized_score=0.0,
            ),
            PopularRecipe(
                recipe_name="Recipe 2",
                url="http://example.com/2",
                source="TestSource",
                raw_rank=2,
                metrics=RecipeEngagementMetrics(rating=3.5, rating_count=500),
                normalized_score=0.0,
            ),
        ]

        normalized = service._normalize_and_score(recipes)

        # All recipes should have non-zero scores
        assert all(r.normalized_score > 0 for r in normalized)
        # Higher rated recipe should have higher score
        assert normalized[0].normalized_score > normalized[1].normalized_score

    def test_handles_empty_list(self, service: PopularRecipesService) -> None:
        """Should handle empty recipe list."""
        result = service._normalize_and_score([])

        assert result == []

    def test_uses_default_source_weight(self, service: PopularRecipesService) -> None:
        """Should use default weight of 1.0 for unknown sources."""
        service._config.sources = []  # No configured sources

        recipes = [
            PopularRecipe(
                recipe_name="Recipe 1",
                url="http://example.com/1",
                source="UnknownSource",
                raw_rank=1,
                metrics=RecipeEngagementMetrics(rating=4.0),
            ),
        ]

        normalized = service._normalize_and_score(recipes)

        assert len(normalized) == 1
        assert normalized[0].normalized_score > 0
