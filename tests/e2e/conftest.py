"""E2E test fixtures.

Provides fixtures for end-to-end testing with full system integration.
"""

from __future__ import annotations

import contextlib
import os
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from arq import create_pool
from arq.connections import RedisSettings as ArqRedisSettings
from httpx import ASGITransport, AsyncClient
from prometheus_client import REGISTRY
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

import app.cache.redis as redis_module
import app.database.connection as db_module
from app.auth.jwt import create_access_token
from app.cache.redis import close_redis_pools, init_redis_pools
from app.core.config import Settings
from app.core.config.settings import (
    ApiSettings,
    AppSettings,
    AuthSettings,
    LoggingSettings,
    ObservabilitySettings,
    RateLimitingSettings,
    RedisSettings,
    ServerSettings,
)
from app.database.connection import close_database_pool, init_database_pool
from app.factory import create_app


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from arq import ArqRedis
    from asyncpg import Pool
    from fastapi import FastAPI


pytestmark = pytest.mark.e2e


@pytest.fixture(scope="session")
def redis_container() -> Generator[RedisContainer]:
    """Start a Redis container for the test session."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


@pytest.fixture(scope="session")
def redis_url(redis_container: RedisContainer) -> str:
    """Get the Redis URL from the container."""
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    return f"redis://{host}:{port}"


@pytest.fixture
def test_settings(redis_url: str) -> Settings:
    """Create test settings with Redis container URLs."""
    parts = redis_url.replace("redis://", "").split(":")
    redis_host = parts[0]
    redis_port = int(parts[1])

    return Settings(
        APP_ENV="test",
        JWT_SECRET_KEY="e2e-test-jwt-secret-key",
        REDIS_PASSWORD="",
        app=AppSettings(
            name="e2e-test-app",
            version="0.0.1-e2e",
            debug=True,
        ),
        server=ServerSettings(
            host="0.0.0.0",
            port=8000,
        ),
        api=ApiSettings(
            cors_origins=["http://localhost:3000"],
        ),
        auth=AuthSettings(
            mode="disabled",
        ),
        redis=RedisSettings(
            host=redis_host,
            port=redis_port,
            cache_db=0,
            queue_db=1,
            rate_limit_db=2,
        ),
        rate_limiting=RateLimitingSettings(
            default="100/minute",
            auth="10/minute",
        ),
        logging=LoggingSettings(
            level="DEBUG",
            format="json",
        ),
        observability=ObservabilitySettings(),
    )


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    """Create FastAPI app with test settings.

    Sets METRICS_ENABLED env var since prometheus-fastapi-instrumentator
    checks this when should_respect_env_var=True.
    """
    original_metrics_enabled = os.environ.get("METRICS_ENABLED")
    os.environ["METRICS_ENABLED"] = "true"

    try:
        with (
            patch("app.observability.metrics.get_settings", return_value=test_settings),
            patch("app.observability.tracing.get_settings", return_value=test_settings),
        ):
            return create_app(test_settings)
    finally:
        if original_metrics_enabled is None:
            os.environ.pop("METRICS_ENABLED", None)
        else:
            os.environ["METRICS_ENABLED"] = original_metrics_enabled


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """Create async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
async def authenticated_client(
    client: AsyncClient,
    test_settings: Settings,
) -> AsyncGenerator[AsyncClient]:
    """Create authenticated client with valid access token.

    Since auth endpoints are now handled by the external auth-service,
    we create tokens directly using the JWT module.
    """
    with patch("app.auth.jwt.get_settings", return_value=test_settings):
        token = create_access_token(
            subject="e2e-test-user",
            roles=["user"],
            permissions=["recipe:read", "recipe:write"],
        )
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture
async def arq_pool(redis_url: str) -> AsyncGenerator[ArqRedis]:
    """Create ARQ connection pool for e2e tests."""
    parts = redis_url.replace("redis://", "").split(":")
    host = parts[0]
    port = int(parts[1])

    pool = await create_pool(
        ArqRedisSettings(host=host, port=port, database=1),
    )
    yield pool
    await pool.aclose()


@pytest.fixture
async def initialized_redis(
    test_settings: Settings,
) -> AsyncGenerator[None]:
    """Initialize Redis pools for e2e tests."""
    with patch("app.cache.redis.get_settings", return_value=test_settings):
        await init_redis_pools()

    yield

    await close_redis_pools()


@pytest.fixture(autouse=True)
async def reset_redis_state() -> AsyncGenerator[None]:
    """Reset Redis module state before and after each test."""
    redis_module._cache_pool = None
    redis_module._queue_pool = None
    redis_module._rate_limit_pool = None
    redis_module._cache_client = None
    redis_module._queue_client = None
    redis_module._rate_limit_client = None

    yield

    await close_redis_pools()


@pytest.fixture(autouse=True)
def reset_prometheus_registry() -> Generator[None]:
    """Reset Prometheus registry between tests.

    This prevents 'Duplicated timeseries' errors when creating
    multiple app instances in tests.
    """

    # Collect all collector names before test
    collectors_before = set(REGISTRY._names_to_collectors.keys())

    yield

    # Remove any collectors added during the test
    collectors_to_remove = []
    for name, collector in list(REGISTRY._names_to_collectors.items()):
        if name not in collectors_before:
            collectors_to_remove.append(collector)

    for collector in collectors_to_remove:
        with contextlib.suppress(Exception):
            REGISTRY.unregister(collector)


# =============================================================================
# PostgreSQL Fixtures for Nutrition E2E Tests
# =============================================================================

