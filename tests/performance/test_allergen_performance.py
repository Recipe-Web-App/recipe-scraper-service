"""Performance benchmarks for allergen endpoints.

Benchmarks cover:
- Ingredient allergen lookup response time
- Recipe allergen aggregation
- Endpoint throughput
- JSON response parsing overhead
- Model instantiation performance

Note: Uses synchronous HTTP client to avoid event loop
conflicts with pytest-benchmark.

All external dependencies (repository, cache) are mocked
via FastAPI dependency overrides for isolated performance measurement.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.dependencies import get_allergen_service, get_recipe_management_client
from app.auth.dependencies import CurrentUser, get_current_user
from app.database.repositories.allergen import AllergenData
from app.schemas.allergen import (
    AllergenDataSource,
    AllergenInfo,
    AllergenPresenceType,
    IngredientAllergenResponse,
    RecipeAllergenResponse,
)
from app.schemas.enums import Allergen


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
def sample_allergen_data() -> list[AllergenData]:
    """Create sample allergen data for benchmarks."""
    return [
        AllergenData(
            ingredient_id=1,
            ingredient_name="flour",
            usda_food_description="Wheat flour, white, all-purpose, enriched",
            allergen_type="GLUTEN",
            presence_type="CONTAINS",
            confidence_score=Decimal("1.0"),
            source_notes="Contains wheat gluten",
            data_source="USDA",
            profile_confidence=Decimal("1.0"),
        ),
        AllergenData(
            ingredient_id=1,
            ingredient_name="flour",
            usda_food_description="Wheat flour, white, all-purpose, enriched",
            allergen_type="WHEAT",
            presence_type="CONTAINS",
            confidence_score=Decimal("1.0"),
            source_notes="Made from wheat",
            data_source="USDA",
            profile_confidence=Decimal("1.0"),
        ),
    ]


@pytest.fixture
def sample_ingredient_allergen_response() -> IngredientAllergenResponse:
    """Create sample ingredient allergen response for benchmarks."""
    return IngredientAllergenResponse(
        ingredient_id=1,
        ingredient_name="flour",
        usda_food_description="Wheat flour, white, all-purpose, enriched",
        allergens=[
            AllergenInfo(
                allergen=Allergen.GLUTEN,
                presence_type=AllergenPresenceType.CONTAINS,
                confidence_score=1.0,
                source_notes="Contains wheat gluten",
            ),
            AllergenInfo(
                allergen=Allergen.WHEAT,
                presence_type=AllergenPresenceType.CONTAINS,
                confidence_score=1.0,
                source_notes="Made from wheat",
            ),
        ],
        data_source=AllergenDataSource.USDA,
        overall_confidence=1.0,
    )


@pytest.fixture
def sample_recipe_allergen_response() -> RecipeAllergenResponse:
    """Create sample recipe allergen response for benchmarks."""
    return RecipeAllergenResponse(
        contains=[Allergen.GLUTEN, Allergen.WHEAT, Allergen.MILK, Allergen.EGGS],
        may_contain=[Allergen.TREE_NUTS],
        allergens=[
            AllergenInfo(
                allergen=Allergen.GLUTEN,
                presence_type=AllergenPresenceType.CONTAINS,
            ),
            AllergenInfo(
                allergen=Allergen.WHEAT,
                presence_type=AllergenPresenceType.CONTAINS,
            ),
            AllergenInfo(
                allergen=Allergen.MILK,
                presence_type=AllergenPresenceType.CONTAINS,
            ),
            AllergenInfo(
                allergen=Allergen.EGGS,
                presence_type=AllergenPresenceType.CONTAINS,
            ),
            AllergenInfo(
                allergen=Allergen.TREE_NUTS,
                presence_type=AllergenPresenceType.MAY_CONTAIN,
            ),
        ],
        missing_ingredients=[],
    )


@pytest.fixture
def mock_allergen_service(
    sample_ingredient_allergen_response: IngredientAllergenResponse,
    sample_recipe_allergen_response: RecipeAllergenResponse,
) -> MagicMock:
    """Create mock allergen service for benchmarks."""
    mock = MagicMock()
    mock.get_ingredient_allergens = AsyncMock(
        return_value=sample_ingredient_allergen_response
    )
    mock.get_recipe_allergens = AsyncMock(return_value=sample_recipe_allergen_response)
    mock.initialize = AsyncMock(return_value=None)
    mock.shutdown = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_recipe_client() -> MagicMock:
    """Create mock recipe management client for benchmarks."""
    # Import at runtime to avoid circular imports
    from app.services.recipe_management.schemas import (
        IngredientUnit,
        RecipeDetailResponse,
        RecipeIngredientResponse,
    )

    mock = MagicMock()
    mock.get_recipe = AsyncMock(
        return_value=RecipeDetailResponse(
            id=1,
            title="Pancakes",
            ingredients=[
                RecipeIngredientResponse(
                    id=1,
                    ingredient_id=1,
                    ingredient_name="flour",
                    quantity=200.0,
                    unit=IngredientUnit.G,
                ),
                RecipeIngredientResponse(
                    id=2,
                    ingredient_id=2,
                    ingredient_name="butter",
                    quantity=50.0,
                    unit=IngredientUnit.G,
                ),
                RecipeIngredientResponse(
                    id=3,
                    ingredient_id=3,
                    ingredient_name="eggs",
                    quantity=2.0,
                    unit=IngredientUnit.PIECE,
                ),
            ],
        )
    )
    return mock


@pytest.fixture
def perf_allergen_client(
    app: FastAPI,
    sync_client: TestClient,
    mock_allergen_service: MagicMock,
    mock_recipe_client: MagicMock,
) -> Generator[TestClient]:
    """Create sync client with allergen service mocked for performance tests."""
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_allergen_service] = lambda: mock_allergen_service
    app.dependency_overrides[get_recipe_management_client] = lambda: mock_recipe_client

    yield sync_client

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_allergen_service, None)
    app.dependency_overrides.pop(get_recipe_management_client, None)


# --- Ingredient Allergen Endpoint Benchmarks ---


class TestIngredientAllergenBenchmarks:
    """Benchmarks for GET /ingredients/{id}/allergens endpoint."""

    def test_ingredient_allergen_lookup_response_time(
        self,
        benchmark: BenchmarkFixture,
        perf_allergen_client: TestClient,
    ) -> None:
        """Benchmark ingredient allergen lookup response time."""

        def get_allergens() -> dict[str, Any]:
            response = perf_allergen_client.get(
                "/api/v1/recipe-scraper/ingredients/flour/allergens"
            )
            result: dict[str, Any] = response.json()
            return result

        result = benchmark(get_allergens)
        assert "ingredientName" in result
        assert result["ingredientName"] == "flour"

    def test_ingredient_allergen_status_code(
        self,
        benchmark: BenchmarkFixture,
        perf_allergen_client: TestClient,
    ) -> None:
        """Benchmark ingredient allergen lookup status code check."""

        def check_status() -> int:
            response = perf_allergen_client.get(
                "/api/v1/recipe-scraper/ingredients/flour/allergens"
            )
            return response.status_code

        result = benchmark(check_status)
        assert result == 200

    def test_ingredient_allergen_throughput(
        self,
        benchmark: BenchmarkFixture,
        perf_allergen_client: TestClient,
    ) -> None:
        """Benchmark ingredient allergen endpoint for high throughput scenarios."""

        def lookup_multiple() -> int:
            success_count = 0
            for _ in range(10):
                response = perf_allergen_client.get(
                    "/api/v1/recipe-scraper/ingredients/flour/allergens"
                )
                if response.status_code == 200:
                    success_count += 1
            return success_count

        result = benchmark(lookup_multiple)
        assert result == 10

    def test_ingredient_allergen_json_parsing(
        self,
        benchmark: BenchmarkFixture,
        perf_allergen_client: TestClient,
    ) -> None:
        """Benchmark JSON parsing overhead for allergen response."""

        def get_and_parse() -> tuple[str, list[str], str]:
            response = perf_allergen_client.get(
                "/api/v1/recipe-scraper/ingredients/flour/allergens"
            )
            data = response.json()
            allergen_types = [a["allergen"] for a in data["allergens"]]
            return (
                data["ingredientName"],
                allergen_types,
                data["dataSource"],
            )

        result = benchmark(get_and_parse)
        name, allergens, source = result
        assert name == "flour"
        assert "GLUTEN" in allergens
        assert "WHEAT" in allergens
        assert source == "USDA"

    def test_ingredient_allergen_headers_check(
        self,
        benchmark: BenchmarkFixture,
        perf_allergen_client: TestClient,
    ) -> None:
        """Benchmark ingredient allergen endpoint with header verification."""

        def get_with_headers() -> tuple[int, bool, bool]:
            response = perf_allergen_client.get(
                "/api/v1/recipe-scraper/ingredients/flour/allergens"
            )
            has_request_id = "x-request-id" in response.headers
            has_process_time = "x-process-time" in response.headers
            return response.status_code, has_request_id, has_process_time

        result = benchmark(get_with_headers)
        status_code, has_request_id, has_process_time = result
        assert status_code == 200
        assert has_request_id
        assert has_process_time

    def test_ingredient_allergen_full_response_validation(
        self,
        benchmark: BenchmarkFixture,
        perf_allergen_client: TestClient,
    ) -> None:
        """Benchmark full response structure validation."""

        def validate_structure() -> bool:
            response = perf_allergen_client.get(
                "/api/v1/recipe-scraper/ingredients/flour/allergens"
            )
            data = response.json()

            has_required_fields = all(
                [
                    "ingredientName" in data,
                    "allergens" in data,
                    "dataSource" in data,
                ]
            )

            if not has_required_fields or not data["allergens"]:
                return False

            # Validate allergen structure
            allergen = data["allergens"][0]
            has_valid_allergen = all(
                [
                    "allergen" in allergen,
                    "presenceType" in allergen,
                ]
            )

            return has_required_fields and has_valid_allergen

        result = benchmark(validate_structure)
        assert result is True


# --- Recipe Allergen Endpoint Benchmarks ---


class TestRecipeAllergenBenchmarks:
    """Benchmarks for GET /recipes/{recipeId}/allergens endpoint."""

    def test_recipe_allergen_aggregation_response_time(
        self,
        benchmark: BenchmarkFixture,
        perf_allergen_client: TestClient,
    ) -> None:
        """Benchmark recipe allergen aggregation response time."""

        def get_recipe_allergens() -> dict[str, Any]:
            response = perf_allergen_client.get(
                "/api/v1/recipe-scraper/recipes/1/allergens"
            )
            result: dict[str, Any] = response.json()
            return result

        result = benchmark(get_recipe_allergens)
        assert "contains" in result
        assert "mayContain" in result

    def test_recipe_allergen_throughput(
        self,
        benchmark: BenchmarkFixture,
        perf_allergen_client: TestClient,
    ) -> None:
        """Benchmark recipe allergen endpoint throughput."""

        def lookup_multiple_recipes() -> int:
            success_count = 0
            for _ in range(10):
                response = perf_allergen_client.get(
                    "/api/v1/recipe-scraper/recipes/1/allergens"
                )
                if response.status_code == 200:
                    success_count += 1
            return success_count

        result = benchmark(lookup_multiple_recipes)
        assert result == 10

    def test_recipe_allergen_contains_list_parsing(
        self,
        benchmark: BenchmarkFixture,
        perf_allergen_client: TestClient,
    ) -> None:
        """Benchmark parsing of recipe allergen contains/mayContain lists."""

        def parse_allergen_lists() -> tuple[set[str], set[str]]:
            response = perf_allergen_client.get(
                "/api/v1/recipe-scraper/recipes/1/allergens"
            )
            data = response.json()
            contains = set(data["contains"])
            may_contain = set(data["mayContain"])
            return contains, may_contain

        result = benchmark(parse_allergen_lists)
        contains, may_contain = result
        assert "GLUTEN" in contains
        assert "MILK" in contains
        assert "TREE_NUTS" in may_contain


# --- Model Instantiation Benchmarks ---


class TestAllergenModelBenchmarks:
    """Benchmarks for allergen model instantiation overhead."""

    def test_allergen_data_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark AllergenData model instantiation."""

        def create_allergen_data() -> AllergenData:
            return AllergenData(
                ingredient_id=1,
                ingredient_name="flour",
                usda_food_description="Wheat flour",
                allergen_type="GLUTEN",
                presence_type="CONTAINS",
                confidence_score=Decimal("1.0"),
                source_notes="Contains gluten",
                data_source="USDA",
                profile_confidence=Decimal("1.0"),
            )

        result = benchmark(create_allergen_data)
        assert result.ingredient_name == "flour"

    def test_allergen_info_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark AllergenInfo model instantiation."""

        def create_allergen_info() -> AllergenInfo:
            return AllergenInfo(
                allergen=Allergen.GLUTEN,
                presence_type=AllergenPresenceType.CONTAINS,
                confidence_score=1.0,
                source_notes="Contains gluten",
            )

        result = benchmark(create_allergen_info)
        assert result.allergen == Allergen.GLUTEN

    def test_ingredient_allergen_response_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark IngredientAllergenResponse model instantiation."""

        def create_response() -> IngredientAllergenResponse:
            return IngredientAllergenResponse(
                ingredient_id=1,
                ingredient_name="flour",
                allergens=[
                    AllergenInfo(
                        allergen=Allergen.GLUTEN,
                        presence_type=AllergenPresenceType.CONTAINS,
                    ),
                    AllergenInfo(
                        allergen=Allergen.WHEAT,
                        presence_type=AllergenPresenceType.CONTAINS,
                    ),
                ],
                data_source=AllergenDataSource.USDA,
            )

        result = benchmark(create_response)
        assert result.ingredient_name == "flour"
        assert len(result.allergens) == 2

    def test_recipe_allergen_response_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark RecipeAllergenResponse model instantiation."""

        def create_response() -> RecipeAllergenResponse:
            return RecipeAllergenResponse(
                contains=[Allergen.GLUTEN, Allergen.MILK, Allergen.EGGS],
                may_contain=[Allergen.TREE_NUTS],
                allergens=[
                    AllergenInfo(allergen=Allergen.GLUTEN),
                    AllergenInfo(allergen=Allergen.MILK),
                    AllergenInfo(allergen=Allergen.EGGS),
                ],
                missing_ingredients=[],
            )

        result = benchmark(create_response)
        assert len(result.contains) == 3
        assert len(result.may_contain) == 1

    def test_allergen_info_batch_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark batch AllergenInfo instantiation."""

        def create_allergen_infos() -> list[AllergenInfo]:
            return [
                AllergenInfo(
                    allergen=Allergen.GLUTEN,
                    presence_type=AllergenPresenceType.CONTAINS,
                ),
                AllergenInfo(
                    allergen=Allergen.WHEAT,
                    presence_type=AllergenPresenceType.CONTAINS,
                ),
                AllergenInfo(
                    allergen=Allergen.MILK,
                    presence_type=AllergenPresenceType.CONTAINS,
                ),
                AllergenInfo(
                    allergen=Allergen.EGGS,
                    presence_type=AllergenPresenceType.CONTAINS,
                ),
                AllergenInfo(
                    allergen=Allergen.PEANUTS,
                    presence_type=AllergenPresenceType.MAY_CONTAIN,
                ),
                AllergenInfo(
                    allergen=Allergen.TREE_NUTS,
                    presence_type=AllergenPresenceType.TRACES,
                ),
            ]

        result = benchmark(create_allergen_infos)
        assert len(result) == 6


