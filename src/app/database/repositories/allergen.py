"""Allergen data repository.

Provides data access layer for allergen information stored in PostgreSQL.
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


class AllergenData(BaseModel):
    """Data transfer object for allergen information."""

    ingredient_id: int
    ingredient_name: str
    usda_food_description: str | None
    allergen_type: str
    presence_type: str
    confidence_score: Decimal
    source_notes: str | None
    data_source: str
    profile_confidence: Decimal


# =============================================================================
# Repository
# =============================================================================


# SQL query for fetching allergen data
_ALLERGEN_QUERY = """
    SELECT
        i.ingredient_id,
        i.name AS ingredient_name,
        i.usda_food_description,
        ap.data_source,
        ap.confidence_score AS profile_confidence,
        ia.allergen_type,
        ia.presence_type,
        ia.confidence_score,
        ia.source_notes
    FROM recipe_manager.ingredients i
    JOIN recipe_manager.allergen_profiles ap
        ON i.ingredient_id = ap.ingredient_id
    LEFT JOIN recipe_manager.ingredient_allergens ia
        ON ap.allergen_profile_id = ia.allergen_profile_id
"""


class AllergenRepository:
    """Repository for allergen data access.

    Uses raw asyncpg queries against the recipe_manager schema.
    Follows the same patterns as NutritionRepository.
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

    async def get_by_ingredient_name(
        self,
        name: str,
    ) -> list[AllergenData]:
        """Get allergen data for an ingredient by exact name match.

        Args:
            name: Ingredient name (case-insensitive).

        Returns:
            List of AllergenData for the ingredient, empty if not found.
        """
        query = f"{_ALLERGEN_QUERY} WHERE LOWER(i.name) = LOWER($1)"

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, name)
            return [
                self._row_to_allergen_data(row)
                for row in rows
                if row["allergen_type"] is not None
            ]

    async def get_by_ingredient_names(
        self,
        names: list[str],
    ) -> dict[str, list[AllergenData]]:
        """Get allergen data for multiple ingredients.

        Args:
            names: List of ingredient names.

        Returns:
            Dict mapping ingredient names to their allergen data.
        """
        if not names:
            return {}

        query = (
            f"{_ALLERGEN_QUERY} "
            "WHERE LOWER(i.name) = ANY(SELECT LOWER(unnest($1::text[])))"
        )

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, names)

        result: dict[str, list[AllergenData]] = {}
        for row in rows:
            if row["allergen_type"] is not None:
                name = row["ingredient_name"]
                if name not in result:
                    result[name] = []
                result[name].append(self._row_to_allergen_data(row))
        return result

    async def get_by_ingredient_name_fuzzy(
        self,
        name: str,
        min_similarity: float = 0.3,
    ) -> list[AllergenData]:
        """Get allergen data using fuzzy name matching.

        Uses PostgreSQL pg_trgm for similarity matching.

        Args:
            name: Ingredient name to search.
            min_similarity: Minimum trigram similarity threshold.

        Returns:
            List of AllergenData for best matching ingredient.
        """
        fuzzy_query = """
            WITH ranked_matches AS (
                SELECT
                    i.*,
                    CASE
                        WHEN LOWER(i.name) = LOWER($1) THEN 0
                        WHEN LOWER(i.name) LIKE LOWER($1) || ',%' THEN 1
                        WHEN LOWER(i.name) LIKE '%' || LOWER($1) || '%' THEN 2
                        ELSE 3
                    END AS match_rank,
                    similarity(LOWER(i.name), LOWER($1)) AS sim_score
                FROM recipe_manager.ingredients i
                WHERE
                    LOWER(i.name) = LOWER($1)
                    OR LOWER(i.name) LIKE LOWER($1) || ',%'
                    OR LOWER(i.name) LIKE '%' || LOWER($1) || '%'
                    OR similarity(LOWER(i.name), LOWER($1)) > $2
            )
            SELECT
                rm.ingredient_id,
                rm.name AS ingredient_name,
                rm.usda_food_description,
                ap.data_source,
                ap.confidence_score AS profile_confidence,
                ia.allergen_type,
                ia.presence_type,
                ia.confidence_score,
                ia.source_notes
            FROM ranked_matches rm
            JOIN recipe_manager.allergen_profiles ap
                ON rm.ingredient_id = ap.ingredient_id
            LEFT JOIN recipe_manager.ingredient_allergens ia
                ON ap.allergen_profile_id = ia.allergen_profile_id
            ORDER BY rm.match_rank, rm.sim_score DESC, LENGTH(rm.name)
            LIMIT 10
        """

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetchrow(fuzzy_query, name, min_similarity)

            if rows is None:
                return []

            # fetchrow returns a single row, but we need to handle multiple allergens
            # Re-run with fetch to get all allergen rows for the matched ingredient
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(fuzzy_query, name, min_similarity)

            result = [
                self._row_to_allergen_data(row)
                for row in rows
                if row["allergen_type"] is not None
            ]

            if result and result[0].ingredient_name.lower() != name.lower():
                logger.debug(
                    "Fuzzy match found",
                    query=name,
                    matched_name=result[0].ingredient_name,
                )
        except Exception as e:
            # Handle missing pg_trgm extension gracefully
            error_msg = str(e).lower()
            if "similarity" in error_msg and "does not exist" in error_msg:
                logger.warning(
                    "pg_trgm extension not available, fuzzy search disabled",
                    error=str(e),
                )
                return []
            raise
        else:
            return result

    @staticmethod
    def _row_to_allergen_data(row: Record) -> AllergenData:
        """Convert database row to AllergenData DTO."""
        return AllergenData(
            ingredient_id=row["ingredient_id"],
            ingredient_name=row["ingredient_name"],
            usda_food_description=row["usda_food_description"],
            allergen_type=row["allergen_type"],
            presence_type=row["presence_type"] or "CONTAINS",
            confidence_score=Decimal(str(row["confidence_score"] or "1.0")),
            source_notes=row["source_notes"],
            data_source=row["data_source"] or "USDA",
            profile_confidence=Decimal(str(row["profile_confidence"] or "1.0")),
        )
