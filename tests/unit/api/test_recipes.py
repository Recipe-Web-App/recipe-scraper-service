"""Unit tests for recipes endpoint.

Tests cover:
- Create recipe endpoint
- Error handling for various failure scenarios
- Request/response schema transformations
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import orjson
import pytest
from fastapi import HTTPException

from app.api.dependencies import (
    get_ingredient_parser,
    get_popular_recipes_service,
    get_recipe_management_client,
    get_scraper_service,
)
from app.api.v1.endpoints.recipes import create_recipe, get_popular_recipes
from app.llm.prompts import IngredientUnit as ParsedIngredientUnit
from app.llm.prompts import ParsedIngredient
from app.mappers import build_downstream_recipe_request, build_recipe_response
from app.parsing.exceptions import (
    IngredientParsingError,
)
from app.schemas import CreateRecipeRequest, CreateRecipeResponse
from app.schemas.recipe import (
    PopularRecipe,
    PopularRecipesData,
    RecipeEngagementMetrics,
)
from app.services.recipe_management import RecipeResponse
from app.services.recipe_management.exceptions import (
    RecipeManagementResponseError,
    RecipeManagementUnavailableError,
    RecipeManagementValidationError,
)
from app.services.scraping.exceptions import (
    RecipeNotFoundError,
    ScrapingFetchError,
    ScrapingTimeoutError,
)
from app.services.scraping.models import ScrapedRecipe


pytestmark = pytest.mark.unit


class TestBuildDownstreamRequest:
    """Tests for building downstream request."""

    def test_builds_request_with_ingredients(self) -> None:
        """Should build request with parsed ingredients."""
        scraped = ScrapedRecipe(
            title="Test Recipe",
            description="A test recipe",
            servings="4",
            prep_time=15,
            cook_time=30,
            ingredients=["1 cup flour", "2 eggs"],
            instructions=["Mix ingredients", "Bake at 350F"],
            source_url="https://example.com/recipe",
        )
        parsed_ingredients = [
            ParsedIngredient(
                name="flour",
                quantity=1.0,
                unit=ParsedIngredientUnit.CUP,
            ),
            ParsedIngredient(
                name="eggs",
                quantity=2.0,
                unit=ParsedIngredientUnit.PIECE,
            ),
        ]

        result = build_downstream_recipe_request(scraped, parsed_ingredients)

        assert result.title == "Test Recipe"
        assert result.description == "A test recipe"
        assert result.servings == 4.0
        assert result.preparation_time == 15
        assert result.cooking_time == 30
        assert len(result.ingredients) == 2
        assert len(result.steps) == 2

    def test_defaults_servings_to_one(self) -> None:
        """Should default servings to 1 if not parseable."""
        scraped = ScrapedRecipe(
            title="Test",
            description="Test description",
            servings=None,  # None/unparseable servings
            ingredients=["1 cup flour"],
            instructions=["Mix well"],
            source_url="https://example.com",
        )
        parsed_ingredients = [
            ParsedIngredient(
                name="flour",
                quantity=1.0,
                unit=ParsedIngredientUnit.CUP,
            ),
        ]

        result = build_downstream_recipe_request(scraped, parsed_ingredients)

        assert result.servings == 1.0

    def test_defaults_description_to_empty_string(self) -> None:
        """Should default description to empty string if None."""
        scraped = ScrapedRecipe(
            title="Test",
            description=None,
            servings="4",
            ingredients=["1 cup flour"],
            instructions=["Mix well"],
            source_url="https://example.com",
        )
        parsed_ingredients = [
            ParsedIngredient(
                name="flour",
                quantity=1.0,
                unit=ParsedIngredientUnit.CUP,
            ),
        ]

        result = build_downstream_recipe_request(scraped, parsed_ingredients)

        assert result.description == ""


class TestBuildResponse:
    """Tests for building endpoint response."""

    def test_builds_response_with_recipe(self) -> None:
        """Should build response with recipe data."""
        downstream = RecipeResponse(id=123, title="Test Recipe", slug="test-recipe")
        scraped = ScrapedRecipe(
            title="Test Recipe",
            description="A test recipe",
            servings="4",
            prep_time=15,
            cook_time=30,
            ingredients=["1 cup flour"],
            instructions=["Mix ingredients"],
            source_url="https://example.com/recipe",
        )
        parsed = [
            ParsedIngredient(
                name="flour",
                quantity=1.0,
                unit=ParsedIngredientUnit.CUP,
            ),
        ]

        result = build_recipe_response(downstream, scraped, parsed)

        assert isinstance(result, CreateRecipeResponse)
        assert result.recipe.recipe_id == 123
        assert result.recipe.title == "Test Recipe"
        assert result.recipe.origin_url == "https://example.com/recipe"
        assert len(result.recipe.ingredients) == 1
        assert len(result.recipe.steps) == 1


class TestGetScraperService:
    """Tests for scraper service dependency."""

    @pytest.mark.asyncio
    async def test_returns_service_from_app_state(self) -> None:
        """Should return service from app state."""
        mock_request = MagicMock()
        mock_service = MagicMock()
        mock_request.app.state.scraper_service = mock_service

        result = await get_scraper_service(mock_request)

        assert result is mock_service

    @pytest.mark.asyncio
    async def test_raises_503_when_service_not_available(self) -> None:
        """Should raise 503 when service not in app state."""
        mock_request = MagicMock()
        mock_request.app.state.scraper_service = None

        with pytest.raises(HTTPException) as exc_info:
            await get_scraper_service(mock_request)

        assert exc_info.value.status_code == 503


class TestGetRecipeManagementClient:
    """Tests for recipe management client dependency."""

    @pytest.mark.asyncio
    async def test_returns_client_from_app_state(self) -> None:
        """Should return client from app state."""
        mock_request = MagicMock()
        mock_client = MagicMock()
        mock_request.app.state.recipe_management_client = mock_client

        result = await get_recipe_management_client(mock_request)

        assert result is mock_client

    @pytest.mark.asyncio
    async def test_raises_503_when_client_not_available(self) -> None:
        """Should raise 503 when client not in app state."""
        mock_request = MagicMock()
        mock_request.app.state.recipe_management_client = None

        with pytest.raises(HTTPException) as exc_info:
            await get_recipe_management_client(mock_request)

        assert exc_info.value.status_code == 503


class TestGetIngredientParser:
    """Tests for ingredient parser dependency."""

    @pytest.mark.asyncio
    async def test_returns_parser_with_llm_client(self) -> None:
        """Should return parser when LLM client available."""
        mock_llm = MagicMock()

        with patch(
            "app.api.dependencies.get_llm_client",
            return_value=mock_llm,
        ):
            result = await get_ingredient_parser()

            assert result is not None

    @pytest.mark.asyncio
    async def test_raises_503_when_llm_not_available(self) -> None:
        """Should raise 503 when LLM client not available."""
        with patch(
            "app.api.dependencies.get_llm_client",
            side_effect=RuntimeError("LLM not available"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_ingredient_parser()

            assert exc_info.value.status_code == 503


class TestCreateRecipeEndpoint:
    """Tests for create_recipe endpoint."""

    @pytest.fixture
    def mock_user(self) -> MagicMock:
        """Create a mock authenticated user."""
        user = MagicMock()
        user.id = "user-123"
        return user

    @pytest.fixture
    def mock_scraper_service(self) -> MagicMock:
        """Create a mock scraper service."""
        return MagicMock()

    @pytest.fixture
    def mock_recipe_client(self) -> MagicMock:
        """Create a mock recipe client."""
        return MagicMock()

    @pytest.fixture
    def mock_parser(self) -> MagicMock:
        """Create a mock ingredient parser."""
        return MagicMock()

    @pytest.fixture
    def mock_request(self) -> MagicMock:
        """Create a mock HTTP request."""
        request = MagicMock()
        request.headers.get.return_value = "Bearer test-token"
        return request

    @pytest.fixture
    def sample_scraped_recipe(self) -> ScrapedRecipe:
        """Create a sample scraped recipe."""
        return ScrapedRecipe(
            title="Chocolate Chip Cookies",
            description="Delicious homemade cookies",
            servings="24",
            prep_time=15,
            cook_time=12,
            ingredients=["2 cups flour", "1 cup sugar"],
            instructions=["Mix ingredients", "Bake at 375F"],
            source_url="https://example.com/cookies",
        )

    @pytest.fixture
    def sample_parsed_ingredients(self) -> list[ParsedIngredient]:
        """Create sample parsed ingredients."""
        return [
            ParsedIngredient(
                name="flour",
                quantity=2.0,
                unit=ParsedIngredientUnit.CUP,
            ),
            ParsedIngredient(
                name="sugar",
                quantity=1.0,
                unit=ParsedIngredientUnit.CUP,
            ),
        ]

    @pytest.mark.asyncio
    async def test_creates_recipe_successfully(
        self,
        mock_user: MagicMock,
        mock_scraper_service: MagicMock,
        mock_recipe_client: MagicMock,
        mock_parser: MagicMock,
        mock_request: MagicMock,
        sample_scraped_recipe: ScrapedRecipe,
        sample_parsed_ingredients: list[ParsedIngredient],
    ) -> None:
        """Should create recipe successfully with all steps."""
        # Setup mocks
        mock_scraper_service.scrape = AsyncMock(return_value=sample_scraped_recipe)
        mock_parser.parse_batch = AsyncMock(return_value=sample_parsed_ingredients)
        mock_recipe_client.create_recipe = AsyncMock(
            return_value=RecipeResponse(
                id=123,
                title="Chocolate Chip Cookies",
                slug="chocolate-chip-cookies",
            )
        )

        request_body = CreateRecipeRequest.model_validate(
            {
                "recipeUrl": "https://example.com/cookies",
            }
        )

        result = await create_recipe(
            request_body=request_body,
            user=mock_user,
            scraper_service=mock_scraper_service,
            recipe_client=mock_recipe_client,
            parser=mock_parser,
            request=mock_request,
        )

        assert result.recipe.recipe_id == 123
        assert result.recipe.title == "Chocolate Chip Cookies"
        mock_scraper_service.scrape.assert_called_once()
        mock_parser.parse_batch.assert_called_once()
        mock_recipe_client.create_recipe.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_400_when_recipe_not_found(
        self,
        mock_user: MagicMock,
        mock_scraper_service: MagicMock,
        mock_recipe_client: MagicMock,
        mock_parser: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        """Should raise 400 when no recipe found at URL."""
        mock_scraper_service.scrape = AsyncMock(
            side_effect=RecipeNotFoundError("No recipe found")
        )

        request_body = CreateRecipeRequest.model_validate(
            {
                "recipeUrl": "https://example.com/not-a-recipe",
            }
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_recipe(
                request_body=request_body,
                user=mock_user,
                scraper_service=mock_scraper_service,
                recipe_client=mock_recipe_client,
                parser=mock_parser,
                request=mock_request,
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "RECIPE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_raises_504_when_scraping_times_out(
        self,
        mock_user: MagicMock,
        mock_scraper_service: MagicMock,
        mock_recipe_client: MagicMock,
        mock_parser: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        """Should raise 504 when scraping times out."""
        mock_scraper_service.scrape = AsyncMock(
            side_effect=ScrapingTimeoutError("Timeout")
        )

        request_body = CreateRecipeRequest.model_validate(
            {
                "recipeUrl": "https://slow-site.com/recipe",
            }
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_recipe(
                request_body=request_body,
                user=mock_user,
                scraper_service=mock_scraper_service,
                recipe_client=mock_recipe_client,
                parser=mock_parser,
                request=mock_request,
            )

        assert exc_info.value.status_code == 504
        assert exc_info.value.detail["error"] == "SCRAPING_TIMEOUT"

    @pytest.mark.asyncio
    async def test_raises_400_when_fetch_fails(
        self,
        mock_user: MagicMock,
        mock_scraper_service: MagicMock,
        mock_recipe_client: MagicMock,
        mock_parser: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        """Should raise 400 when URL fetch fails."""
        mock_scraper_service.scrape = AsyncMock(
            side_effect=ScrapingFetchError("HTTP 404")
        )

        request_body = CreateRecipeRequest.model_validate(
            {
                "recipeUrl": "https://broken.com/recipe",
            }
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_recipe(
                request_body=request_body,
                user=mock_user,
                scraper_service=mock_scraper_service,
                recipe_client=mock_recipe_client,
                parser=mock_parser,
                request=mock_request,
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "INVALID_RECIPE_URL"

    @pytest.mark.asyncio
    async def test_raises_500_when_ingredient_parsing_fails(
        self,
        mock_user: MagicMock,
        mock_scraper_service: MagicMock,
        mock_recipe_client: MagicMock,
        mock_parser: MagicMock,
        mock_request: MagicMock,
        sample_scraped_recipe: ScrapedRecipe,
    ) -> None:
        """Should raise 500 when ingredient parsing fails."""
        mock_scraper_service.scrape = AsyncMock(return_value=sample_scraped_recipe)
        mock_parser.parse_batch = AsyncMock(
            side_effect=IngredientParsingError("LLM failed")
        )

        request_body = CreateRecipeRequest.model_validate(
            {
                "recipeUrl": "https://example.com/cookies",
            }
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_recipe(
                request_body=request_body,
                user=mock_user,
                scraper_service=mock_scraper_service,
                recipe_client=mock_recipe_client,
                parser=mock_parser,
                request=mock_request,
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail["error"] == "INGREDIENT_PARSING_ERROR"

    @pytest.mark.asyncio
    async def test_raises_422_when_downstream_validation_fails(
        self,
        mock_user: MagicMock,
        mock_scraper_service: MagicMock,
        mock_recipe_client: MagicMock,
        mock_parser: MagicMock,
        mock_request: MagicMock,
        sample_scraped_recipe: ScrapedRecipe,
        sample_parsed_ingredients: list[ParsedIngredient],
    ) -> None:
        """Should raise 422 when downstream validation fails."""
        mock_scraper_service.scrape = AsyncMock(return_value=sample_scraped_recipe)
        mock_parser.parse_batch = AsyncMock(return_value=sample_parsed_ingredients)
        mock_recipe_client.create_recipe = AsyncMock(
            side_effect=RecipeManagementValidationError("Title too short")
        )

        request_body = CreateRecipeRequest.model_validate(
            {
                "recipeUrl": "https://example.com/cookies",
            }
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_recipe(
                request_body=request_body,
                user=mock_user,
                scraper_service=mock_scraper_service,
                recipe_client=mock_recipe_client,
                parser=mock_parser,
                request=mock_request,
            )

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["error"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_raises_503_when_downstream_unavailable(
        self,
        mock_user: MagicMock,
        mock_scraper_service: MagicMock,
        mock_recipe_client: MagicMock,
        mock_parser: MagicMock,
        mock_request: MagicMock,
        sample_scraped_recipe: ScrapedRecipe,
        sample_parsed_ingredients: list[ParsedIngredient],
    ) -> None:
        """Should raise 503 when downstream service unavailable."""
        mock_scraper_service.scrape = AsyncMock(return_value=sample_scraped_recipe)
        mock_parser.parse_batch = AsyncMock(return_value=sample_parsed_ingredients)
        mock_recipe_client.create_recipe = AsyncMock(
            side_effect=RecipeManagementUnavailableError("Connection refused")
        )

        request_body = CreateRecipeRequest.model_validate(
            {
                "recipeUrl": "https://example.com/cookies",
            }
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_recipe(
                request_body=request_body,
                user=mock_user,
                scraper_service=mock_scraper_service,
                recipe_client=mock_recipe_client,
                parser=mock_parser,
                request=mock_request,
            )

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["error"] == "SERVICE_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_raises_502_when_downstream_returns_error(
        self,
        mock_user: MagicMock,
        mock_scraper_service: MagicMock,
        mock_recipe_client: MagicMock,
        mock_parser: MagicMock,
        mock_request: MagicMock,
        sample_scraped_recipe: ScrapedRecipe,
        sample_parsed_ingredients: list[ParsedIngredient],
    ) -> None:
        """Should raise 502 when downstream returns error."""
        mock_scraper_service.scrape = AsyncMock(return_value=sample_scraped_recipe)
        mock_parser.parse_batch = AsyncMock(return_value=sample_parsed_ingredients)
        mock_recipe_client.create_recipe = AsyncMock(
            side_effect=RecipeManagementResponseError(500, "Internal error")
        )

        request_body = CreateRecipeRequest.model_validate(
            {
                "recipeUrl": "https://example.com/cookies",
            }
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_recipe(
                request_body=request_body,
                user=mock_user,
                scraper_service=mock_scraper_service,
                recipe_client=mock_recipe_client,
                parser=mock_parser,
                request=mock_request,
            )

        assert exc_info.value.status_code == 502
        assert exc_info.value.detail["error"] == "DOWNSTREAM_ERROR"


class TestCreateRecipeRequestSchema:
    """Tests for request schema validation."""

    def test_accepts_valid_url(self) -> None:
        """Should accept a valid recipe URL."""
        request = CreateRecipeRequest.model_validate(
            {
                "recipeUrl": "https://example.com/recipe",
            }
        )
        assert str(request.recipe_url) == "https://example.com/recipe"

    def test_accepts_url_with_path(self) -> None:
        """Should accept URL with complex path."""
        request = CreateRecipeRequest.model_validate(
            {
                "recipeUrl": "https://www.allrecipes.com/recipe/10813/cookies/",
            }
        )
        assert "allrecipes.com" in str(request.recipe_url)

    def test_supports_alias_and_python_name(self) -> None:
        """Should support both alias and Python name."""
        # Test using alias
        request1 = CreateRecipeRequest.model_validate(
            {
                "recipeUrl": "https://example.com/recipe1",
            }
        )
        assert request1.recipe_url is not None

        # Test using Python name with populate_by_name
        request2 = CreateRecipeRequest(
            recipe_url="https://example.com/recipe2",  # type: ignore[arg-type]
        )
        assert request2.recipe_url is not None


# =============================================================================
# Popular Recipes Endpoint Tests
# =============================================================================


class TestGetPopularRecipesEndpoint:
    """Tests for get_popular_recipes endpoint.

    The endpoint now reads directly from cache and returns 503 if cache is empty.
    """

    @pytest.fixture
    def mock_cache_client(self) -> AsyncMock:
        """Create a mock Redis cache client."""
        return AsyncMock()

    @pytest.fixture
    def sample_cached_data(self) -> PopularRecipesData:
        """Create sample cached data."""
        return PopularRecipesData(
            recipes=[
                PopularRecipe(
                    recipe_name="Recipe 1",
                    url="https://test.com/recipe1",
                    source="TestSource",
                    raw_rank=1,
                    metrics=RecipeEngagementMetrics(),
                    normalized_score=0.95,
                ),
                PopularRecipe(
                    recipe_name="Recipe 2",
                    url="https://test.com/recipe2",
                    source="TestSource",
                    raw_rank=2,
                    metrics=RecipeEngagementMetrics(),
                    normalized_score=0.90,
                ),
            ],
            total_count=100,
            sources_fetched=["TestSource"],
        )

    @pytest.mark.asyncio
    async def test_returns_popular_recipes_from_cache(
        self,
        mock_cache_client: AsyncMock,
        sample_cached_data: PopularRecipesData,
    ) -> None:
        """Should return list of popular recipes from cache."""
        # Setup mock to return cached data
        mock_cache_client.get = AsyncMock(
            return_value=orjson.dumps(sample_cached_data.model_dump())
        )

        with patch("app.api.v1.endpoints.recipes.get_settings") as mock_settings:
            mock_settings.return_value.scraping.popular_recipes.cache_key = "test"
            response = await get_popular_recipes(
                cache_client=mock_cache_client,
                limit=50,
                offset=0,
                count_only=False,
            )

        assert len(response.recipes) == 2
        assert response.count == 100
        assert response.limit == 50
        assert response.offset == 0
        assert response.recipes[0].recipe_name == "Recipe 1"
        assert response.recipes[0].url == "https://test.com/recipe1"

    @pytest.mark.asyncio
    async def test_returns_count_only(
        self,
        mock_cache_client: AsyncMock,
        sample_cached_data: PopularRecipesData,
    ) -> None:
        """Should return only count when count_only is True."""
        mock_cache_client.get = AsyncMock(
            return_value=orjson.dumps(sample_cached_data.model_dump())
        )

        with patch("app.api.v1.endpoints.recipes.get_settings") as mock_settings:
            mock_settings.return_value.scraping.popular_recipes.cache_key = "test"
            response = await get_popular_recipes(
                cache_client=mock_cache_client,
                limit=50,
                offset=0,
                count_only=True,
            )

        assert response.recipes == []
        assert response.count == 100

    @pytest.mark.asyncio
    async def test_applies_pagination_parameters(
        self,
        mock_cache_client: AsyncMock,
        sample_cached_data: PopularRecipesData,
    ) -> None:
        """Should apply pagination to cached recipes."""
        mock_cache_client.get = AsyncMock(
            return_value=orjson.dumps(sample_cached_data.model_dump())
        )

        with patch("app.api.v1.endpoints.recipes.get_settings") as mock_settings:
            mock_settings.return_value.scraping.popular_recipes.cache_key = "test"
            response = await get_popular_recipes(
                cache_client=mock_cache_client,
                limit=1,
                offset=1,
                count_only=False,
            )

        # Should return second recipe only (offset=1, limit=1)
        assert len(response.recipes) == 1
        assert response.recipes[0].recipe_name == "Recipe 2"
        assert response.limit == 1
        assert response.offset == 1

    @pytest.mark.asyncio
    async def test_converts_to_web_recipe_format(
        self, mock_cache_client: AsyncMock
    ) -> None:
        """Should convert PopularRecipe to WebRecipe for response."""
        cached_data = PopularRecipesData(
            recipes=[
                PopularRecipe(
                    recipe_name="Full Recipe",
                    url="https://test.com/full",
                    source="TestSource",
                    raw_rank=1,
                    metrics=RecipeEngagementMetrics(
                        rating=4.5,
                        rating_count=1000,
                        favorites=500,
                        reviews=200,
                    ),
                    normalized_score=0.95,
                ),
            ],
            total_count=1,
        )
        mock_cache_client.get = AsyncMock(
            return_value=orjson.dumps(cached_data.model_dump())
        )

        with patch("app.api.v1.endpoints.recipes.get_settings") as mock_settings:
            mock_settings.return_value.scraping.popular_recipes.cache_key = "test"
            response = await get_popular_recipes(
                cache_client=mock_cache_client,
                limit=50,
                offset=0,
                count_only=False,
            )

        # WebRecipe should only have recipe_name and url
        web_recipe = response.recipes[0]
        assert web_recipe.recipe_name == "Full Recipe"
        assert web_recipe.url == "https://test.com/full"
        # Should not have internal fields
        assert not hasattr(web_recipe, "source")
        assert not hasattr(web_recipe, "raw_rank")
        assert not hasattr(web_recipe, "metrics")
        assert not hasattr(web_recipe, "normalized_score")

    @pytest.mark.asyncio
    async def test_returns_503_on_cache_miss(
        self, mock_cache_client: AsyncMock
    ) -> None:
        """Should return 503 with Retry-After when cache is empty."""
        mock_cache_client.get = AsyncMock(return_value=None)

        with (
            patch("app.api.v1.endpoints.recipes.get_settings") as mock_settings,
            patch(
                "app.api.v1.endpoints.recipes.enqueue_popular_recipes_refresh"
            ) as mock_enqueue,
        ):
            mock_settings.return_value.scraping.popular_recipes.cache_key = "test"
            mock_enqueue.return_value = None

            response = await get_popular_recipes(
                cache_client=mock_cache_client,
                limit=50,
                offset=0,
                count_only=False,
            )

        # Should be a JSONResponse with 503 status
        assert response.status_code == 503
        assert response.headers.get("retry-after") == "60"
        mock_enqueue.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_503_when_no_cache_client(self) -> None:
        """Should return 503 when cache client is None."""
        with (
            patch("app.api.v1.endpoints.recipes.get_settings") as mock_settings,
            patch(
                "app.api.v1.endpoints.recipes.enqueue_popular_recipes_refresh"
            ) as mock_enqueue,
        ):
            mock_settings.return_value.scraping.popular_recipes.cache_key = "test"
            mock_enqueue.return_value = None

            response = await get_popular_recipes(
                cache_client=None,
                limit=50,
                offset=0,
                count_only=False,
            )

        assert response.status_code == 503
        mock_enqueue.assert_called_once()


class TestGetPopularRecipesServiceDependency:
    """Tests for popular recipes service dependency."""

    @pytest.mark.asyncio
    async def test_returns_service_from_app_state(self) -> None:
        """Should return service from app state."""
        mock_service = MagicMock()
        mock_request = MagicMock()
        mock_request.app.state.popular_recipes_service = mock_service

        result = await get_popular_recipes_service(mock_request)

        assert result is mock_service

    @pytest.mark.asyncio
    async def test_raises_503_when_service_not_available(self) -> None:
        """Should raise 503 when service not in app state."""
        mock_request = MagicMock()
        mock_request.app.state.popular_recipes_service = None

        with pytest.raises(HTTPException) as exc_info:
            await get_popular_recipes_service(mock_request)

        assert exc_info.value.status_code == 503
        assert "Popular recipes service" in exc_info.value.detail
