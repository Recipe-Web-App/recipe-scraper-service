"""Unit tests for recipes endpoint.

Tests cover:
- Create recipe endpoint
- Error handling for various failure scenarios
- Request/response schema transformations
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.dependencies import (
    get_ingredient_parser,
    get_recipe_management_client,
    get_scraper_service,
)
from app.api.v1.endpoints.recipes import (
    _build_downstream_request,
    _build_response,
    _map_unit,
    create_recipe,
)
from app.llm.prompts import IngredientUnit as ParsedIngredientUnit
from app.llm.prompts import ParsedIngredient
from app.parsing.exceptions import (
    IngredientParsingError,
)
from app.schemas import CreateRecipeRequest, CreateRecipeResponse
from app.services.recipe_management import IngredientUnit, RecipeResponse
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


class TestUnitMapping:
    """Tests for unit mapping function."""

    def test_maps_cup_unit(self) -> None:
        """Should map CUP unit correctly."""
        result = _map_unit(ParsedIngredientUnit.CUP)
        assert result == IngredientUnit.CUP

    def test_maps_tsp_unit(self) -> None:
        """Should map TSP unit correctly."""
        result = _map_unit(ParsedIngredientUnit.TSP)
        assert result == IngredientUnit.TSP

    def test_maps_piece_unit(self) -> None:
        """Should map PIECE unit correctly."""
        result = _map_unit(ParsedIngredientUnit.PIECE)
        assert result == IngredientUnit.PIECE


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

        result = _build_downstream_request(scraped, parsed_ingredients)

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

        result = _build_downstream_request(scraped, parsed_ingredients)

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

        result = _build_downstream_request(scraped, parsed_ingredients)

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

        result = _build_response(downstream, scraped, parsed)

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
