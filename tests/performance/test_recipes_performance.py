"""Performance benchmarks for recipes endpoint.

Benchmarks cover:
- Recipe creation endpoint response time
- Throughput under load
- Response parsing overhead
- Isolated scraping layer performance
- Isolated LLM parsing layer performance

Note: Uses synchronous HTTP client to avoid event loop
conflicts with pytest-benchmark.

All external dependencies (scraper, LLM, downstream service) are mocked
via FastAPI dependency overrides for isolated performance measurement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.dependencies import (
    get_ingredient_parser,
    get_recipe_management_client,
    get_scraper_service,
)
from app.auth.dependencies import CurrentUser, get_current_user
from app.llm.prompts import ParsedIngredient
from app.llm.prompts.ingredient_parsing import IngredientUnit
from app.parsing.ingredient import IngredientParser
from app.services.recipe_management.schemas import RecipeResponse
from app.services.scraping.models import ScrapedRecipe


if TYPE_CHECKING:
    from collections.abc import Generator

    from fastapi import FastAPI
    from pytest_benchmark.fixture import BenchmarkFixture
    from starlette.testclient import TestClient


pytestmark = pytest.mark.performance


# --- Test Fixtures ---


MOCK_USER = CurrentUser(
    id="perf-test-user",
    roles=["user"],
    permissions=["recipe:create"],
)


@pytest.fixture
def scraped_recipe() -> ScrapedRecipe:
    """Create a sample scraped recipe for benchmarks."""
    return ScrapedRecipe(
        title="Benchmark Chocolate Chip Cookies",
        description="Classic chocolate chip cookies for performance testing",
        servings="24 cookies",
        prep_time=15,
        cook_time=12,
        total_time=27,
        ingredients=[
            "2 cups all-purpose flour",
            "1 tsp baking soda",
            "1 cup butter, softened",
            "1 cup sugar",
            "2 eggs",
            "2 cups chocolate chips",
        ],
        instructions=[
            "Preheat oven to 375°F.",
            "Mix flour and baking soda.",
            "Cream butter and sugar.",
            "Add eggs and mix well.",
            "Combine wet and dry ingredients.",
            "Fold in chocolate chips.",
            "Bake for 10-12 minutes.",
        ],
        image_url="https://example.com/cookies.jpg",
        source_url="https://example.com/recipes/cookies",
        author="Benchmark Chef",
        cuisine="American",
        category="Dessert",
        keywords=["cookies", "chocolate", "baking"],
        yields="24 cookies",
    )


@pytest.fixture
def parsed_ingredients() -> list[ParsedIngredient]:
    """Create sample parsed ingredients for benchmarks."""
    return [
        ParsedIngredient(
            name="all-purpose flour",
            quantity=2.0,
            unit=IngredientUnit.CUP,
            is_optional=False,
            notes=None,
        ),
        ParsedIngredient(
            name="baking soda",
            quantity=1.0,
            unit=IngredientUnit.TSP,
            is_optional=False,
            notes=None,
        ),
        ParsedIngredient(
            name="butter",
            quantity=1.0,
            unit=IngredientUnit.CUP,
            is_optional=False,
            notes="softened",
        ),
        ParsedIngredient(
            name="sugar",
            quantity=1.0,
            unit=IngredientUnit.CUP,
            is_optional=False,
            notes=None,
        ),
        ParsedIngredient(
            name="eggs",
            quantity=2.0,
            unit=IngredientUnit.UNIT,
            is_optional=False,
            notes=None,
        ),
        ParsedIngredient(
            name="chocolate chips",
            quantity=2.0,
            unit=IngredientUnit.CUP,
            is_optional=False,
            notes=None,
        ),
    ]


@pytest.fixture
def downstream_response() -> RecipeResponse:
    """Create sample downstream service response for benchmarks."""
    return RecipeResponse(
        id=42,
        title="Benchmark Chocolate Chip Cookies",
    )


@pytest.fixture
def mock_scraper_service(scraped_recipe: ScrapedRecipe) -> MagicMock:
    """Create mock scraper service for benchmarks."""
    mock = MagicMock()
    # Use AsyncMock for async methods that will be awaited
    mock.scrape = AsyncMock(return_value=scraped_recipe)
    mock.initialize = AsyncMock(return_value=None)
    mock.shutdown = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_recipe_client(downstream_response: RecipeResponse) -> MagicMock:
    """Create mock recipe management client for benchmarks."""
    mock = MagicMock()
    # Use AsyncMock for async methods that will be awaited
    mock.create_recipe = AsyncMock(return_value=downstream_response)
    mock.initialize = AsyncMock(return_value=None)
    mock.shutdown = AsyncMock(return_value=None)
    mock.base_url = "http://mock-recipe-service"
    return mock


@pytest.fixture
def mock_parser(parsed_ingredients: list[ParsedIngredient]) -> MagicMock:
    """Create mock ingredient parser for benchmarks."""
    mock = MagicMock(spec=IngredientParser)
    # Use AsyncMock for async methods that will be awaited
    mock.parse_batch = AsyncMock(return_value=parsed_ingredients)
    return mock


@pytest.fixture
def perf_client(
    app: FastAPI,
    sync_client: TestClient,
    mock_scraper_service: MagicMock,
    mock_recipe_client: MagicMock,
    mock_parser: MagicMock,
) -> Generator[TestClient]:
    """Create sync client with all services mocked for performance tests."""
    # Override dependencies with sync-compatible mocks
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_scraper_service] = lambda: mock_scraper_service
    app.dependency_overrides[get_recipe_management_client] = lambda: mock_recipe_client
    app.dependency_overrides[get_ingredient_parser] = lambda: mock_parser

    yield sync_client

    # Clean up dependency overrides
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_scraper_service, None)
    app.dependency_overrides.pop(get_recipe_management_client, None)
    app.dependency_overrides.pop(get_ingredient_parser, None)


# --- Benchmark Tests ---


class TestRecipesEndpointBenchmarks:
    """Benchmarks for POST /recipes endpoint performance."""

    def test_recipes_endpoint_response_time(
        self,
        benchmark: BenchmarkFixture,
        perf_client: TestClient,
    ) -> None:
        """Benchmark recipe creation endpoint response time."""

        def create_recipe() -> dict[str, Any]:
            response = perf_client.post(
                "/api/v1/recipe-scraper/recipes",
                json={"recipeUrl": "https://example.com/recipes/cookies"},
            )
            result: dict[str, Any] = response.json()
            return result

        result = benchmark(create_recipe)
        assert "recipe" in result
        assert result["recipe"]["recipeId"] == 42

    def test_recipes_endpoint_status_code(
        self,
        benchmark: BenchmarkFixture,
        perf_client: TestClient,
    ) -> None:
        """Benchmark recipe creation endpoint status code check."""

        def check_status() -> int:
            response = perf_client.post(
                "/api/v1/recipe-scraper/recipes",
                json={"recipeUrl": "https://example.com/recipes/cookies"},
            )
            return response.status_code

        result = benchmark(check_status)
        assert result == 201

    def test_recipes_endpoint_throughput(
        self,
        benchmark: BenchmarkFixture,
        perf_client: TestClient,
    ) -> None:
        """Benchmark recipe endpoint for high throughput scenarios."""

        def create_multiple() -> int:
            success_count = 0
            for _ in range(10):
                response = perf_client.post(
                    "/api/v1/recipe-scraper/recipes",
                    json={"recipeUrl": "https://example.com/recipes/cookies"},
                )
                if response.status_code == 201:
                    success_count += 1
            return success_count

        result = benchmark(create_multiple)
        assert result == 10

    def test_recipes_endpoint_json_parsing(
        self,
        benchmark: BenchmarkFixture,
        perf_client: TestClient,
    ) -> None:
        """Benchmark JSON parsing overhead for recipe response."""

        def create_and_parse() -> tuple[int, str, int]:
            response = perf_client.post(
                "/api/v1/recipe-scraper/recipes",
                json={"recipeUrl": "https://example.com/recipes/cookies"},
            )
            data = response.json()
            recipe = data["recipe"]
            return recipe["recipeId"], recipe["title"], len(recipe["ingredients"])

        result = benchmark(create_and_parse)
        recipe_id, title, ingredient_count = result
        assert recipe_id == 42
        assert title == "Benchmark Chocolate Chip Cookies"
        assert ingredient_count == 6

    def test_recipes_endpoint_headers_check(
        self,
        benchmark: BenchmarkFixture,
        perf_client: TestClient,
    ) -> None:
        """Benchmark recipe endpoint with header verification."""

        def create_with_headers() -> tuple[int, bool, bool]:
            response = perf_client.post(
                "/api/v1/recipe-scraper/recipes",
                json={"recipeUrl": "https://example.com/recipes/cookies"},
            )
            has_request_id = "x-request-id" in response.headers
            has_process_time = "x-process-time" in response.headers
            return response.status_code, has_request_id, has_process_time

        result = benchmark(create_with_headers)
        status_code, has_request_id, has_process_time = result
        assert status_code == 201
        assert has_request_id
        assert has_process_time

    def test_recipes_endpoint_response_structure(
        self,
        benchmark: BenchmarkFixture,
        perf_client: TestClient,
    ) -> None:
        """Benchmark full response structure validation."""

        def validate_structure() -> bool:
            response = perf_client.post(
                "/api/v1/recipe-scraper/recipes",
                json={"recipeUrl": "https://example.com/recipes/cookies"},
            )
            data = response.json()
            recipe = data["recipe"]

            # Validate all expected fields
            has_all_fields = all(
                [
                    "recipeId" in recipe,
                    "title" in recipe,
                    "description" in recipe,
                    "ingredients" in recipe,
                    "steps" in recipe,
                ]
            )

            # Validate nested structures
            has_valid_ingredients = all(
                "name" in ing and "quantity" in ing for ing in recipe["ingredients"]
            )
            has_valid_steps = all(
                "stepNumber" in step and "instruction" in step
                for step in recipe["steps"]
            )

            return has_all_fields and has_valid_ingredients and has_valid_steps

        result = benchmark(validate_structure)
        assert result is True


class TestRecipesLayerBenchmarks:
    """Benchmarks for isolated layer performance."""

    def test_scraped_recipe_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark ScrapedRecipe model instantiation overhead."""

        def create_scraped_recipe() -> ScrapedRecipe:
            return ScrapedRecipe(
                title="Test Cookies",
                description="Delicious cookies",
                servings="24 cookies",
                prep_time=15,
                cook_time=12,
                ingredients=["2 cups flour", "1 cup sugar", "2 eggs"],
                instructions=["Mix", "Bake", "Cool"],
                source_url="https://example.com/recipe",
            )

        result = benchmark(create_scraped_recipe)
        assert result.title == "Test Cookies"

    def test_parsed_ingredient_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark ParsedIngredient model instantiation overhead."""

        def create_parsed_ingredients() -> list[ParsedIngredient]:
            return [
                ParsedIngredient(
                    name="flour",
                    quantity=2.0,
                    unit=IngredientUnit.CUP,
                    is_optional=False,
                    notes=None,
                ),
                ParsedIngredient(
                    name="sugar",
                    quantity=1.0,
                    unit=IngredientUnit.CUP,
                    is_optional=False,
                    notes=None,
                ),
                ParsedIngredient(
                    name="eggs",
                    quantity=2.0,
                    unit=IngredientUnit.UNIT,
                    is_optional=False,
                    notes=None,
                ),
            ]

        result = benchmark(create_parsed_ingredients)
        assert len(result) == 3

    def test_recipe_response_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark RecipeResponse model instantiation overhead."""

        def create_response() -> RecipeResponse:
            return RecipeResponse(
                id=42,
                title="Test Cookies",
            )

        result = benchmark(create_response)
        assert result.id == 42
