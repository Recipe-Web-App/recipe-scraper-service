"""Performance benchmarks for ingredient substitutions endpoint.

Benchmarks cover:
- Substitution lookup response time
- Endpoint throughput
- JSON response parsing overhead
- Model instantiation performance
- Pagination performance

Note: Uses synchronous HTTP client to avoid event loop
conflicts with pytest-benchmark.

All external dependencies (LLM, cache, repository) are mocked
via FastAPI dependency overrides for isolated performance measurement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.dependencies import get_substitution_service
from app.auth.dependencies import CurrentUser, get_current_user
from app.llm.prompts.substitution import SubstitutionListResult, SubstitutionResult
from app.schemas.enums import IngredientUnit
from app.schemas.ingredient import Ingredient, Quantity
from app.schemas.recommendations import (
    ConversionRatio,
    IngredientSubstitution,
    RecommendedSubstitutionsResponse,
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
def sample_substitution_result() -> SubstitutionListResult:
    """Create sample LLM substitution result for benchmarks."""
    return SubstitutionListResult(
        substitutions=[
            SubstitutionResult(
                ingredient="coconut oil",
                ratio=1.0,
                measurement="CUP",
                notes="Best for baking",
                confidence=0.95,
            ),
            SubstitutionResult(
                ingredient="olive oil",
                ratio=0.75,
                measurement="CUP",
                notes="Best for savory",
                confidence=0.9,
            ),
            SubstitutionResult(
                ingredient="applesauce",
                ratio=0.5,
                measurement="CUP",
                notes="Good for baking",
                confidence=0.85,
            ),
            SubstitutionResult(
                ingredient="avocado",
                ratio=1.0,
                measurement="CUP",
                notes="Healthy alternative",
                confidence=0.8,
            ),
            SubstitutionResult(
                ingredient="greek yogurt",
                ratio=0.5,
                measurement="CUP",
                notes="Adds protein",
                confidence=0.75,
            ),
        ]
    )


@pytest.fixture
def sample_response() -> RecommendedSubstitutionsResponse:
    """Create sample substitution response for benchmarks."""
    return RecommendedSubstitutionsResponse(
        ingredient=Ingredient(
            ingredient_id=None,
            name="butter",
            quantity=None,
        ),
        recommended_substitutions=[
            IngredientSubstitution(
                ingredient="coconut oil",
                quantity=None,
                conversion_ratio=ConversionRatio(
                    ratio=1.0,
                    measurement=IngredientUnit.CUP,
                ),
            ),
            IngredientSubstitution(
                ingredient="olive oil",
                quantity=None,
                conversion_ratio=ConversionRatio(
                    ratio=0.75,
                    measurement=IngredientUnit.CUP,
                ),
            ),
            IngredientSubstitution(
                ingredient="applesauce",
                quantity=None,
                conversion_ratio=ConversionRatio(
                    ratio=0.5,
                    measurement=IngredientUnit.CUP,
                ),
            ),
        ],
        limit=50,
        offset=0,
        count=3,
    )


@pytest.fixture
def sample_response_with_quantity() -> RecommendedSubstitutionsResponse:
    """Create sample response with quantity for benchmarks."""
    return RecommendedSubstitutionsResponse(
        ingredient=Ingredient(
            ingredient_id=None,
            name="butter",
            quantity=Quantity(amount=1.0, measurement=IngredientUnit.CUP),
        ),
        recommended_substitutions=[
            IngredientSubstitution(
                ingredient="coconut oil",
                quantity=Quantity(amount=1.0, measurement=IngredientUnit.CUP),
                conversion_ratio=ConversionRatio(
                    ratio=1.0,
                    measurement=IngredientUnit.CUP,
                ),
            ),
            IngredientSubstitution(
                ingredient="olive oil",
                quantity=Quantity(amount=0.75, measurement=IngredientUnit.CUP),
                conversion_ratio=ConversionRatio(
                    ratio=0.75,
                    measurement=IngredientUnit.CUP,
                ),
            ),
            IngredientSubstitution(
                ingredient="applesauce",
                quantity=Quantity(amount=0.5, measurement=IngredientUnit.CUP),
                conversion_ratio=ConversionRatio(
                    ratio=0.5,
                    measurement=IngredientUnit.CUP,
                ),
            ),
        ],
        limit=50,
        offset=0,
        count=3,
    )


@pytest.fixture
def mock_substitution_service(
    sample_response: RecommendedSubstitutionsResponse,
) -> MagicMock:
    """Create mock substitution service for benchmarks."""
    mock = MagicMock()
    mock.get_substitutions = AsyncMock(return_value=sample_response)
    mock.initialize = AsyncMock(return_value=None)
    mock.shutdown = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def perf_substitution_client(
    app: FastAPI,
    sync_client: TestClient,
    mock_substitution_service: MagicMock,
) -> Generator[TestClient]:
    """Create sync client with substitution service mocked for performance tests."""
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_substitution_service] = (
        lambda: mock_substitution_service
    )

    yield sync_client

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_substitution_service, None)


# --- Substitution Endpoint Benchmarks ---


class TestSubstitutionEndpointBenchmarks:
    """Benchmarks for GET /ingredients/{id}/substitutions endpoint."""

    def test_substitution_lookup_response_time(
        self,
        benchmark: BenchmarkFixture,
        perf_substitution_client: TestClient,
    ) -> None:
        """Benchmark substitution lookup response time."""

        def get_substitutions() -> dict[str, Any]:
            response = perf_substitution_client.get(
                "/api/v1/recipe-scraper/ingredients/butter/substitutions"
            )
            result: dict[str, Any] = response.json()
            return result

        result = benchmark(get_substitutions)
        assert "ingredient" in result
        assert result["ingredient"]["name"] == "butter"

    def test_substitution_status_code(
        self,
        benchmark: BenchmarkFixture,
        perf_substitution_client: TestClient,
    ) -> None:
        """Benchmark substitution lookup status code check."""

        def check_status() -> int:
            response = perf_substitution_client.get(
                "/api/v1/recipe-scraper/ingredients/butter/substitutions"
            )
            return response.status_code

        result = benchmark(check_status)
        assert result == 200

    def test_substitution_throughput(
        self,
        benchmark: BenchmarkFixture,
        perf_substitution_client: TestClient,
    ) -> None:
        """Benchmark substitution endpoint for high throughput scenarios."""

        def lookup_multiple() -> int:
            success_count = 0
            for _ in range(10):
                response = perf_substitution_client.get(
                    "/api/v1/recipe-scraper/ingredients/butter/substitutions"
                )
                if response.status_code == 200:
                    success_count += 1
            return success_count

        result = benchmark(lookup_multiple)
        assert result == 10

    def test_substitution_json_parsing(
        self,
        benchmark: BenchmarkFixture,
        perf_substitution_client: TestClient,
    ) -> None:
        """Benchmark JSON parsing overhead for substitution response."""

        def get_and_parse() -> tuple[str, list[str], int]:
            response = perf_substitution_client.get(
                "/api/v1/recipe-scraper/ingredients/butter/substitutions"
            )
            data = response.json()
            substitution_names = [
                s["ingredient"] for s in data["recommendedSubstitutions"]
            ]
            return (
                data["ingredient"]["name"],
                substitution_names,
                data["count"],
            )

        result = benchmark(get_and_parse)
        name, substitutions, count = result
        assert name == "butter"
        assert "coconut oil" in substitutions
        assert count == 3

    def test_substitution_headers_check(
        self,
        benchmark: BenchmarkFixture,
        perf_substitution_client: TestClient,
    ) -> None:
        """Benchmark substitution endpoint with header verification."""

        def get_with_headers() -> tuple[int, bool, bool]:
            response = perf_substitution_client.get(
                "/api/v1/recipe-scraper/ingredients/butter/substitutions"
            )
            has_request_id = "x-request-id" in response.headers
            has_process_time = "x-process-time" in response.headers
            return response.status_code, has_request_id, has_process_time

        result = benchmark(get_with_headers)
        status_code, has_request_id, has_process_time = result
        assert status_code == 200
        assert has_request_id
        assert has_process_time

    def test_substitution_full_response_validation(
        self,
        benchmark: BenchmarkFixture,
        perf_substitution_client: TestClient,
    ) -> None:
        """Benchmark full response structure validation."""

        def validate_structure() -> bool:
            response = perf_substitution_client.get(
                "/api/v1/recipe-scraper/ingredients/butter/substitutions"
            )
            data = response.json()

            has_required_fields = all(
                [
                    "ingredient" in data,
                    "recommendedSubstitutions" in data,
                    "limit" in data,
                    "offset" in data,
                    "count" in data,
                ]
            )

            if not has_required_fields or not data["recommendedSubstitutions"]:
                return False

            # Validate substitution structure
            substitution = data["recommendedSubstitutions"][0]
            has_valid_substitution = all(
                [
                    "ingredient" in substitution,
                    "conversionRatio" in substitution,
                ]
            )

            return has_required_fields and has_valid_substitution

        result = benchmark(validate_structure)
        assert result is True


# --- Pagination Benchmarks ---


class TestSubstitutionPaginationBenchmarks:
    """Benchmarks for substitution pagination performance."""

    def test_pagination_with_limit(
        self,
        benchmark: BenchmarkFixture,
        perf_substitution_client: TestClient,
    ) -> None:
        """Benchmark pagination with limit parameter."""

        def paginated_request() -> dict[str, Any]:
            response = perf_substitution_client.get(
                "/api/v1/recipe-scraper/ingredients/butter/substitutions?limit=2"
            )
            result: dict[str, Any] = response.json()
            return result

        result = benchmark(paginated_request)
        # Verify response has pagination metadata (actual limit depends on mock)
        assert "limit" in result

    def test_pagination_with_offset(
        self,
        benchmark: BenchmarkFixture,
        perf_substitution_client: TestClient,
    ) -> None:
        """Benchmark pagination with offset parameter."""

        def offset_request() -> dict[str, Any]:
            response = perf_substitution_client.get(
                "/api/v1/recipe-scraper/ingredients/butter/substitutions?offset=1"
            )
            result: dict[str, Any] = response.json()
            return result

        result = benchmark(offset_request)
        # Verify response has pagination metadata (actual offset depends on mock)
        assert "offset" in result

    def test_count_only_performance(
        self,
        benchmark: BenchmarkFixture,
        perf_substitution_client: TestClient,
    ) -> None:
        """Benchmark countOnly parameter performance."""

        def count_only_request() -> dict[str, Any]:
            response = perf_substitution_client.get(
                "/api/v1/recipe-scraper/ingredients/butter/substitutions?countOnly=true"
            )
            result: dict[str, Any] = response.json()
            return result

        result = benchmark(count_only_request)
        assert result["recommendedSubstitutions"] == []
        assert result["count"] == 3


# --- Model Instantiation Benchmarks ---


class TestSubstitutionModelBenchmarks:
    """Benchmarks for substitution model instantiation overhead."""

    def test_substitution_result_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark SubstitutionResult model instantiation."""

        def create_substitution_result() -> SubstitutionResult:
            return SubstitutionResult(
                ingredient="coconut oil",
                ratio=1.0,
                measurement="CUP",
                notes="Best for baking",
                confidence=0.95,
            )

        result = benchmark(create_substitution_result)
        assert result.ingredient == "coconut oil"

    def test_substitution_list_result_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark SubstitutionListResult model instantiation."""

        def create_list_result() -> SubstitutionListResult:
            return SubstitutionListResult(
                substitutions=[
                    SubstitutionResult(
                        ingredient="coconut oil",
                        ratio=1.0,
                        measurement="CUP",
                    ),
                    SubstitutionResult(
                        ingredient="olive oil",
                        ratio=0.75,
                        measurement="CUP",
                    ),
                ]
            )

        result = benchmark(create_list_result)
        assert len(result.substitutions) == 2

    def test_ingredient_substitution_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark IngredientSubstitution model instantiation."""

        def create_ingredient_substitution() -> IngredientSubstitution:
            return IngredientSubstitution(
                ingredient="coconut oil",
                quantity=Quantity(amount=1.0, measurement=IngredientUnit.CUP),
                conversion_ratio=ConversionRatio(
                    ratio=1.0,
                    measurement=IngredientUnit.CUP,
                ),
            )

        result = benchmark(create_ingredient_substitution)
        assert result.ingredient == "coconut oil"

    def test_recommended_substitutions_response_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark RecommendedSubstitutionsResponse model instantiation."""

        def create_response() -> RecommendedSubstitutionsResponse:
            return RecommendedSubstitutionsResponse(
                ingredient=Ingredient(
                    ingredient_id=None,
                    name="butter",
                    quantity=None,
                ),
                recommended_substitutions=[
                    IngredientSubstitution(
                        ingredient="coconut oil",
                        quantity=None,
                        conversion_ratio=ConversionRatio(
                            ratio=1.0,
                            measurement=IngredientUnit.CUP,
                        ),
                    ),
                    IngredientSubstitution(
                        ingredient="olive oil",
                        quantity=None,
                        conversion_ratio=ConversionRatio(
                            ratio=0.75,
                            measurement=IngredientUnit.CUP,
                        ),
                    ),
                ],
                limit=50,
                offset=0,
                count=2,
            )

        result = benchmark(create_response)
        assert result.ingredient.name == "butter"
        assert len(result.recommended_substitutions) == 2

    def test_conversion_ratio_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark ConversionRatio model instantiation."""

        def create_conversion_ratio() -> ConversionRatio:
            return ConversionRatio(
                ratio=1.0,
                measurement=IngredientUnit.CUP,
            )

        result = benchmark(create_conversion_ratio)
        assert result.ratio == 1.0
        assert result.measurement == IngredientUnit.CUP

    def test_batch_substitution_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark batch IngredientSubstitution instantiation."""

        def create_substitutions() -> list[IngredientSubstitution]:
            return [
                IngredientSubstitution(
                    ingredient="coconut oil",
                    quantity=None,
                    conversion_ratio=ConversionRatio(
                        ratio=1.0, measurement=IngredientUnit.CUP
                    ),
                ),
                IngredientSubstitution(
                    ingredient="olive oil",
                    quantity=None,
                    conversion_ratio=ConversionRatio(
                        ratio=0.75, measurement=IngredientUnit.CUP
                    ),
                ),
                IngredientSubstitution(
                    ingredient="applesauce",
                    quantity=None,
                    conversion_ratio=ConversionRatio(
                        ratio=0.5, measurement=IngredientUnit.CUP
                    ),
                ),
                IngredientSubstitution(
                    ingredient="avocado",
                    quantity=None,
                    conversion_ratio=ConversionRatio(
                        ratio=1.0, measurement=IngredientUnit.CUP
                    ),
                ),
                IngredientSubstitution(
                    ingredient="greek yogurt",
                    quantity=None,
                    conversion_ratio=ConversionRatio(
                        ratio=0.5, measurement=IngredientUnit.CUP
                    ),
                ),
            ]

        result = benchmark(create_substitutions)
        assert len(result) == 5


# --- Quantity Calculation Benchmarks ---


class TestQuantityCalculationBenchmarks:
    """Benchmarks for quantity calculation performance."""

    def test_quantity_with_amount_and_measurement(
        self,
        benchmark: BenchmarkFixture,
        perf_substitution_client: TestClient,
    ) -> None:
        """Benchmark request with quantity parameters."""

        def request_with_quantity() -> dict[str, Any]:
            response = perf_substitution_client.get(
                "/api/v1/recipe-scraper/ingredients/butter/substitutions"
                "?amount=1&measurement=CUP"
            )
            result: dict[str, Any] = response.json()
            return result

        result = benchmark(request_with_quantity)
        assert result["ingredient"]["name"] == "butter"

    def test_quantity_calculation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark quantity calculation logic."""

        def calculate_quantities() -> list[Quantity]:
            base_amount = 1.0
            ratios = [1.0, 0.75, 0.5, 1.0, 0.5]

            return [
                Quantity(
                    amount=base_amount * ratio,
                    measurement=IngredientUnit.CUP,
                )
                for ratio in ratios
            ]

        result = benchmark(calculate_quantities)
        assert len(result) == 5
        assert result[0].amount == 1.0
        assert result[1].amount == 0.75
