"""Integration tests for NutritionService with real PostgreSQL and Redis.

Tests cover:
- Full nutrition lookup flow with database and caching
- Portion weight lookups from ingredient_portions table
- Cache hit/miss behavior with real Redis
- Recipe nutrition aggregation
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from redis.asyncio import Redis
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

import app.database.connection as db_module
from app.database.connection import close_database_pool, init_database_pool
from app.database.repositories.nutrition import NutritionRepository
from app.schemas.enums import IngredientUnit
from app.schemas.ingredient import Ingredient, Quantity
from app.services.nutrition.service import NutritionService


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from asyncpg import Pool

pytestmark = pytest.mark.integration


# =============================================================================
# Database Schema SQL
# =============================================================================

CREATE_TABLES_SQL = """
-- Create schema
CREATE SCHEMA IF NOT EXISTS recipe_manager;

-- Ingredients table
CREATE TABLE IF NOT EXISTS recipe_manager.ingredients (
    ingredient_id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    fdc_id INTEGER,
    usda_food_description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Nutrition profiles table
CREATE TABLE IF NOT EXISTS recipe_manager.nutrition_profiles (
    nutrition_profile_id BIGSERIAL PRIMARY KEY,
    ingredient_id BIGINT NOT NULL
        REFERENCES recipe_manager.ingredients(ingredient_id) ON DELETE CASCADE,
    serving_size_g DECIMAL(10,2) DEFAULT 100.00,
    data_source VARCHAR(50) DEFAULT 'USDA',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(ingredient_id)
);

-- Macronutrients table
CREATE TABLE IF NOT EXISTS recipe_manager.macronutrients (
    macronutrient_id BIGSERIAL PRIMARY KEY,
    nutrition_profile_id BIGINT NOT NULL
        REFERENCES recipe_manager.nutrition_profiles(nutrition_profile_id) ON DELETE CASCADE,
    calories_kcal DECIMAL(10,2),
    protein_g DECIMAL(10,2),
    carbs_g DECIMAL(10,2),
    fat_g DECIMAL(10,2),
    saturated_fat_g DECIMAL(10,2),
    trans_fat_g DECIMAL(10,2),
    monounsaturated_fat_g DECIMAL(10,2),
    polyunsaturated_fat_g DECIMAL(10,2),
    cholesterol_mg DECIMAL(10,2),
    sodium_mg DECIMAL(10,2),
    fiber_g DECIMAL(10,2),
    sugar_g DECIMAL(10,2),
    added_sugar_g DECIMAL(10,2),
    UNIQUE(nutrition_profile_id)
);

-- Vitamins table
CREATE TABLE IF NOT EXISTS recipe_manager.vitamins (
    vitamin_id BIGSERIAL PRIMARY KEY,
    nutrition_profile_id BIGINT NOT NULL
        REFERENCES recipe_manager.nutrition_profiles(nutrition_profile_id) ON DELETE CASCADE,
    vitamin_a_mcg DECIMAL(10,2),
    vitamin_b6_mcg DECIMAL(10,2),
    vitamin_b12_mcg DECIMAL(10,2),
    vitamin_c_mcg DECIMAL(10,2),
    vitamin_d_mcg DECIMAL(10,2),
    vitamin_e_mcg DECIMAL(10,2),
    vitamin_k_mcg DECIMAL(10,2),
    UNIQUE(nutrition_profile_id)
);

-- Minerals table
CREATE TABLE IF NOT EXISTS recipe_manager.minerals (
    mineral_id BIGSERIAL PRIMARY KEY,
    nutrition_profile_id BIGINT NOT NULL
        REFERENCES recipe_manager.nutrition_profiles(nutrition_profile_id) ON DELETE CASCADE,
    calcium_mg DECIMAL(10,2),
    iron_mg DECIMAL(10,2),
    magnesium_mg DECIMAL(10,2),
    potassium_mg DECIMAL(10,2),
    zinc_mg DECIMAL(10,2),
    UNIQUE(nutrition_profile_id)
);

-- Ingredient portions table (for unit conversions)
CREATE TABLE IF NOT EXISTS recipe_manager.ingredient_portions (
    id BIGSERIAL PRIMARY KEY,
    ingredient_id BIGINT NOT NULL
        REFERENCES recipe_manager.ingredients(ingredient_id) ON DELETE CASCADE,
    portion_description VARCHAR(255) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    modifier VARCHAR(100),
    gram_weight DECIMAL(10,3) NOT NULL,
    sequence_number INT,
    data_source VARCHAR(50) DEFAULT 'USDA',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(ingredient_id, portion_description)
);

CREATE INDEX IF NOT EXISTS idx_ingredient_portions_ingredient_id
    ON recipe_manager.ingredient_portions(ingredient_id);
CREATE INDEX IF NOT EXISTS idx_ingredient_portions_unit
    ON recipe_manager.ingredient_portions(unit);
"""

INSERT_TEST_DATA_SQL = """
-- Insert test ingredients
INSERT INTO recipe_manager.ingredients (ingredient_id, name, fdc_id, usda_food_description) VALUES
    (1, 'flour', 169761, 'Wheat flour, white, all-purpose, enriched'),
    (2, 'sugar', 169655, 'Sugar, granulated'),
    (3, 'apple', 171688, 'Apples, raw, with skin'),
    (4, 'garlic', 169230, 'Garlic, raw')
ON CONFLICT (name) DO NOTHING;

-- Insert nutrition profiles
INSERT INTO recipe_manager.nutrition_profiles (nutrition_profile_id, ingredient_id, serving_size_g, data_source) VALUES
    (1, 1, 100.00, 'USDA'),
    (2, 2, 100.00, 'USDA'),
    (3, 3, 100.00, 'USDA'),
    (4, 4, 100.00, 'USDA')
ON CONFLICT (ingredient_id) DO NOTHING;

-- Insert macronutrients (per 100g)
INSERT INTO recipe_manager.macronutrients (nutrition_profile_id, calories_kcal, protein_g, carbs_g, fat_g, fiber_g, sugar_g) VALUES
    (1, 364, 10.3, 76.3, 1.0, 2.7, 0.3),   -- flour
    (2, 387, 0.0, 100.0, 0.0, 0.0, 100.0), -- sugar
    (3, 52, 0.3, 13.8, 0.2, 2.4, 10.4),    -- apple
    (4, 149, 6.4, 33.1, 0.5, 2.1, 1.0)     -- garlic
ON CONFLICT (nutrition_profile_id) DO NOTHING;

-- Insert vitamins
INSERT INTO recipe_manager.vitamins (nutrition_profile_id, vitamin_c_mcg, vitamin_b6_mcg) VALUES
    (1, 0, 44),
    (3, 4600, 41)  -- apple has vitamin C
ON CONFLICT (nutrition_profile_id) DO NOTHING;

-- Insert minerals
INSERT INTO recipe_manager.minerals (nutrition_profile_id, calcium_mg, iron_mg, potassium_mg) VALUES
    (1, 15, 4.6, 107),
    (3, 6, 0.1, 107)  -- apple
ON CONFLICT (nutrition_profile_id) DO NOTHING;

-- Insert portion weights (for unit conversions)
INSERT INTO recipe_manager.ingredient_portions (ingredient_id, portion_description, unit, modifier, gram_weight) VALUES
    (1, '1 cup', 'CUP', NULL, 125.0),           -- 1 cup flour = 125g
    (1, '1 tablespoon', 'TBSP', NULL, 7.8),     -- 1 tbsp flour = 7.8g
    (2, '1 cup', 'CUP', NULL, 200.0),           -- 1 cup sugar = 200g
    (2, '1 teaspoon', 'TSP', NULL, 4.2),        -- 1 tsp sugar = 4.2g
    (3, '1 medium', 'PIECE', 'medium', 182.0),  -- 1 medium apple = 182g
    (3, '1 cup, sliced', 'CUP', 'sliced', 109.0), -- 1 cup sliced apple = 109g
    (4, '1 clove', 'CLOVE', NULL, 3.0)          -- 1 clove garlic = 3g
ON CONFLICT (ingredient_id, portion_description) DO NOTHING;
"""


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer]:
    """Start a PostgreSQL container for the test session."""
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def redis_container() -> Generator[RedisContainer]:
    """Start a Redis container for the test session."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


@pytest.fixture(scope="session")
def postgres_config(postgres_container: PostgresContainer) -> dict[str, str | int]:
    """Get PostgreSQL connection config from container."""
    return {
        "host": postgres_container.get_container_host_ip(),
        "port": int(postgres_container.get_exposed_port(5432)),
        "user": "test",
        "password": "test",
        "database": "test",
    }


@pytest.fixture(scope="session")
def redis_url(redis_container: RedisContainer) -> str:
    """Get the Redis URL from the container."""
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    return f"redis://{host}:{port}"


@pytest.fixture
async def db_pool(postgres_config: dict[str, str | int]) -> AsyncGenerator[Pool]:
    """Initialize database pool and create schema."""
    mock_settings = MagicMock()
    mock_settings.database.host = postgres_config["host"]
    mock_settings.database.port = postgres_config["port"]
    mock_settings.database.name = postgres_config["database"]
    mock_settings.database.user = postgres_config["user"]
    mock_settings.database.min_pool_size = 1
    mock_settings.database.max_pool_size = 5
    mock_settings.database.command_timeout = 30.0
    mock_settings.database.ssl = False
    mock_settings.DATABASE_PASSWORD = postgres_config["password"]

    with patch("app.database.connection.get_settings", return_value=mock_settings):
        await init_database_pool()

        # Create tables and insert test data
        pool = db_module._pool
        async with pool.acquire() as conn:
            await conn.execute(CREATE_TABLES_SQL)
            await conn.execute(INSERT_TEST_DATA_SQL)

        yield pool

        await close_database_pool()


@pytest.fixture
async def cache_client(redis_url: str) -> AsyncGenerator[Redis[bytes]]:
    """Create a Redis client connected to the test container."""
    client: Redis[bytes] = Redis.from_url(redis_url, decode_responses=False)
    # Clear any existing cache data
    await client.flushdb()
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
async def repository(db_pool: Pool) -> NutritionRepository:
    """Create NutritionRepository with test database pool."""
    return NutritionRepository(pool=db_pool)


@pytest.fixture
async def service(
    cache_client: Redis[bytes],
    repository: NutritionRepository,
) -> AsyncGenerator[NutritionService]:
    """Create NutritionService with real Redis and PostgreSQL."""
    svc = NutritionService(
        cache_client=cache_client,
        repository=repository,
    )
    await svc.initialize()
    yield svc
    await svc.shutdown()


# =============================================================================
# Repository Tests
# =============================================================================


class TestNutritionRepositoryIntegration:
    """Integration tests for NutritionRepository."""

    async def test_get_by_ingredient_name(
        self, repository: NutritionRepository
    ) -> None:
        """Should retrieve nutrition data by ingredient name."""
        result = await repository.get_by_ingredient_name("flour")

        assert result is not None
        assert result.ingredient_name == "flour"
        assert result.fdc_id == 169761
        assert result.macronutrients is not None
        assert result.macronutrients.calories_kcal == Decimal("364.00")
        assert result.macronutrients.protein_g == Decimal("10.30")

    async def test_get_by_ingredient_name_case_insensitive(
        self, repository: NutritionRepository
    ) -> None:
        """Should match ingredient name case-insensitively."""
        result = await repository.get_by_ingredient_name("FLOUR")

        assert result is not None
        assert result.ingredient_name == "flour"

    async def test_get_by_ingredient_name_not_found(
        self, repository: NutritionRepository
    ) -> None:
        """Should return None for unknown ingredient."""
        result = await repository.get_by_ingredient_name("unknown-ingredient")

        assert result is None

    async def test_get_by_ingredient_names_batch(
        self, repository: NutritionRepository
    ) -> None:
        """Should retrieve multiple ingredients in batch."""
        result = await repository.get_by_ingredient_names(["flour", "sugar", "apple"])

        assert len(result) == 3
        assert "flour" in result
        assert "sugar" in result
        assert "apple" in result

    async def test_get_portion_weight_cup_flour(
        self, repository: NutritionRepository
    ) -> None:
        """Should retrieve portion weight for 1 cup flour."""
        result = await repository.get_portion_weight("flour", "CUP")

        assert result is not None
        assert result == Decimal("125.000")

    async def test_get_portion_weight_clove_garlic(
        self, repository: NutritionRepository
    ) -> None:
        """Should retrieve portion weight for 1 clove garlic."""
        result = await repository.get_portion_weight("garlic", "CLOVE")

        assert result is not None
        assert result == Decimal("3.000")

    async def test_get_portion_weight_not_found(
        self, repository: NutritionRepository
    ) -> None:
        """Should return None for unknown portion."""
        result = await repository.get_portion_weight("flour", "UNKNOWN_UNIT")

        assert result is None


# =============================================================================
# Service Tests
# =============================================================================


class TestNutritionServiceIntegration:
    """Integration tests for NutritionService with caching."""

    async def test_get_ingredient_nutrition_with_gram_quantity(
        self, service: NutritionService
    ) -> None:
        """Should return scaled nutrition for gram quantity."""
        quantity = Quantity(amount=200, measurement=IngredientUnit.G)
        result = await service.get_ingredient_nutrition("flour", quantity)

        assert result is not None
        assert result.quantity == quantity
        assert result.macro_nutrients is not None
        # 364 kcal per 100g * 2 = 728 kcal
        assert result.macro_nutrients.calories is not None
        assert result.macro_nutrients.calories.amount == pytest.approx(728, rel=0.01)

    async def test_get_ingredient_nutrition_with_cup_quantity(
        self, service: NutritionService
    ) -> None:
        """Should use portion weight for cup conversion."""
        quantity = Quantity(amount=1, measurement=IngredientUnit.CUP)
        result = await service.get_ingredient_nutrition("flour", quantity)

        assert result is not None
        # 1 cup flour = 125g, so 364 * 1.25 = 455 kcal
        assert result.macro_nutrients is not None
        assert result.macro_nutrients.calories is not None
        assert result.macro_nutrients.calories.amount == pytest.approx(455, rel=0.01)

    async def test_get_ingredient_nutrition_caches_result(
        self,
        service: NutritionService,
        cache_client: Redis[bytes],
    ) -> None:
        """Should cache nutrition data after first lookup."""
        quantity = Quantity(amount=100, measurement=IngredientUnit.G)

        # First call - should query database
        result1 = await service.get_ingredient_nutrition("sugar", quantity)
        assert result1 is not None

        # Verify cache was populated
        cache_key = "nutrition:sugar"
        cached = await cache_client.get(cache_key)
        assert cached is not None

        # Second call - should use cache
        result2 = await service.get_ingredient_nutrition("sugar", quantity)
        assert result2 is not None
        assert (
            result2.macro_nutrients.calories.amount
            == result1.macro_nutrients.calories.amount
        )

    async def test_get_ingredient_nutrition_not_found(
        self, service: NutritionService
    ) -> None:
        """Should return None for unknown ingredient."""
        quantity = Quantity(amount=100, measurement=IngredientUnit.G)
        result = await service.get_ingredient_nutrition("unknown-ingredient", quantity)

        assert result is None


class TestRecipeNutritionIntegration:
    """Integration tests for recipe nutrition aggregation."""

    async def test_get_recipe_nutrition_multiple_ingredients(
        self, service: NutritionService
    ) -> None:
        """Should aggregate nutrition from multiple ingredients."""
        ingredients = [
            Ingredient(
                ingredient_id=1,
                name="flour",
                quantity=Quantity(amount=2, measurement=IngredientUnit.CUP),
            ),
            Ingredient(
                ingredient_id=2,
                name="sugar",
                quantity=Quantity(amount=1, measurement=IngredientUnit.CUP),
            ),
        ]

        result = await service.get_recipe_nutrition(ingredients)

        assert result.ingredients is not None
        assert len(result.ingredients) == 2
        assert "flour" in result.ingredients
        assert "sugar" in result.ingredients

        # Total should be sum of both
        # 2 cups flour = 250g @ 364 kcal/100g = 910 kcal
        # 1 cup sugar = 200g @ 387 kcal/100g = 774 kcal
        # Total = 1684 kcal
        assert result.total.macro_nutrients is not None
        assert result.total.macro_nutrients.calories is not None
        assert result.total.macro_nutrients.calories.amount == pytest.approx(
            1684, rel=0.02
        )

    async def test_get_recipe_nutrition_with_missing_ingredient(
        self, service: NutritionService
    ) -> None:
        """Should track missing ingredients."""
        ingredients = [
            Ingredient(
                ingredient_id=1,
                name="flour",
                quantity=Quantity(amount=100, measurement=IngredientUnit.G),
            ),
            Ingredient(
                ingredient_id=99,
                name="unicorn-tears",  # Doesn't exist
                quantity=Quantity(amount=50, measurement=IngredientUnit.ML),
            ),
        ]

        result = await service.get_recipe_nutrition(ingredients)

        assert result.ingredients is not None
        assert "flour" in result.ingredients
        assert result.missing_ingredients is not None
        assert 99 in result.missing_ingredients

    async def test_get_recipe_nutrition_with_count_units(
        self, service: NutritionService
    ) -> None:
        """Should handle count-based units like PIECE and CLOVE."""
        ingredients = [
            Ingredient(
                ingredient_id=3,
                name="apple",
                quantity=Quantity(amount=2, measurement=IngredientUnit.PIECE),
            ),
            Ingredient(
                ingredient_id=4,
                name="garlic",
                quantity=Quantity(amount=3, measurement=IngredientUnit.CLOVE),
            ),
        ]

        result = await service.get_recipe_nutrition(ingredients)

        assert result.ingredients is not None
        assert len(result.ingredients) == 2

        # 2 medium apples = 364g @ 52 kcal/100g = 189 kcal
        # 3 cloves garlic = 9g @ 149 kcal/100g = 13 kcal
        # Total ≈ 202 kcal
        assert result.total.macro_nutrients is not None
        assert result.total.macro_nutrients.calories is not None
        assert result.total.macro_nutrients.calories.amount == pytest.approx(
            202, rel=0.05
        )
