"""Nutrition data repository.

Provides methods for querying nutrition data from the PostgreSQL database.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from app.database.connection import get_database_pool
from app.observability.logging import get_logger


if TYPE_CHECKING:
    from asyncpg import Pool, Record

logger = get_logger(__name__)


# =============================================================================
# Data Transfer Objects
# =============================================================================


class MacronutrientsData(BaseModel):
    """Macronutrient data from database."""

    calories_kcal: Decimal | None = None
    protein_g: Decimal | None = None
    carbs_g: Decimal | None = None
    fat_g: Decimal | None = None
    saturated_fat_g: Decimal | None = None
    trans_fat_g: Decimal | None = None
    monounsaturated_fat_g: Decimal | None = None
    polyunsaturated_fat_g: Decimal | None = None
    cholesterol_mg: Decimal | None = None
    sodium_mg: Decimal | None = None
    fiber_g: Decimal | None = None
    sugar_g: Decimal | None = None
    added_sugar_g: Decimal | None = None


class VitaminsData(BaseModel):
    """Vitamin data from database."""

    vitamin_a_mcg: Decimal | None = None
    vitamin_b6_mcg: Decimal | None = None
    vitamin_b12_mcg: Decimal | None = None
    vitamin_c_mcg: Decimal | None = None
    vitamin_d_mcg: Decimal | None = None
    vitamin_e_mcg: Decimal | None = None
    vitamin_k_mcg: Decimal | None = None


class MineralsData(BaseModel):
    """Mineral data from database."""

    calcium_mg: Decimal | None = None
    iron_mg: Decimal | None = None
    magnesium_mg: Decimal | None = None
    potassium_mg: Decimal | None = None
    zinc_mg: Decimal | None = None


class PortionData(BaseModel):
    """Portion weight data from database.

    Represents a single portion measurement (e.g., "1 cup chopped" = 160g).
    Data sourced from USDA FoodData Central Food Weights.
    """

    ingredient_id: int
    portion_description: str
    unit: str
    modifier: str | None = None
    gram_weight: Decimal


class NutritionData(BaseModel):
    """Complete nutrition data for an ingredient."""

    ingredient_id: int
    ingredient_name: str
    fdc_id: int | None = None
    usda_food_description: str | None = None
    serving_size_g: Decimal = Field(default=Decimal("100.00"))
    data_source: str = "USDA"
    macronutrients: MacronutrientsData | None = None
    vitamins: VitaminsData | None = None
    minerals: MineralsData | None = None


# =============================================================================
# Repository
# =============================================================================


# SQL query for fetching nutrition data
_NUTRITION_QUERY = """
    SELECT
        i.ingredient_id,
        i.name AS ingredient_name,
        i.fdc_id,
        i.usda_food_description,
        np.serving_size_g,
        np.data_source,
        -- Macronutrients
        m.calories_kcal,
        m.protein_g,
        m.carbs_g,
        m.fat_g,
        m.saturated_fat_g,
        m.trans_fat_g,
        m.monounsaturated_fat_g,
        m.polyunsaturated_fat_g,
        m.cholesterol_mg,
        m.sodium_mg,
        m.fiber_g,
        m.sugar_g,
        m.added_sugar_g,
        -- Vitamins
        v.vitamin_a_mcg,
        v.vitamin_b6_mcg,
        v.vitamin_b12_mcg,
        v.vitamin_c_mcg,
        v.vitamin_d_mcg,
        v.vitamin_e_mcg,
        v.vitamin_k_mcg,
        -- Minerals
        min.calcium_mg,
        min.iron_mg,
        min.magnesium_mg,
        min.potassium_mg,
        min.zinc_mg
    FROM recipe_manager.ingredients i
    LEFT JOIN recipe_manager.nutrition_profiles np
        ON np.ingredient_id = i.ingredient_id
    LEFT JOIN recipe_manager.macronutrients m
        ON m.nutrition_profile_id = np.nutrition_profile_id
    LEFT JOIN recipe_manager.vitamins v
        ON v.nutrition_profile_id = np.nutrition_profile_id
    LEFT JOIN recipe_manager.minerals min
        ON min.nutrition_profile_id = np.nutrition_profile_id
