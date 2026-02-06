"""Unit tests for RecipeScraperService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import orjson
import pytest
from recipe_scrapers import WebsiteNotImplementedError

from app.services.scraping.exceptions import (
    RecipeNotFoundError,
    ScrapingFetchError,
    ScrapingParseError,
    ScrapingTimeoutError,
)
from app.services.scraping.models import ScrapedRecipe
from app.services.scraping.service import RecipeScraperService


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings."""
    settings = MagicMock()
    settings.scraping.fetch_timeout = 30.0
    settings.scraping.cache_enabled = False
    settings.scraping.cache_ttl = 3600
    return settings


@pytest.fixture
def service(mock_settings: MagicMock) -> RecipeScraperService:
    """Create a RecipeScraperService with mocked settings."""
    with patch(
        "app.services.scraping.service.get_settings",
        return_value=mock_settings,
    ):
        return RecipeScraperService()


class TestRecipeScraperServiceLifecycle:
    """Tests for service lifecycle methods."""

    async def test_initialize_creates_http_client(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should create HTTP client on initialize."""
        assert service._http_client is None

        await service.initialize()

        assert service._http_client is not None
        assert isinstance(service._http_client, httpx.AsyncClient)

        await service.shutdown()

    async def test_shutdown_closes_http_client(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should close HTTP client on shutdown."""
        await service.initialize()
        assert service._http_client is not None

        await service.shutdown()

        assert service._http_client is None


class TestRecipeScraperServiceFetchHtml:
    """Tests for _fetch_html method."""

    async def test_fetch_html_raises_when_not_initialized(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should raise RuntimeError if service not initialized."""
        with pytest.raises(RuntimeError, match="not initialized"):
            await service._fetch_html("https://example.com")

    async def test_fetch_html_raises_timeout_error(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should raise ScrapingTimeoutError on timeout."""
        await service.initialize()
        service._http_client.get = AsyncMock(  # type: ignore[union-attr]
            side_effect=httpx.TimeoutException("timeout")
        )

        with pytest.raises(ScrapingTimeoutError):
            await service._fetch_html("https://example.com")

        await service.shutdown()

    async def test_fetch_html_raises_fetch_error_on_http_error(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should raise ScrapingFetchError on HTTP error."""
        await service.initialize()
        response = MagicMock()
        response.status_code = 404
        service._http_client.get = AsyncMock(  # type: ignore[union-attr]
            side_effect=httpx.HTTPStatusError(
                "Not found", request=MagicMock(), response=response
            )
        )

        with pytest.raises(ScrapingFetchError, match="404"):
            await service._fetch_html("https://example.com")

        await service.shutdown()

    async def test_fetch_html_raises_fetch_error_on_request_error(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should raise ScrapingFetchError on request error."""
        await service.initialize()
        service._http_client.get = AsyncMock(  # type: ignore[union-attr]
            side_effect=httpx.RequestError("Connection failed")
        )

        with pytest.raises(ScrapingFetchError, match="Failed to fetch"):
            await service._fetch_html("https://example.com")

        await service.shutdown()


class TestRecipeScraperServiceExtraction:
    """Tests for recipe extraction methods."""

    async def test_extract_with_recipe_scrapers_returns_recipe(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should return ScrapedRecipe from recipe-scrapers."""
        html = "<html><body>recipe content</body></html>"
        url = "https://allrecipes.com/recipe/123"

        with patch("app.services.scraping.service.scrape_html") as mock_scrape:
            mock_scraper = MagicMock()
            mock_scraper.title.return_value = "Test Recipe"
            mock_scraper.description.return_value = "A test description"
            mock_scraper.yields.return_value = "4 servings"
            mock_scraper.prep_time.return_value = 15
            mock_scraper.cook_time.return_value = 30
            mock_scraper.total_time.return_value = 45
            mock_scraper.ingredients.return_value = ["1 cup flour", "2 eggs"]
            mock_scraper.instructions_list.return_value = ["Mix", "Bake"]
            mock_scraper.image.return_value = "https://example.com/image.jpg"
            mock_scraper.author.return_value = "Test Author"
            mock_scraper.cuisine.return_value = "American"
            mock_scraper.category.return_value = "Dessert"
            mock_scraper.keywords.return_value = "easy,quick"
            mock_scrape.return_value = mock_scraper

            recipe = await service._extract_with_recipe_scrapers(url, html)

            assert recipe is not None
            assert recipe.title == "Test Recipe"
            assert recipe.description == "A test description"
            assert recipe.servings == "4 servings"
            assert recipe.prep_time == 15
            assert recipe.cook_time == 30
            assert recipe.ingredients == ["1 cup flour", "2 eggs"]
            assert recipe.instructions == ["Mix", "Bake"]

    async def test_extract_with_recipe_scrapers_returns_none_for_unsupported(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should return None for unsupported websites."""
        html = "<html><body>recipe content</body></html>"
        url = "https://unsupported-site.com/recipe"

        with patch("app.services.scraping.service.scrape_html") as mock_scrape:
            mock_scrape.side_effect = WebsiteNotImplementedError(url)

            recipe = await service._extract_with_recipe_scrapers(url, html)

            assert recipe is None

    async def test_extract_with_recipe_scrapers_raises_parse_error(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should raise ScrapingParseError on parsing failure."""
        html = "<html><body>bad content</body></html>"
        url = "https://allrecipes.com/recipe/123"

        with patch("app.services.scraping.service.scrape_html") as mock_scrape:
            mock_scrape.side_effect = ValueError("Parse error")

            with pytest.raises(ScrapingParseError):
                await service._extract_with_recipe_scrapers(url, html)


class TestRecipeScraperServiceScrape:
    """Tests for the main scrape method."""

    async def test_scrape_uses_recipe_scrapers_first(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should try recipe-scrapers before JSON-LD."""
        await service.initialize()

        mock_recipe = ScrapedRecipe(
            title="Test Recipe",
            source_url="https://example.com/recipe",
            ingredients=["flour", "eggs"],
            instructions=["mix", "bake"],
        )

        with (
            patch.object(service, "_fetch_html", new_callable=AsyncMock) as mock_fetch,
            patch.object(
                service,
                "_extract_with_recipe_scrapers",
                new_callable=AsyncMock,
            ) as mock_extract,
        ):
            mock_fetch.return_value = "<html>content</html>"
            mock_extract.return_value = mock_recipe

            result = await service.scrape("https://example.com/recipe")

            assert result == mock_recipe
            mock_extract.assert_called_once()

        await service.shutdown()

    async def test_scrape_falls_back_to_jsonld(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should fall back to JSON-LD when recipe-scrapers fails."""
        await service.initialize()

        mock_recipe = ScrapedRecipe(
            title="JSON-LD Recipe",
            source_url="https://example.com/recipe",
            ingredients=["flour"],
            instructions=["bake"],
        )

        with (
            patch.object(service, "_fetch_html", new_callable=AsyncMock) as mock_fetch,
            patch.object(
                service,
                "_extract_with_recipe_scrapers",
                new_callable=AsyncMock,
            ) as mock_scrapers,
            patch.object(
                service, "_extract_with_jsonld", new_callable=AsyncMock
            ) as mock_jsonld,
        ):
            mock_fetch.return_value = "<html>content</html>"
            mock_scrapers.return_value = None  # recipe-scrapers fails
            mock_jsonld.return_value = mock_recipe

            result = await service.scrape("https://example.com/recipe")

            assert result == mock_recipe
            mock_jsonld.assert_called_once()

        await service.shutdown()

    async def test_scrape_raises_not_found_when_all_fail(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should raise RecipeNotFoundError when no extraction works."""
        await service.initialize()

        with (
            patch.object(service, "_fetch_html", new_callable=AsyncMock) as mock_fetch,
            patch.object(
                service,
                "_extract_with_recipe_scrapers",
                new_callable=AsyncMock,
            ) as mock_scrapers,
            patch.object(
                service, "_extract_with_jsonld", new_callable=AsyncMock
            ) as mock_jsonld,
        ):
            mock_fetch.return_value = "<html>content</html>"
            mock_scrapers.return_value = None
            mock_jsonld.return_value = None

            with pytest.raises(RecipeNotFoundError):
                await service.scrape("https://example.com/recipe")

        await service.shutdown()


class TestScrapedRecipeModel:
    """Tests for ScrapedRecipe model."""

    def test_parse_servings_simple_number(self) -> None:
        """Should parse simple number servings."""
        recipe = ScrapedRecipe(
            title="Test",
            source_url="https://example.com",
            servings="4",
        )
        assert recipe.parse_servings() == 4.0

    def test_parse_servings_with_text(self) -> None:
        """Should parse servings with text."""
        recipe = ScrapedRecipe(
            title="Test",
            source_url="https://example.com",
            servings="4 servings",
        )
        assert recipe.parse_servings() == 4.0

    def test_parse_servings_range(self) -> None:
        """Should parse range and take first number."""
        recipe = ScrapedRecipe(
            title="Test",
            source_url="https://example.com",
            servings="4-6",
        )
        assert recipe.parse_servings() == 4.0

    def test_parse_servings_none(self) -> None:
        """Should return None when servings is None."""
        recipe = ScrapedRecipe(
            title="Test",
            source_url="https://example.com",
            servings=None,
        )
        assert recipe.parse_servings() is None

    def test_parse_servings_invalid(self) -> None:
        """Should return None for invalid servings."""
        recipe = ScrapedRecipe(
            title="Test",
            source_url="https://example.com",
            servings="a lot",
        )
        assert recipe.parse_servings() is None


class TestRecipeScraperServiceHelperMethods:
    """Tests for service helper methods."""

    async def test_safe_call_str_field_returns_string(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should return string value from callable."""

        def get_value() -> str:
            return "test value"

        result = service._safe_call_str_field(get_value)
        assert result == "test value"

    async def test_safe_call_str_field_returns_none_for_empty(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should return None for empty string."""

        def get_value() -> str:
            return ""

        result = service._safe_call_str_field(get_value)
        assert result is None

    async def test_safe_call_str_field_converts_non_string(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should convert non-string values to string."""

        def get_value() -> int:
            return 42

        result = service._safe_call_str_field(get_value)
        assert result == "42"

    async def test_safe_call_str_field_returns_none_on_exception(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should return None when callable raises exception."""

        def get_value() -> str:
            msg = "Something went wrong"
            raise ValueError(msg)

        result = service._safe_call_str_field(get_value)
        assert result is None

    async def test_safe_call_str_field_returns_none_for_none(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should return None when callable returns None."""

        def get_value() -> None:
            return None

        result = service._safe_call_str_field(get_value)
        assert result is None

    async def test_safe_call_int_field_returns_int(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should return integer value from callable."""

        def get_value() -> int:
            return 42

        result = service._safe_call_int_field(get_value)
        assert result == 42

    async def test_safe_call_int_field_converts_string(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should convert string to int."""

        def get_value() -> str:
            return "42"

        result = service._safe_call_int_field(get_value)
        assert result == 42

    async def test_safe_call_int_field_returns_none_on_invalid(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should return None for non-convertible values."""

        def get_value() -> str:
            return "not a number"

        result = service._safe_call_int_field(get_value)
        assert result is None

    async def test_safe_call_int_field_returns_none_on_exception(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should return None when callable raises exception."""

        def get_value() -> int:
            msg = "Something went wrong"
            raise ValueError(msg)

        result = service._safe_call_int_field(get_value)
        assert result is None

    async def test_safe_call_int_field_returns_none_for_none(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should return None when callable returns None."""

        def get_value() -> None:
            return None

        result = service._safe_call_int_field(get_value)
        assert result is None

    async def test_safe_call_str_returns_string(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should return string from callable."""

        def get_value() -> str:
            return "test"

        result = service._safe_call_str(get_value)
        assert result == "test"

    async def test_safe_call_str_returns_list(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should return list from callable."""

        def get_value() -> list[str]:
            return ["a", "b", "c"]

        result = service._safe_call_str(get_value)
        assert result == ["a", "b", "c"]

    async def test_safe_call_str_converts_to_string(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should convert other types to string."""

        def get_value() -> int:
            return 42

        result = service._safe_call_str(get_value)
        assert result == "42"

    async def test_safe_call_str_returns_none_on_exception(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should return None when callable raises exception."""

        def get_value() -> str:
            msg = "Error"
            raise ValueError(msg)

        result = service._safe_call_str(get_value)
        assert result is None

    async def test_safe_call_str_returns_none_for_none(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should return None when callable returns None."""

        def get_value() -> None:
            return None

        result = service._safe_call_str(get_value)
        assert result is None

    def test_parse_instructions_handles_none(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should return empty list for None instructions."""
        result = service._parse_instructions(None)
        assert result == []

    def test_parse_instructions_handles_empty_list(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should return empty list for empty instructions."""
        result = service._parse_instructions([])
        assert result == []

    def test_parse_instructions_strips_whitespace(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should strip whitespace from instructions."""
        result = service._parse_instructions(["  Step 1  ", "\n Step 2 \n"])
        assert result == ["Step 1", "Step 2"]

    def test_parse_instructions_filters_empty(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should filter out empty instructions."""
        result = service._parse_instructions(["Step 1", "", "   ", "Step 2"])
        assert result == ["Step 1", "Step 2"]

    def test_parse_keywords_string(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should parse comma-separated string keywords."""
        result = service._parse_keywords("easy, quick, dinner")
        assert result == ["easy", "quick", "dinner"]

    def test_parse_keywords_list(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should parse list keywords."""
        result = service._parse_keywords(["easy", "quick", "dinner"])
        assert result == ["easy", "quick", "dinner"]

    def test_parse_keywords_filters_empty(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should filter out empty keywords."""
        result = service._parse_keywords(["easy", "", "  ", "quick"])
        assert result == ["easy", "quick"]

    def test_parse_keywords_none(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should return empty list for None keywords."""
        result = service._parse_keywords(None)
        assert result == []


class TestRecipeScraperServiceCaching:
    """Tests for caching functionality."""

    @pytest.fixture
    def mock_cache_client(self) -> MagicMock:
        """Create mock Redis cache client."""
        return MagicMock()

    @pytest.fixture
    def service_with_cache(
        self,
        mock_settings: MagicMock,
        mock_cache_client: MagicMock,
    ) -> RecipeScraperService:
        """Create service with cache enabled."""
        mock_settings.scraping.cache_enabled = True
        mock_settings.scraping.cache_ttl = 3600
        with patch(
            "app.services.scraping.service.get_settings",
            return_value=mock_settings,
        ):
            return RecipeScraperService(cache_client=mock_cache_client)

    async def test_scrape_returns_cached_recipe(
        self,
        service_with_cache: RecipeScraperService,
        mock_cache_client: MagicMock,
    ) -> None:
        """Should return cached recipe when available."""
        cached_recipe = ScrapedRecipe(
            title="Cached Recipe",
            source_url="https://example.com/recipe",
            ingredients=["flour"],
            instructions=["bake"],
        )
        mock_cache_client.get = AsyncMock(
            return_value=orjson.dumps(cached_recipe.model_dump())
        )

        await service_with_cache.initialize()

        with patch.object(
            service_with_cache, "_fetch_html", new_callable=AsyncMock
        ) as mock_fetch:
            result = await service_with_cache.scrape("https://example.com/recipe")

            # Should not call fetch since cache hit
            mock_fetch.assert_not_called()
            assert result.title == "Cached Recipe"

        await service_with_cache.shutdown()

    async def test_scrape_skips_cache_when_requested(
        self,
        service_with_cache: RecipeScraperService,
        mock_cache_client: MagicMock,
    ) -> None:
        """Should skip cache when skip_cache=True."""
        await service_with_cache.initialize()

        mock_recipe = ScrapedRecipe(
            title="Fresh Recipe",
            source_url="https://example.com/recipe",
            ingredients=["flour"],
            instructions=["bake"],
        )

        with (
            patch.object(
                service_with_cache, "_fetch_html", new_callable=AsyncMock
            ) as mock_fetch,
            patch.object(
                service_with_cache,
                "_extract_with_recipe_scrapers",
                new_callable=AsyncMock,
            ) as mock_extract,
        ):
            mock_fetch.return_value = "<html>content</html>"
            mock_extract.return_value = mock_recipe
            mock_cache_client.set = AsyncMock()

            result = await service_with_cache.scrape(
                "https://example.com/recipe",
                skip_cache=True,
            )

            # Cache get should not be called when skip_cache=True
            mock_cache_client.get.assert_not_called()
            assert result.title == "Fresh Recipe"

        await service_with_cache.shutdown()

    async def test_scrape_saves_to_cache(
        self,
        service_with_cache: RecipeScraperService,
        mock_cache_client: MagicMock,
    ) -> None:
        """Should save scraped recipe to cache."""
        await service_with_cache.initialize()

        mock_recipe = ScrapedRecipe(
            title="New Recipe",
            source_url="https://example.com/recipe",
            ingredients=["flour"],
            instructions=["bake"],
        )

        mock_cache_client.get = AsyncMock(return_value=None)
        mock_cache_client.set = AsyncMock()

        with (
            patch.object(
                service_with_cache, "_fetch_html", new_callable=AsyncMock
            ) as mock_fetch,
            patch.object(
                service_with_cache,
                "_extract_with_recipe_scrapers",
                new_callable=AsyncMock,
            ) as mock_extract,
        ):
            mock_fetch.return_value = "<html>content</html>"
            mock_extract.return_value = mock_recipe

            result = await service_with_cache.scrape("https://example.com/recipe")

            # Cache should be called to save
            mock_cache_client.set.assert_called_once()
            assert result.title == "New Recipe"

        await service_with_cache.shutdown()

    async def test_cache_read_failure_continues(
        self,
        service_with_cache: RecipeScraperService,
        mock_cache_client: MagicMock,
    ) -> None:
        """Should continue scraping if cache read fails."""
        await service_with_cache.initialize()

        mock_recipe = ScrapedRecipe(
            title="Fresh Recipe",
            source_url="https://example.com/recipe",
            ingredients=["flour"],
            instructions=["bake"],
        )

        # Cache read raises exception
        mock_cache_client.get = AsyncMock(
            side_effect=Exception("Redis connection failed")
        )
        mock_cache_client.set = AsyncMock()

        with (
            patch.object(
                service_with_cache, "_fetch_html", new_callable=AsyncMock
            ) as mock_fetch,
            patch.object(
                service_with_cache,
                "_extract_with_recipe_scrapers",
                new_callable=AsyncMock,
            ) as mock_extract,
        ):
            mock_fetch.return_value = "<html>content</html>"
            mock_extract.return_value = mock_recipe

            # Should not raise, should continue to fetch
            result = await service_with_cache.scrape("https://example.com/recipe")
            assert result.title == "Fresh Recipe"

        await service_with_cache.shutdown()

    async def test_cache_write_failure_continues(
        self,
        service_with_cache: RecipeScraperService,
        mock_cache_client: MagicMock,
    ) -> None:
        """Should continue if cache write fails."""
        await service_with_cache.initialize()

        mock_recipe = ScrapedRecipe(
            title="Fresh Recipe",
            source_url="https://example.com/recipe",
            ingredients=["flour"],
            instructions=["bake"],
        )

        mock_cache_client.get = AsyncMock(return_value=None)
        mock_cache_client.set = AsyncMock(
            side_effect=Exception("Redis connection failed")
        )

        with (
            patch.object(
                service_with_cache, "_fetch_html", new_callable=AsyncMock
            ) as mock_fetch,
            patch.object(
                service_with_cache,
                "_extract_with_recipe_scrapers",
                new_callable=AsyncMock,
            ) as mock_extract,
        ):
            mock_fetch.return_value = "<html>content</html>"
            mock_extract.return_value = mock_recipe

            # Should not raise, should return result despite cache failure
            result = await service_with_cache.scrape("https://example.com/recipe")
            assert result.title == "Fresh Recipe"

        await service_with_cache.shutdown()


class TestRecipeScraperServiceFetchHtmlSuccess:
    """Tests for successful HTML fetching."""

    async def test_fetch_html_returns_content(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should return HTML content on successful fetch."""
        await service.initialize()

        mock_response = MagicMock()
        mock_response.text = "<html><body>Recipe content</body></html>"
        mock_response.raise_for_status = MagicMock()

        service._http_client.get = AsyncMock(return_value=mock_response)  # type: ignore[union-attr]

        result = await service._fetch_html("https://example.com/recipe")

        assert result == "<html><body>Recipe content</body></html>"
        mock_response.raise_for_status.assert_called_once()

        await service.shutdown()


class TestRecipeScraperServiceShutdown:
    """Tests for shutdown edge cases."""

    async def test_shutdown_when_not_initialized(
        self,
        service: RecipeScraperService,
    ) -> None:
        """Should handle shutdown when not initialized."""
        # Should not raise
        await service.shutdown()
        assert service._http_client is None
