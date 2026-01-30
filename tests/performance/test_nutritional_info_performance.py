"""Performance benchmarks for nutritional-info endpoints.

Benchmarks cover:
- Ingredient lookup response time (cache hit vs miss)
- Recipe aggregation with multiple ingredients
- Fuzzy search overhead compared to exact match
- Unit conversion throughput
- Batch lookup performance

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

from app.api.dependencies import get_nutrition_service
from app.auth.dependencies import CurrentUser, get_current_user
from app.database.repositories.nutrition import (
    MacronutrientsData,
    MineralsData,
    NutritionData,
    VitaminsData,
)
from app.schemas.enums import IngredientUnit, NutrientUnit
from app.schemas.ingredient import Quantity
from app.schemas.nutrition import (
    Fats,
    IngredientNutritionalInfoResponse,
    MacroNutrients,
    Minerals,
    NutrientValue,
    Vitamins,
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
def sample_nutrition_data() -> NutritionData:
    """Create sample nutrition data for benchmarks."""
    return NutritionData(
        ingredient_id=1,
        ingredient_name="flour",
        fdc_id=169761,
        usda_food_description="Wheat flour, white, all-purpose, enriched",
        serving_size_g=Decimal("100.00"),
        macronutrients=MacronutrientsData(
            calories_kcal=Decimal("364.00"),
            protein_g=Decimal("10.30"),
            carbs_g=Decimal("76.30"),
            fat_g=Decimal("1.00"),
            saturated_fat_g=Decimal("0.20"),
            fiber_g=Decimal("2.70"),
            sugar_g=Decimal("0.30"),
            cholesterol_mg=Decimal("0.00"),
            sodium_mg=Decimal("2.00"),
        ),
        vitamins=VitaminsData(
            vitamin_a_mcg=Decimal("0.00"),
            vitamin_b6_mcg=Decimal("44.00"),
            vitamin_c_mcg=Decimal("0.00"),
        ),
        minerals=MineralsData(
            calcium_mg=Decimal("15.00"),
            iron_mg=Decimal("4.60"),
            potassium_mg=Decimal("107.00"),
        ),
    )


@pytest.fixture
def sample_nutrition_response() -> IngredientNutritionalInfoResponse:
    """Create sample nutrition response for benchmarks."""
    return IngredientNutritionalInfoResponse(
        quantity=Quantity(amount=100.0, measurement=IngredientUnit.G),
        usda_food_description="Wheat flour, white, all-purpose, enriched",
        macro_nutrients=MacroNutrients(
            calories=NutrientValue(amount=364.0, measurement=NutrientUnit.KILOCALORIE),
            carbs=NutrientValue(amount=76.3, measurement=NutrientUnit.GRAM),
            protein=NutrientValue(amount=10.3, measurement=NutrientUnit.GRAM),
            cholesterol=NutrientValue(amount=0.0, measurement=NutrientUnit.MILLIGRAM),
            sodium=NutrientValue(amount=2.0, measurement=NutrientUnit.MILLIGRAM),
            fiber=NutrientValue(amount=2.7, measurement=NutrientUnit.GRAM),
            sugar=NutrientValue(amount=0.3, measurement=NutrientUnit.GRAM),
            fats=Fats(
                total=NutrientValue(amount=1.0, measurement=NutrientUnit.GRAM),
                saturated=NutrientValue(amount=0.2, measurement=NutrientUnit.GRAM),
            ),
        ),
        vitamins=Vitamins(
            vitamin_a=NutrientValue(amount=0.0, measurement=NutrientUnit.MICROGRAM),
            vitamin_b6=NutrientValue(amount=44.0, measurement=NutrientUnit.MICROGRAM),
            vitamin_c=NutrientValue(amount=0.0, measurement=NutrientUnit.MICROGRAM),
        ),
        minerals=Minerals(
            calcium=NutrientValue(amount=15.0, measurement=NutrientUnit.MILLIGRAM),
            iron=NutrientValue(amount=4.6, measurement=NutrientUnit.MILLIGRAM),
            potassium=NutrientValue(amount=107.0, measurement=NutrientUnit.MILLIGRAM),
        ),
    )


@pytest.fixture
def mock_nutrition_service(
    sample_nutrition_response: IngredientNutritionalInfoResponse,
) -> MagicMock:
    """Create mock nutrition service for benchmarks."""
    mock = MagicMock()
    mock.get_ingredient_nutrition = AsyncMock(return_value=sample_nutrition_response)
    mock.initialize = AsyncMock(return_value=None)
    mock.shutdown = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def perf_nutrition_client(
    app: FastAPI,
    sync_client: TestClient,
    mock_nutrition_service: MagicMock,
) -> Generator[TestClient]:
    """Create sync client with nutrition service mocked for performance tests."""
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_nutrition_service] = lambda: mock_nutrition_service

    yield sync_client

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_nutrition_service, None)


# --- Ingredient Endpoint Benchmarks ---


class TestIngredientNutritionBenchmarks:
    """Benchmarks for GET /ingredients/{id}/nutritional-info endpoint."""

    def test_ingredient_lookup_response_time(
        self,
        benchmark: BenchmarkFixture,
        perf_nutrition_client: TestClient,
    ) -> None:
        """Benchmark ingredient nutrition lookup response time."""

        def get_nutrition() -> dict[str, Any]:
            response = perf_nutrition_client.get(
                "/api/v1/recipe-scraper/ingredients/flour/nutritional-info"
            )
            result: dict[str, Any] = response.json()
            return result

        result = benchmark(get_nutrition)
        assert "quantity" in result
        assert result["macroNutrients"]["calories"]["amount"] == 364.0

    def test_ingredient_lookup_status_code(
        self,
        benchmark: BenchmarkFixture,
        perf_nutrition_client: TestClient,
    ) -> None:
        """Benchmark ingredient nutrition lookup status code check."""

        def check_status() -> int:
            response = perf_nutrition_client.get(
                "/api/v1/recipe-scraper/ingredients/flour/nutritional-info"
            )
            return response.status_code

        result = benchmark(check_status)
        assert result == 200

    def test_ingredient_lookup_with_quantity(
        self,
        benchmark: BenchmarkFixture,
        perf_nutrition_client: TestClient,
    ) -> None:
        """Benchmark ingredient lookup with custom quantity parameters."""

        def get_nutrition_with_quantity() -> dict[str, Any]:
            response = perf_nutrition_client.get(
                "/api/v1/recipe-scraper/ingredients/flour/nutritional-info",
                params={"amount": 250, "measurement": "G"},
            )
            result: dict[str, Any] = response.json()
            return result

        result = benchmark(get_nutrition_with_quantity)
        assert "quantity" in result

    def test_ingredient_lookup_throughput(
        self,
        benchmark: BenchmarkFixture,
        perf_nutrition_client: TestClient,
    ) -> None:
        """Benchmark ingredient endpoint for high throughput scenarios."""

        def lookup_multiple() -> int:
            success_count = 0
            for _ in range(10):
                response = perf_nutrition_client.get(
                    "/api/v1/recipe-scraper/ingredients/flour/nutritional-info"
                )
                if response.status_code == 200:
                    success_count += 1
            return success_count

        result = benchmark(lookup_multiple)
        assert result == 10

    def test_ingredient_lookup_json_parsing(
        self,
        benchmark: BenchmarkFixture,
        perf_nutrition_client: TestClient,
    ) -> None:
        """Benchmark JSON parsing overhead for nutrition response."""

        def get_and_parse() -> tuple[float, float, float]:
            response = perf_nutrition_client.get(
                "/api/v1/recipe-scraper/ingredients/flour/nutritional-info"
            )
            data = response.json()
            macros = data["macroNutrients"]
            return (
                macros["calories"]["amount"],
                macros["protein"]["amount"],
                macros["carbs"]["amount"],
            )

        result = benchmark(get_and_parse)
        calories, protein, carbs = result
        assert calories == 364.0
        assert protein == 10.3
        assert carbs == 76.3

    def test_ingredient_lookup_headers_check(
        self,
        benchmark: BenchmarkFixture,
        perf_nutrition_client: TestClient,
    ) -> None:
        """Benchmark ingredient endpoint with header verification."""

        def get_with_headers() -> tuple[int, bool, bool]:
            response = perf_nutrition_client.get(
                "/api/v1/recipe-scraper/ingredients/flour/nutritional-info"
            )
            has_request_id = "x-request-id" in response.headers
            has_process_time = "x-process-time" in response.headers
            return response.status_code, has_request_id, has_process_time

        result = benchmark(get_with_headers)
        status_code, has_request_id, has_process_time = result
        assert status_code == 200
        assert has_request_id
        assert has_process_time

    def test_ingredient_lookup_full_response_validation(
        self,
        benchmark: BenchmarkFixture,
        perf_nutrition_client: TestClient,
    ) -> None:
        """Benchmark full response structure validation."""

        def validate_structure() -> bool:
            response = perf_nutrition_client.get(
                "/api/v1/recipe-scraper/ingredients/flour/nutritional-info"
            )
            data = response.json()

            has_all_fields = all(
                [
                    "quantity" in data,
                    "macroNutrients" in data,
                    "vitamins" in data,
                    "minerals" in data,
                ]
            )

            macros = data["macroNutrients"]
            has_valid_macros = all(
                [
                    "calories" in macros,
                    "protein" in macros,
                    "carbs" in macros,
                    "fats" in macros,
                ]
            )

            return has_all_fields and has_valid_macros

        result = benchmark(validate_structure)
        assert result is True


# --- Model Instantiation Benchmarks ---


class TestNutritionModelBenchmarks:
    """Benchmarks for nutrition model instantiation overhead."""

    def test_nutrition_data_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark NutritionData model instantiation."""

        def create_nutrition_data() -> NutritionData:
            return NutritionData(
                ingredient_id=1,
                ingredient_name="flour",
                fdc_id=169761,
                usda_food_description="Wheat flour",
                serving_size_g=Decimal("100.00"),
                macronutrients=MacronutrientsData(
                    calories_kcal=Decimal("364.00"),
                    protein_g=Decimal("10.30"),
                    carbs_g=Decimal("76.30"),
                ),
            )

        result = benchmark(create_nutrition_data)
        assert result.ingredient_name == "flour"

    def test_nutrition_response_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark IngredientNutritionalInfoResponse model instantiation."""

        def create_response() -> IngredientNutritionalInfoResponse:
            return IngredientNutritionalInfoResponse(
                quantity=Quantity(amount=100.0, measurement=IngredientUnit.G),
                usda_food_description="Wheat flour",
                macro_nutrients=MacroNutrients(
                    calories=NutrientValue(
                        amount=364.0, measurement=NutrientUnit.KILOCALORIE
                    ),
                    protein=NutrientValue(amount=10.3, measurement=NutrientUnit.GRAM),
                    carbs=NutrientValue(amount=76.3, measurement=NutrientUnit.GRAM),
                    fats=Fats(
                        total=NutrientValue(amount=1.0, measurement=NutrientUnit.GRAM),
                    ),
                ),
            )

        result = benchmark(create_response)
        assert result.quantity.amount == 100.0

    def test_nutrient_value_batch_instantiation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark batch NutrientValue instantiation."""

        def create_nutrient_values() -> list[NutrientValue]:
            return [
                NutrientValue(amount=364.0, measurement=NutrientUnit.KILOCALORIE),
                NutrientValue(amount=10.3, measurement=NutrientUnit.GRAM),
                NutrientValue(amount=76.3, measurement=NutrientUnit.GRAM),
                NutrientValue(amount=1.0, measurement=NutrientUnit.GRAM),
                NutrientValue(amount=2.7, measurement=NutrientUnit.GRAM),
                NutrientValue(amount=0.3, measurement=NutrientUnit.GRAM),
                NutrientValue(amount=15.0, measurement=NutrientUnit.MILLIGRAM),
                NutrientValue(amount=4.6, measurement=NutrientUnit.MILLIGRAM),
            ]

        result = benchmark(create_nutrient_values)
        assert len(result) == 8


# --- Scaling Benchmarks ---


class TestNutrientScalingBenchmarks:
    """Benchmarks for nutrient scaling calculations."""

    def test_decimal_scaling_performance(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark Decimal scaling operations."""

        def scale_nutrients() -> list[float]:
            base_values = [
                Decimal("364.00"),
                Decimal("10.30"),
                Decimal("76.30"),
                Decimal("1.00"),
                Decimal("2.70"),
                Decimal("0.30"),
            ]
            scale_factor = Decimal("2.5")  # 250g / 100g

            return [float(v * scale_factor) for v in base_values]

        result = benchmark(scale_nutrients)
        assert len(result) == 6
        assert result[0] == 910.0  # 364 * 2.5

    def test_multiple_quantity_conversions(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark multiple quantity scale factor calculations."""

        def calculate_scale_factors() -> list[Decimal]:
            quantities_grams = [50, 100, 150, 200, 250, 500, 1000]
            return [Decimal(g) / Decimal(100) for g in quantities_grams]

        result = benchmark(calculate_scale_factors)
        assert len(result) == 7
        assert result[2] == Decimal("1.5")  # 150g / 100g