# --- Allergen Aggregation Benchmarks ---


class TestAllergenAggregationBenchmarks:
    """Benchmarks for allergen aggregation logic."""

    def test_allergen_deduplication(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark allergen deduplication from multiple ingredients."""

        def deduplicate_allergens() -> set[Allergen]:
            # Simulate aggregating allergens from multiple ingredients
            flour_allergens = [Allergen.GLUTEN, Allergen.WHEAT]
            butter_allergens = [Allergen.MILK]
            eggs_allergens = [Allergen.EGGS]
            bread_allergens = [Allergen.GLUTEN, Allergen.WHEAT]  # Duplicates

            all_allergens = (
                flour_allergens + butter_allergens + eggs_allergens + bread_allergens
            )
            return set(all_allergens)

        result = benchmark(deduplicate_allergens)
        assert len(result) == 4  # GLUTEN, WHEAT, MILK, EGGS (no duplicates)

    def test_contains_vs_may_contain_classification(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark allergen classification into contains/may_contain."""

        def classify_allergens() -> tuple[list[Allergen], list[Allergen]]:
            allergen_infos = [
                AllergenInfo(
                    allergen=Allergen.GLUTEN,
                    presence_type=AllergenPresenceType.CONTAINS,
                ),
                AllergenInfo(
                    allergen=Allergen.MILK,
                    presence_type=AllergenPresenceType.CONTAINS,
                ),
                AllergenInfo(
                    allergen=Allergen.PEANUTS,
                    presence_type=AllergenPresenceType.MAY_CONTAIN,
                ),
                AllergenInfo(
                    allergen=Allergen.TREE_NUTS,
                    presence_type=AllergenPresenceType.TRACES,
                ),
            ]

            contains = [
                a.allergen
                for a in allergen_infos
                if a.presence_type == AllergenPresenceType.CONTAINS
            ]
            may_contain = [
                a.allergen
                for a in allergen_infos
                if a.presence_type
                in (AllergenPresenceType.MAY_CONTAIN, AllergenPresenceType.TRACES)
            ]

            return contains, may_contain

        result = benchmark(classify_allergens)
        contains, may_contain = result
        assert len(contains) == 2
        assert len(may_contain) == 2