"""


class NutritionRepository:
    """Repository for querying nutrition data.

    Provides methods for fetching nutrition information from the database.
    Handles NULL values from LEFT JOINs by returning None for missing data.
    """

    def __init__(self, pool: Pool | None = None) -> None:
        """Initialize repository.

        Args:
            pool: Optional connection pool. If None, uses global pool.
        """
        self._pool = pool

    @property
    def pool(self) -> Pool:
        """Get connection pool."""
        if self._pool is not None:
            return self._pool
        return get_database_pool()

    async def get_by_ingredient_name(
        self,
        name: str,
    ) -> NutritionData | None:
        """Get nutrition data for an ingredient by name.

        Args:
            name: Ingredient name (case-insensitive match).

        Returns:
            NutritionData if found, None otherwise.
        """
        query = f"{_NUTRITION_QUERY} WHERE LOWER(i.name) = LOWER($1) LIMIT 1"

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, name)

        if row is None:
            return None

        return self._row_to_nutrition_data(row)

    async def get_by_ingredient_names(
        self,
        names: list[str],
    ) -> dict[str, NutritionData]:
        """Get nutrition data for multiple ingredients.

        Args:
            names: List of ingredient names.

        Returns:
            Dictionary mapping ingredient names to NutritionData.
            Missing ingredients are not included in the result.
        """
        if not names:
            return {}

        query = (
            f"{_NUTRITION_QUERY} "
            "WHERE LOWER(i.name) = ANY(SELECT LOWER(unnest($1::text[])))"
        )

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, names)

        return {
            row["ingredient_name"]: self._row_to_nutrition_data(row) for row in rows
        }

    async def get_by_fdc_id(self, fdc_id: int) -> NutritionData | None:
        """Get nutrition data by USDA FDC ID.

        Args:
            fdc_id: USDA FoodData Central ID.

        Returns:
            NutritionData if found, None otherwise.
        """
        query = f"{_NUTRITION_QUERY} WHERE i.fdc_id = $1 LIMIT 1"

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, fdc_id)

        if row is None:
            return None

        return self._row_to_nutrition_data(row)

    async def get_portion_weight(
        self,
        ingredient_name: str,
        unit: str,
        modifier: str | None = None,
    ) -> Decimal | None:
        """Get gram weight for a portion measurement.

        Looks up portion data from the ingredient_portions table.
        Used for converting volume and count units to grams.

        Args:
            ingredient_name: Ingredient name (case-insensitive match).
            unit: Unit type (e.g., "CUP", "PIECE", "TBSP").
            modifier: Optional modifier (e.g., "chopped", "medium", "sliced").

        Returns:
            Gram weight for the portion, or None if not found.

        Note:
            Gracefully handles missing ingredient_portions table by returning None.
        """
        try:
            async with self.pool.acquire() as conn:
                if modifier:
                    # Query with modifier if provided
                    query = """
                        SELECT ip.gram_weight
                        FROM recipe_manager.ingredient_portions ip
                        JOIN recipe_manager.ingredients i
                            ON i.ingredient_id = ip.ingredient_id
                        WHERE LOWER(i.name) = LOWER($1)
                          AND UPPER(ip.unit) = UPPER($2)
                          AND LOWER(ip.modifier) = LOWER($3)
                        ORDER BY ip.sequence_number NULLS LAST
                        LIMIT 1
                    """
                    row = await conn.fetchrow(query, ingredient_name, unit, modifier)
                else:
                    # No modifier - prefer entries without modifier, then any
                    query = """
                        SELECT ip.gram_weight
                        FROM recipe_manager.ingredient_portions ip
                        JOIN recipe_manager.ingredients i
                            ON i.ingredient_id = ip.ingredient_id
                        WHERE LOWER(i.name) = LOWER($1)
                          AND UPPER(ip.unit) = UPPER($2)
                        ORDER BY
                            CASE WHEN ip.modifier IS NULL THEN 0 ELSE 1 END,
                            ip.sequence_number NULLS LAST
                        LIMIT 1
                    """
                    row = await conn.fetchrow(query, ingredient_name, unit)

            if row is None:
                return None

            return Decimal(str(row["gram_weight"]))

        except Exception as e:
            # Handle missing table or other database errors gracefully
            error_msg = str(e).lower()
            if "relation" in error_msg and "does not exist" in error_msg:
                logger.debug(
                    "ingredient_portions table not found, returning None",
                    ingredient=ingredient_name,
                    unit=unit,
                )
                return None
            # Log but don't raise - fallback to default conversion
            logger.warning(
                "Error looking up portion weight",
                ingredient=ingredient_name,
                unit=unit,
                error=str(e),
            )
            return None

    def _row_to_nutrition_data(self, row: Record) -> NutritionData:
        """Convert database row to NutritionData model.

        Handles NULL values from LEFT JOINs by creating None for
        missing related data (macros, vitamins, minerals).
        """
        # Check if we have any macronutrient data
        has_macros = row["calories_kcal"] is not None or row["protein_g"] is not None

        # Check if we have any vitamin data
        has_vitamins = (
            row["vitamin_a_mcg"] is not None or row["vitamin_c_mcg"] is not None
        )

        # Check if we have any mineral data
        has_minerals = row["calcium_mg"] is not None or row["iron_mg"] is not None

        return NutritionData(
            ingredient_id=row["ingredient_id"],
            ingredient_name=row["ingredient_name"],
            fdc_id=row["fdc_id"],
            usda_food_description=row["usda_food_description"],
            serving_size_g=row["serving_size_g"] or Decimal("100.00"),
            data_source=row["data_source"] or "USDA",
            macronutrients=MacronutrientsData(
                calories_kcal=row["calories_kcal"],
                protein_g=row["protein_g"],
                carbs_g=row["carbs_g"],
                fat_g=row["fat_g"],
                saturated_fat_g=row["saturated_fat_g"],
                trans_fat_g=row["trans_fat_g"],
                monounsaturated_fat_g=row["monounsaturated_fat_g"],
                polyunsaturated_fat_g=row["polyunsaturated_fat_g"],
                cholesterol_mg=row["cholesterol_mg"],
                sodium_mg=row["sodium_mg"],
                fiber_g=row["fiber_g"],
                sugar_g=row["sugar_g"],
                added_sugar_g=row["added_sugar_g"],
            )
            if has_macros
            else None,
            vitamins=VitaminsData(
                vitamin_a_mcg=row["vitamin_a_mcg"],
                vitamin_b6_mcg=row["vitamin_b6_mcg"],
                vitamin_b12_mcg=row["vitamin_b12_mcg"],
                vitamin_c_mcg=row["vitamin_c_mcg"],
                vitamin_d_mcg=row["vitamin_d_mcg"],
                vitamin_e_mcg=row["vitamin_e_mcg"],
                vitamin_k_mcg=row["vitamin_k_mcg"],
            )
            if has_vitamins
            else None,
            minerals=MineralsData(
                calcium_mg=row["calcium_mg"],
                iron_mg=row["iron_mg"],
                magnesium_mg=row["magnesium_mg"],
                potassium_mg=row["potassium_mg"],
                zinc_mg=row["zinc_mg"],
            )
            if has_minerals
            else None,
        )