# Database schema SQL
NUTRITION_SCHEMA_SQL = """
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

# Seed data with common ingredients (USDA FoodData Central values per 100g)
COMMON_INGREDIENTS_SQL = """
-- Insert common ingredients (flour, butter, eggs, chicken, rice)
INSERT INTO recipe_manager.ingredients (ingredient_id, name, fdc_id, usda_food_description) VALUES
    (1, 'flour', 169761, 'Wheat flour, white, all-purpose, enriched'),
    (2, 'butter', 173410, 'Butter, salted'),
    (3, 'eggs', 173424, 'Egg, whole, raw, fresh'),
    (4, 'chicken', 171052, 'Chicken, broiler or fryers, breast, skinless, boneless, meat only, raw'),
    (5, 'rice', 169756, 'Rice, white, long-grain, regular, cooked')
ON CONFLICT (name) DO NOTHING;

-- Insert nutrition profiles
INSERT INTO recipe_manager.nutrition_profiles (nutrition_profile_id, ingredient_id, serving_size_g, data_source) VALUES
    (1, 1, 100.00, 'USDA'),
    (2, 2, 100.00, 'USDA'),
    (3, 3, 100.00, 'USDA'),
    (4, 4, 100.00, 'USDA'),
    (5, 5, 100.00, 'USDA')
ON CONFLICT (ingredient_id) DO NOTHING;

-- Insert macronutrients (USDA values per 100g)
INSERT INTO recipe_manager.macronutrients (
    nutrition_profile_id, calories_kcal, protein_g, carbs_g, fat_g,
    saturated_fat_g, fiber_g, sugar_g, cholesterol_mg, sodium_mg
) VALUES
    -- Flour: 364 kcal, 10.3g protein, 76.3g carbs, 1.0g fat
    (1, 364, 10.3, 76.3, 1.0, 0.2, 2.7, 0.3, 0, 2),
    -- Butter: 717 kcal, 0.9g protein, 0.1g carbs, 81.1g fat
    (2, 717, 0.9, 0.1, 81.1, 51.4, 0, 0.1, 215, 714),
    -- Eggs: 155 kcal, 13.0g protein, 1.1g carbs, 11.0g fat
    (3, 155, 13.0, 1.1, 11.0, 3.3, 0, 1.1, 373, 124),
    -- Chicken breast: 165 kcal, 31.0g protein, 0g carbs, 3.6g fat
    (4, 165, 31.0, 0, 3.6, 1.0, 0, 0, 85, 74),
    -- Rice (cooked): 130 kcal, 2.7g protein, 28.2g carbs, 0.3g fat
    (5, 130, 2.7, 28.2, 0.3, 0.1, 0.4, 0, 0, 1)
ON CONFLICT (nutrition_profile_id) DO NOTHING;

-- Insert vitamins
INSERT INTO recipe_manager.vitamins (
    nutrition_profile_id, vitamin_a_mcg, vitamin_c_mcg, vitamin_d_mcg, vitamin_b6_mcg, vitamin_b12_mcg
) VALUES
    (1, 0, 0, 0, 44, 0),        -- Flour
    (2, 684, 0, 1.5, 3, 0.17),  -- Butter (high vitamin A)
    (3, 160, 0, 2.0, 170, 0.89), -- Eggs
    (4, 6, 0, 0.1, 600, 0.34),  -- Chicken
    (5, 0, 0, 0, 93, 0)         -- Rice
ON CONFLICT (nutrition_profile_id) DO NOTHING;

-- Insert minerals
INSERT INTO recipe_manager.minerals (
    nutrition_profile_id, calcium_mg, iron_mg, magnesium_mg, potassium_mg, zinc_mg
) VALUES
    (1, 15, 4.6, 22, 107, 0.7),   -- Flour
    (2, 24, 0.02, 2, 24, 0.09),   -- Butter
    (3, 56, 1.75, 12, 138, 1.29), -- Eggs
    (4, 15, 1.04, 29, 256, 1.0),  -- Chicken
    (5, 10, 0.2, 12, 35, 0.49)    -- Rice
ON CONFLICT (nutrition_profile_id) DO NOTHING;

-- Insert portion weights for unit conversions
INSERT INTO recipe_manager.ingredient_portions (ingredient_id, portion_description, unit, modifier, gram_weight) VALUES
    -- Flour portions
    (1, '1 cup', 'CUP', NULL, 125.0),
    (1, '1 tablespoon', 'TBSP', NULL, 7.8),
    (1, '1 teaspoon', 'TSP', NULL, 2.6),
    -- Butter portions
    (2, '1 tablespoon', 'TBSP', NULL, 14.2),
    (2, '1 cup', 'CUP', NULL, 227.0),
    (2, '1 stick', 'PIECE', 'stick', 113.0),
    -- Egg portions
    (3, '1 large', 'PIECE', 'large', 50.0),
    (3, '1 medium', 'PIECE', 'medium', 44.0),
    -- Chicken portions
    (4, '1 breast', 'PIECE', 'breast', 174.0),
    (4, '1 oz', 'OZ', NULL, 28.35),
    -- Rice portions
    (5, '1 cup', 'CUP', 'cooked', 158.0)
ON CONFLICT (ingredient_id, portion_description) DO NOTHING;
"""


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer]:
    """Start a PostgreSQL container for the test session."""
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres


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


@pytest.fixture
async def nutrition_db_pool(
    postgres_config: dict[str, str | int],
) -> AsyncGenerator[Pool]:
    """Initialize database pool with nutrition schema and common ingredients."""
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

        # Create schema and seed with common ingredients
        pool = db_module._pool
        assert pool is not None, "Database pool initialization failed"
        async with pool.acquire() as conn:
            await conn.execute(NUTRITION_SCHEMA_SQL)
            await conn.execute(COMMON_INGREDIENTS_SQL)

        yield pool

        await close_database_pool()
