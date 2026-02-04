"""Performance benchmarks for recipe pairings endpoint.

Benchmarks cover:
- Pairing lookup response time
- Endpoint throughput
- JSON response parsing overhead
- Model instantiation performance
- Pagination performance

Note: Uses synchronous HTTP client to avoid event loop
conflicts with pytest-benchmark.

All external dependencies (LLM, cache, recipe client) are mocked
via FastAPI dependency overrides for isolated performance measurement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.dependencies import get_pairings_service, get_recipe_management_client
from app.auth.dependencies import CurrentUser, get_current_user
from app.llm.prompts.pairings import PairingListResult, PairingResult
from app.schemas.ingredient import WebRecipe
from app.schemas.recommendations import PairingSuggestionsResponse
from app.services.recipe_management.schemas import (
    RecipeDetailResponse,
    RecipeIngredientResponse,
)


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
    permissions=["recipe:read"],
)


@pytest.fixture
def sample_pairing_result() -> PairingSuggestionsResponse:
    """Create sample pairing response for benchmarks."""
    return PairingSuggestionsResponse(
        recipe_id=123,
        pairing_suggestions=[
            WebRecipe(
                recipe_name="Garlic Bread",
                url="https://www.allrecipes.com/recipe/garlic-bread",
            ),
            WebRecipe(
                recipe_name="Caesar Salad",
                url="https://www.foodnetwork.com/recipes/caesar-salad",
            ),
            WebRecipe(
                recipe_name="Tiramisu",
                url="https://www.epicurious.com/recipes/tiramisu",
            ),
            WebRecipe(
                recipe_name="Chianti Wine",
                url="https://www.wine.com/chianti",
            ),
            WebRecipe(
                recipe_name="Bruschetta",
                url="https://www.simplyrecipes.com/bruschetta",
            ),
        ],
        limit=50,
        offset=0,
        count=5,
    )


@pytest.fixture
def sample_recipe_detail() -> RecipeDetailResponse:
    """Create sample recipe detail for benchmarks."""
    return RecipeDetailResponse(
        id=123,
        title="Spaghetti Carbonara",
        description="Classic Italian pasta",
        ingredients=[
            RecipeIngredientResponse(
                id=1,
                ingredient_id=1,
                ingredient_name="spaghetti",
                quantity=400.0,
                unit="G",
            ),
            RecipeIngredientResponse(
                id=2,
                ingredient_id=2,
                ingredient_name="pancetta",
                quantity=200.0,
                unit="G",
            ),
        ],
        servings=4,
    )


@pytest.fixture
def mock_pairings_service(
    sample_pairing_result: PairingSuggestionsResponse,
) -> MagicMock:
    """Create mock pairings service for benchmarks."""
    mock = MagicMock()
    mock.get_pairings = AsyncMock(return_value=sample_pairing_result)
    mock.initialize = AsyncMock(return_value=None)
    mock.shutdown = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_recipe_client(
    sample_recipe_detail: RecipeDetailResponse,
) -> MagicMock:
    """Create mock recipe client for benchmarks."""
    mock = MagicMock()
    mock.get_recipe = AsyncMock(return_value=sample_recipe_detail)
    return mock


@pytest.fixture
def perf_pairings_client(
    app: FastAPI,
    sync_client: TestClient,
    mock_pairings_service: MagicMock,
    mock_recipe_client: MagicMock,
) -> Generator[TestClient]:
    """Create sync client with pairings service mocked for performance tests."""
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_pairings_service] = lambda: mock_pairings_service
    app.dependency_overrides[get_recipe_management_client] = lambda: mock_recipe_client

    yield sync_client

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_pairings_service, None)
    app.dependency_overrides.pop(get_recipe_management_client, None)


# --- Pairings Endpoint Benchmarks ---


class TestPairingsEndpointBenchmarks:
    """Benchmarks for GET /recipes/{recipeId}/pairings endpoint."""

    def test_pairings_lookup_response_time(
        self,
        benchmark: BenchmarkFixture,
        perf_pairings_client: TestClient,
    ) -> None:
        """Benchmark pairings lookup response time."""

        def get_pairings() -> dict[str, Any]:
            response = perf_pairings_client.get(
                "/api/v1/recipe-scraper/recipes/123/pairings"
            )
            result: dict[str, Any] = response.json()
            return result

        result = benchmark(get_pairings)
        assert "recipeId" in result
        assert result["recipeId"] == 123

    def test_pairings_status_code(
        self,
        benchmark: BenchmarkFixture,
        perf_pairings_client: TestClient,
    ) -> None:
        """Benchmark pairings lookup status code check."""

        def check_status() -> int:
            response = perf_pairings_client.get(
                "/api/v1/recipe-scraper/recipes/123/pairings"
            )
            return response.status_code

        result = benchmark(check_status)
        assert result == 200

    def test_pairings_throughput(
        self,
        benchmark: BenchmarkFixture,
        perf_pairings_client: TestClient,
    ) -> None:
        """Benchmark pairings endpoint for high throughput scenarios."""

        def lookup_multiple() -> int:
            success_count = 0
            for _ in range(10):
                response = perf_pairings_client.get(
                    "/api/v1/recipe-scraper/recipes/123/pairings"
                )
                if response.status_code == 200:
                    success_count += 1
            return success_count

        result = benchmark(lookup_multiple)
        assert result == 10

    def test_pairings_json_parsing(
        self,
        benchmark: BenchmarkFixture,
        perf_pairings_client: TestClient,
    ) -> None:
        """Benchmark JSON parsing overhead for pairings response."""

        def get_and_parse() -> tuple[int, list[str], int]:
            response = perf_pairings_client.get(
                "/api/v1/recipe-scraper/recipes/123/pairings"
            )
            data = response.json()
            recipe_names = [s["recipeName"] for s in data["pairingSuggestions"]]
            return (
                data["recipeId"],
                recipe_names,
                data["count"],
            )

        result = benchmark(get_and_parse)
        recipe_id, names, count = result
        assert recipe_id == 123
        assert "Garlic Bread" in names
        assert count == 5

    def test_pairings_headers_check(
        self,
        benchmark: BenchmarkFixture,
        perf_pairings_client: TestClient,
    ) -> None:
        """Benchmark pairings endpoint with header verification."""

        def get_with_headers() -> tuple[int, bool, bool]:
            response = perf_pairings_client.get(
                "/api/v1/recipe-scraper/recipes/123/pairings"
            )
            has_request_id = "x-request-id" in response.headers
            has_process_time = "x-process-time" in response.headers
            return response.status_code, has_request_id, has_process_time

        result = benchmark(get_with_headers)
        status_code, has_request_id, has_process_time = result
        assert status_code == 200
        assert has_request_id
        assert has_process_time

    def test_pairings_full_response_validation(
        self,
        benchmark: BenchmarkFixture,
        perf_pairings_client: TestClient,
    ) -> None:
        """Benchmark full response structure validation."""

        def validate_structure() -> bool:
            response = perf_pairings_client.get(
                "/api/v1/recipe-scraper/recipes/123/pairings"
            )
            data = response.json()

            has_required_fields = all(
                [
                    "recipeId" in data,
                    "pairingSuggestions" in data,
                    "limit" in data,
                    "offset" in data,
                    "count" in data,
                ]
            )

            if not has_required_fields or not data["pairingSuggestions"]:
                return False

            # Validate pairing structure
            pairing = data["pairingSuggestions"][0]
            has_valid_pairing = all(
                [
                    "recipeName" in pairing,
                    "url" in pairing,
                ]
            )

            return has_required_fields and has_valid_pairing

        result = benchmark(validate_structure)
        assert result is True


# --- Pagination Benchmarks ---


class TestPairingsPaginationBenchmarks:
    """Benchmarks for pairings pagination performance."""

    def test_pagination_with_limit(
        self,
        benchmark: BenchmarkFixture,
        perf_pairings_client: TestClient,
    ) -> None:
        """Benchmark pagination with limit parameter."""

        def paginated_request() -> dict[str, Any]:
            response = perf_pairings_client.get(
                "/api/v1/recipe-scraper/recipes/123/pairings?limit=2"
            )
            result: dict[str, Any] = response.json()
            return result

        result = benchmark(paginated_request)
        assert "limit" in result

    def test_pagination_with_offset(
        self,
        benchmark: BenchmarkFixture,
        perf_pairings_client: TestClient,
    ) -> None:
        """Benchmark pagination with offset parameter."""

        def offset_request() -> dict[str, Any]:
            response = perf_pairings_client.get(
                "/api/v1/recipe-scraper/recipes/123/pairings?offset=1"
            )
            result: dict[str, Any] = response.json()
            return result

        result = benchmark(offset_request)
        assert "offset" in result

    def test_count_only_performance(
        self,
        benchmark: BenchmarkFixture,
        perf_pairings_client: TestClient,
    ) -> None:
        """Benchmark countOnly parameter performance."""

        def count_only_request() -> dict[str, Any]:
            response = perf_pairings_client.get(
                "/api/v1/recipe-scraper/recipes/123/pairings?countOnly=true"
            )
            result: dict[str, Any] = response.json()
            return result

        result = benchmark(count_only_request)
        assert result["pairingSuggestions"] == []
        assert result["count"] == 5


# --- Model Instantiation Benchmarks ---


class TestPairingsModelBenchmarks:
    """Benchmarks for pairings model instantiation overhead."""

    def test_pairing_result_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark PairingResult model instantiation."""

        def create_pairing_result() -> PairingResult:
            return PairingResult(
                recipe_name="Garlic Bread",
                url="https://www.allrecipes.com/recipe/garlic-bread",
                pairing_reason="Classic Italian accompaniment",
                cuisine_type="Italian",
                confidence=0.95,
            )

        result = benchmark(create_pairing_result)
        assert result.recipe_name == "Garlic Bread"

    def test_pairing_list_result_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark PairingListResult model instantiation."""

        def create_list_result() -> PairingListResult:
            return PairingListResult(
                pairings=[
                    PairingResult(
                        recipe_name="Garlic Bread",
                        url="https://example.com/1",
                        pairing_reason="Reason 1",
                    ),
                    PairingResult(
                        recipe_name="Caesar Salad",
                        url="https://example.com/2",
                        pairing_reason="Reason 2",
                    ),
                ]
            )

        result = benchmark(create_list_result)
        assert len(result.pairings) == 2

    def test_web_recipe_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark WebRecipe model instantiation."""

        def create_web_recipe() -> WebRecipe:
            return WebRecipe(
                recipe_name="Garlic Bread",
                url="https://www.allrecipes.com/recipe/garlic-bread",
            )

        result = benchmark(create_web_recipe)
        assert result.recipe_name == "Garlic Bread"

    def test_pairing_suggestions_response_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark PairingSuggestionsResponse model instantiation."""

        def create_response() -> PairingSuggestionsResponse:
            return PairingSuggestionsResponse(
                recipe_id=123,
                pairing_suggestions=[
                    WebRecipe(
                        recipe_name="Garlic Bread",
                        url="https://example.com/1",
                    ),
                    WebRecipe(
                        recipe_name="Caesar Salad",
                        url="https://example.com/2",
                    ),
                ],
                limit=50,
                offset=0,
                count=2,
            )

        result = benchmark(create_response)
        assert result.recipe_id == 123
        assert len(result.pairing_suggestions) == 2

    def test_batch_web_recipe_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark batch WebRecipe instantiation."""

        def create_web_recipes() -> list[WebRecipe]:
            return [
                WebRecipe(
                    recipe_name="Garlic Bread",
                    url="https://example.com/1",
                ),
                WebRecipe(
                    recipe_name="Caesar Salad",
                    url="https://example.com/2",
                ),
                WebRecipe(
                    recipe_name="Tiramisu",
                    url="https://example.com/3",
                ),
                WebRecipe(
                    recipe_name="Chianti Wine",
                    url="https://example.com/4",
                ),
                WebRecipe(
                    recipe_name="Bruschetta",
                    url="https://example.com/5",
                ),
            ]

        result = benchmark(create_web_recipes)
        assert len(result) == 5
