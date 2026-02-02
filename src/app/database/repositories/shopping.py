"""Shopping/pricing data repository.

Provides data access layer for ingredient pricing information stored in PostgreSQL.
Uses a two-tier lookup strategy:
- Tier 1: Direct ingredient pricing from ingredient_pricing table
- Tier 2: Food group average pricing from food_group_pricing table
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel

from app.database.connection import get_database_pool
from app.observability.logging import get_logger


if TYPE_CHECKING:
    from asyncpg import Pool, Record

logger = get_logger(__name__)


# =============================================================================
# Data Transfer Objects
# =============================================================================


class PricingData(BaseModel):
    """Data transfer object for pricing information."""

    price_per_100g: Decimal
    currency: str
    data_source: str
    source_year: int | None = None
    tier: int  # 1 for direct ingredient, 2 for food group fallback


class IngredientDetails(BaseModel):
    """Data transfer object for ingredient details needed for pricing lookup."""

    ingredient_id: int
    name: str
    food_group: str | None = None


# =============================================================================
# Repository
# =============================================================================


class PricingRepository:
    """Repository for pricing data access.

    Uses raw asyncpg queries against the recipe_manager schema.
    Implements two-tier pricing lookup strategy.
    """

    def __init__(self, pool: Pool | None = None) -> None:
        """Initialize repository with optional connection pool.

        Args:
            pool: asyncpg connection pool. If None, uses global pool.
        """
        self._pool = pool

    @property
    def pool(self) -> Pool:
        """Get the database connection pool."""
        if self._pool is not None:
            return self._pool
        return get_database_pool()

    async def get_price_by_ingredient_id(
        self,
        ingredient_id: int,
    ) -> PricingData | None:
        """Get pricing data for an ingredient by ID (Tier 1 lookup).

        Args:
            ingredient_id: The ingredient's database ID.

        Returns:
            PricingData if found, None otherwise.
        """
        query = """
            SELECT
                price_per_100g,
                currency,
                data_source,
                source_year
            FROM recipe_manager.ingredient_pricing
            WHERE ingredient_id = $1
        """

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, ingredient_id)

            if row is None:
                return None

            return self._row_to_pricing_data(row, tier=1)

        except Exception as e:
            # Handle missing table gracefully
            error_msg = str(e).lower()
            if "relation" in error_msg and "does not exist" in error_msg:
                logger.debug(
                    "ingredient_pricing table not found",
                    ingredient_id=ingredient_id,
                )
                return None
            raise

    async def get_price_by_food_group(
        self,
        food_group: str,
    ) -> PricingData | None:
        """Get average pricing data for a food group (Tier 2 fallback).

        Args:
            food_group: The food group name (e.g., "VEGETABLES", "FRUITS").

        Returns:
            PricingData if found, None otherwise.
        """
        query = """
            SELECT
                avg_price_per_100g AS price_per_100g,
                currency,
                data_source
            FROM recipe_manager.food_group_pricing
            WHERE food_group = $1::recipe_manager.food_group_enum
        """

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, food_group)

            if row is None:
                return None

            return self._row_to_pricing_data(row, tier=2)

        except Exception as e:
            # Handle missing table or invalid enum gracefully
            error_msg = str(e).lower()
            if "relation" in error_msg and "does not exist" in error_msg:
                logger.debug(
                    "food_group_pricing table not found",
                    food_group=food_group,
                )
                return None
            if "invalid input value for enum" in error_msg:
                logger.debug(
                    "Invalid food group enum value",
                    food_group=food_group,
                )
                return None
            raise

    async def get_ingredient_details(
        self,
        ingredient_id: int,
    ) -> IngredientDetails | None:
        """Get ingredient details by ID (name and food group).

        Args:
            ingredient_id: The ingredient's database ID.

        Returns:
            IngredientDetails if found, None otherwise.
        """
        query = """
            SELECT
                i.ingredient_id,
                i.name,
                np.food_group
            FROM recipe_manager.ingredients i
            LEFT JOIN recipe_manager.nutrition_profiles np
                ON np.ingredient_id = i.ingredient_id
            WHERE i.ingredient_id = $1
        """

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, ingredient_id)

            if row is None:
                return None

            return IngredientDetails(
                ingredient_id=row["ingredient_id"],
                name=row["name"],
                food_group=row["food_group"],
            )

        except Exception as e:
            # Handle missing table gracefully
            error_msg = str(e).lower()
            if "relation" in error_msg and "does not exist" in error_msg:
                logger.debug(
                    "ingredients table not found",
                    ingredient_id=ingredient_id,
                )
                return None
            raise

    @staticmethod
    def _row_to_pricing_data(row: Record, tier: int) -> PricingData:
        """Convert database row to PricingData DTO.

        Args:
            row: Database record.
            tier: Pricing tier (1 for direct, 2 for food group).

        Returns:
            PricingData object.
        """
        return PricingData(
            price_per_100g=Decimal(str(row["price_per_100g"])),
            currency=row["currency"],
            data_source=row["data_source"],
            source_year=row.get("source_year"),
            tier=tier,
        )
