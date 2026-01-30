"""Nutrition service for retrieving and computing ingredient nutrition.

Provides methods for:
- Single ingredient nutrition lookup
- Batch recipe nutrition with aggregation
- Redis caching with 30-day TTL
- Unit conversion and nutrient scaling
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

import orjson

from app.cache.redis import get_cache_client
from app.database.repositories.nutrition import NutritionData, NutritionRepository
from app.observability.logging import get_logger
from app.schemas.enums import IngredientUnit, NutrientUnit
from app.schemas.ingredient import Quantity
from app.schemas.nutrition import (
    Fats,
    IngredientNutritionalInfoResponse,
    MacroNutrients,
    Minerals,
    NutrientValue,
    RecipeNutritionalInfoResponse,
    Vitamins,
)
from app.services.nutrition.constants import (
    NUTRITION_CACHE_KEY_PREFIX,
    NUTRITION_CACHE_TTL_SECONDS,
)
from app.services.nutrition.converter import UnitConverter
from app.services.nutrition.exceptions import ConversionError


if TYPE_CHECKING:
    from redis.asyncio import Redis

    from app.schemas.ingredient import Ingredient

logger = get_logger(__name__)


class NutritionService:
    """Service for retrieving nutritional information.

    Orchestrates:
    1. Redis cache lookups
    2. PostgreSQL database queries via NutritionRepository
    3. Unit conversion to grams
    4. Nutrient scaling based on actual quantity
    5. Transformation to API response schemas

    Cache Strategy:
    - Cache key: "nutrition:{ingredient_name}"
    - TTL: 30 days
    - Caches raw database data (NutritionData), not scaled values
    - Scaling applied at response time based on requested quantity
    """

    def __init__(
        self,
        cache_client: Redis[bytes] | None = None,
        repository: NutritionRepository | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            cache_client: Optional Redis client for caching.
            repository: Optional NutritionRepository instance.
        """
        self._cache_client = cache_client
        self._repository = repository
        self._converter: UnitConverter | None = None

    async def initialize(self) -> None:
        """Initialize service resources.

        Called during application startup. Sets up repository if not injected.
        """
        if self._cache_client is None:
            try:
                self._cache_client = get_cache_client()
            except RuntimeError:
                logger.warning("Redis not available, caching disabled")

        if self._repository is None:
            self._repository = NutritionRepository()

        # Create converter with repository for portion weight lookups
        self._converter = UnitConverter(nutrition_repository=self._repository)

        logger.info("NutritionService initialized")

    async def shutdown(self) -> None:
        """Cleanup service resources.

        Called during application shutdown.
        """
        logger.info("NutritionService shutdown")

    async def get_ingredient_nutrition(
        self,
        name: str,
        quantity: Quantity,
    ) -> IngredientNutritionalInfoResponse | None:
        """Get nutritional information for a single ingredient.

        Args:
            name: Ingredient name.
            quantity: Quantity with amount and unit.

        Returns:
            Nutritional information scaled to the quantity, or None if not found.

        Raises:
            ConversionError: If unit conversion fails.
        """
        if self._converter is None:
            logger.error("NutritionService not initialized")
            return None

        # Get raw nutrition data (from cache or database)
        nutrition_data = await self._get_nutrition_data(name)

        if nutrition_data is None:
            logger.debug("Nutrition data not found", ingredient=name)
            return None

        # Convert quantity to grams
        try:
            grams = await self._converter.to_grams(quantity, name)
        except ConversionError:
            logger.warning(
                "Unit conversion failed",
                ingredient=name,
                unit=quantity.measurement,
            )
            raise

        # Scale and transform to response
        return self._transform_to_response(
            nutrition_data=nutrition_data,
            quantity=quantity,
            grams=grams,
        )

    async def get_recipe_nutrition(
        self,
        ingredients: list[Ingredient],
    ) -> RecipeNutritionalInfoResponse:
        """Get nutritional information for a recipe.

        Args:
            ingredients: List of ingredients with names and quantities.

        Returns:
            Recipe nutritional response with:
            - Per-ingredient nutrition
            - Missing ingredient IDs
            - Aggregated totals
        """
        if self._converter is None:
            logger.error("NutritionService not initialized")
            return RecipeNutritionalInfoResponse(
                ingredients=None,
                missing_ingredients=[
                    ing.ingredient_id
                    for ing in ingredients
                    if ing.ingredient_id is not None
                ],
                total=IngredientNutritionalInfoResponse(
                    quantity=Quantity(amount=0, measurement=IngredientUnit.G),
                    macro_nutrients=None,
                    vitamins=None,
                    minerals=None,
                ),
            )

        # Extract ingredient names
        names = [ing.name for ing in ingredients if ing.name]

        # Batch fetch nutrition data
        nutrition_map = await self._get_batch_nutrition_data(names)

        # Process each ingredient
        per_ingredient: dict[str, IngredientNutritionalInfoResponse] = {}
        missing_ingredients: list[int] = []
        totals = self._create_zero_totals()
        total_grams = Decimal(0)

        for ingredient in ingredients:
            if not ingredient.name:
                if ingredient.ingredient_id:
                    missing_ingredients.append(ingredient.ingredient_id)
                continue

            nutrition_data = nutrition_map.get(ingredient.name)

            if nutrition_data is None:
                if ingredient.ingredient_id:
                    missing_ingredients.append(ingredient.ingredient_id)
                continue

            quantity = ingredient.quantity or Quantity(
                amount=100,
                measurement=IngredientUnit.G,
            )

            try:
                grams = await self._converter.to_grams(quantity, ingredient.name)
            except ConversionError:
                logger.warning(
                    "Skipping ingredient due to conversion error",
                    ingredient=ingredient.name,
                )
                if ingredient.ingredient_id:
                    missing_ingredients.append(ingredient.ingredient_id)
                continue

            response = self._transform_to_response(
                nutrition_data=nutrition_data,
                quantity=quantity,
                grams=grams,
            )

            per_ingredient[ingredient.name] = response
            self._accumulate_totals(totals, response)
            total_grams += grams

        total_quantity = Quantity(
            amount=float(total_grams),
            measurement=IngredientUnit.G,
        )

        total_response = IngredientNutritionalInfoResponse(
            quantity=total_quantity,
            macro_nutrients=totals["macros"],
            vitamins=totals["vitamins"],
            minerals=totals["minerals"],
        )

        return RecipeNutritionalInfoResponse(
            ingredients=per_ingredient if per_ingredient else None,
            missing_ingredients=missing_ingredients if missing_ingredients else None,
            total=total_response,
        )

    # =========================================================================
    # Cache Operations
    # =========================================================================

    async def _get_nutrition_data(self, name: str) -> NutritionData | None:
        """Get nutrition data from cache or database.

        Uses a multi-tier lookup strategy:
        1. Check cache for exact query name
        2. Try exact match in database
        3. Fall back to fuzzy search if exact match fails

        Args:
            name: Ingredient name.

        Returns:
            NutritionData or None if not found.
        """
        # Try cache first
        cached = await self._get_from_cache(name)
        if cached is not None:
            logger.debug("Cache hit", ingredient=name)
            return cached

        # Cache miss - query database
        logger.debug("Cache miss", ingredient=name)
        if self._repository is None:
            return None

        # Try exact match first
        data = await self._repository.get_by_ingredient_name(name)

        # Fall back to fuzzy search if exact match fails
        if data is None:
            data = await self._repository.get_by_ingredient_name_fuzzy(name)
            if data is not None:
                logger.debug(
                    "Fuzzy match found",
                    query=name,
                    matched_name=data.ingredient_name,
                )

        # Cache under original query name (not matched name)
        if data is not None:
            await self._save_to_cache(name, data)

        return data

    async def _get_batch_nutrition_data(
        self,
        names: list[str],
    ) -> dict[str, NutritionData]:
        """Get nutrition data for multiple ingredients.

        Uses a multi-tier lookup strategy:
        1. Check cache for each name
        2. Batch exact match in database
        3. Fuzzy search for any remaining misses

        Args:
            names: List of ingredient names.

        Returns:
            Dictionary mapping query names to NutritionData.
            Names that don't match are not included.
        """
        if not names:
            return {}

        result: dict[str, NutritionData] = {}
        cache_misses: list[str] = []

        # Check cache for each ingredient
        for name in names:
            cached = await self._get_from_cache(name)
            if cached is not None:
                result[name] = cached
            else:
                cache_misses.append(name)

        if cache_misses and self._repository is not None:
            # Batch query database for exact matches
            db_results = await self._repository.get_by_ingredient_names(cache_misses)

            # Track which names still need fuzzy search
            # Note: db_results keys are the actual DB names, we need to match back
            still_missing: list[str] = []

            for name in cache_misses:
                # Check if this query name got an exact match
                data = db_results.get(name)
                if data is not None:
                    await self._save_to_cache(name, data)
                    result[name] = data
                else:
                    still_missing.append(name)

            # Fall back to fuzzy search for remaining misses
            if still_missing:
                fuzzy_results = await self._repository.get_by_ingredient_names_fuzzy(
                    still_missing
                )

                for query_name, data in fuzzy_results.items():
                    logger.debug(
                        "Fuzzy match found (batch)",
                        query=query_name,
                        matched_name=data.ingredient_name,
                    )
                    # Cache under original query name
                    await self._save_to_cache(query_name, data)
                    result[query_name] = data

        return result

    async def _get_from_cache(self, name: str) -> NutritionData | None:
        """Get nutrition data from cache.

        Args:
            name: Ingredient name.

        Returns:
            NutritionData or None if not cached.
        """
        if self._cache_client is None:
            return None

        cache_key = self._make_cache_key(name)

        try:
            cached_bytes = await self._cache_client.get(cache_key)
            if cached_bytes:
                data = orjson.loads(cached_bytes)
                return NutritionData.model_validate(data)
        except Exception:
            logger.exception("Cache read error", key=cache_key)

        return None

    async def _save_to_cache(self, name: str, data: NutritionData) -> None:
        """Save nutrition data to cache.

        Args:
            name: Ingredient name.
            data: NutritionData to cache.
        """
        if self._cache_client is None:
            return

        cache_key = self._make_cache_key(name)

        try:
            json_bytes = orjson.dumps(data.model_dump(mode="json"))
            await self._cache_client.setex(
                cache_key,
                NUTRITION_CACHE_TTL_SECONDS,
                json_bytes,
            )
            logger.debug("Cached nutrition data", key=cache_key)
        except Exception:
            logger.exception("Cache write error", key=cache_key)

    def _make_cache_key(self, name: str) -> str:
        """Create cache key for an ingredient.

        Args:
            name: Ingredient name.

        Returns:
            Cache key string.
        """
        # Normalize name for consistent caching
        normalized = name.lower().strip()
        return f"{NUTRITION_CACHE_KEY_PREFIX}:{normalized}"

    # =========================================================================
    # Transformation
    # =========================================================================

    def _transform_to_response(
        self,
        nutrition_data: NutritionData,
        quantity: Quantity,
        grams: Decimal,
    ) -> IngredientNutritionalInfoResponse:
        """Transform database DTO to API response with scaling.

        Args:
            nutrition_data: Raw data from database (per 100g).
            quantity: Original quantity for response.
            grams: Actual amount in grams for scaling.

        Returns:
            Scaled nutritional information.
        """
        scale_factor = grams / Decimal(100)

        # Transform macronutrients
        macros = None
        if nutrition_data.macronutrients:
            m = nutrition_data.macronutrients
            macros = MacroNutrients(
                calories=self._scale_nutrient(
                    m.calories_kcal, scale_factor, NutrientUnit.KILOCALORIE
                ),
                carbs=self._scale_nutrient(m.carbs_g, scale_factor, NutrientUnit.GRAM),
                protein=self._scale_nutrient(
                    m.protein_g, scale_factor, NutrientUnit.GRAM
                ),
                cholesterol=self._scale_nutrient(
                    m.cholesterol_mg, scale_factor, NutrientUnit.MILLIGRAM
                ),
                sodium=self._scale_nutrient(
                    m.sodium_mg, scale_factor, NutrientUnit.MILLIGRAM
                ),
                fiber=self._scale_nutrient(m.fiber_g, scale_factor, NutrientUnit.GRAM),
                sugar=self._scale_nutrient(m.sugar_g, scale_factor, NutrientUnit.GRAM),
                added_sugar=self._scale_nutrient(
                    m.added_sugar_g, scale_factor, NutrientUnit.GRAM
                ),
                fats=Fats(
                    total=self._scale_nutrient(
                        m.fat_g, scale_factor, NutrientUnit.GRAM
                    ),
                    saturated=self._scale_nutrient(
                        m.saturated_fat_g, scale_factor, NutrientUnit.GRAM
                    ),
                    monounsaturated=self._scale_nutrient(
                        m.monounsaturated_fat_g, scale_factor, NutrientUnit.GRAM
                    ),
                    polyunsaturated=self._scale_nutrient(
                        m.polyunsaturated_fat_g, scale_factor, NutrientUnit.GRAM
                    ),
                    trans=self._scale_nutrient(
                        m.trans_fat_g, scale_factor, NutrientUnit.GRAM
                    ),
                ),
            )

        # Transform vitamins
        vitamins = None
        if nutrition_data.vitamins:
            v = nutrition_data.vitamins
            vitamins = Vitamins(
                vitamin_a=self._scale_nutrient(
                    v.vitamin_a_mcg, scale_factor, NutrientUnit.MICROGRAM
                ),
                vitamin_b6=self._scale_nutrient(
                    v.vitamin_b6_mcg, scale_factor, NutrientUnit.MICROGRAM
                ),
                vitamin_b12=self._scale_nutrient(
                    v.vitamin_b12_mcg, scale_factor, NutrientUnit.MICROGRAM
                ),
                vitamin_c=self._scale_nutrient(
                    v.vitamin_c_mcg, scale_factor, NutrientUnit.MICROGRAM
                ),
                vitamin_d=self._scale_nutrient(
                    v.vitamin_d_mcg, scale_factor, NutrientUnit.MICROGRAM
                ),
                vitamin_e=self._scale_nutrient(
                    v.vitamin_e_mcg, scale_factor, NutrientUnit.MICROGRAM
                ),
                vitamin_k=self._scale_nutrient(
                    v.vitamin_k_mcg, scale_factor, NutrientUnit.MICROGRAM
                ),
            )

        # Transform minerals
        minerals = None
        if nutrition_data.minerals:
            min_data = nutrition_data.minerals
            minerals = Minerals(
                calcium=self._scale_nutrient(
                    min_data.calcium_mg, scale_factor, NutrientUnit.MILLIGRAM
                ),
                iron=self._scale_nutrient(
                    min_data.iron_mg, scale_factor, NutrientUnit.MILLIGRAM
                ),
                magnesium=self._scale_nutrient(
                    min_data.magnesium_mg, scale_factor, NutrientUnit.MILLIGRAM
                ),
                potassium=self._scale_nutrient(
                    min_data.potassium_mg, scale_factor, NutrientUnit.MILLIGRAM
                ),
                zinc=self._scale_nutrient(
                    min_data.zinc_mg, scale_factor, NutrientUnit.MILLIGRAM
                ),
            )

        return IngredientNutritionalInfoResponse(
            quantity=quantity,
            usda_food_description=nutrition_data.usda_food_description,
            macro_nutrients=macros,
            vitamins=vitamins,
            minerals=minerals,
        )

    def _scale_nutrient(
        self,
        value: Decimal | None,
        scale_factor: Decimal,
        unit: NutrientUnit,
    ) -> NutrientValue | None:
        """Scale a nutrient value and wrap in NutrientValue.

        Args:
            value: Raw value per 100g (or None).
            scale_factor: Multiplier (grams / 100).
            unit: Unit of measurement.

        Returns:
            NutrientValue with scaled amount, or None if value is None.
        """
        if value is None:
            return None

        scaled = float(value * scale_factor)
        return NutrientValue(amount=round(scaled, 2), measurement=unit)

    def _create_zero_totals(self) -> dict[str, Any]:
        """Create zero-initialized totals structure for accumulation."""
        return {
            "macros": MacroNutrients(
                calories=NutrientValue(amount=0, measurement=NutrientUnit.KILOCALORIE),
                carbs=NutrientValue(amount=0, measurement=NutrientUnit.GRAM),
                protein=NutrientValue(amount=0, measurement=NutrientUnit.GRAM),
                cholesterol=NutrientValue(amount=0, measurement=NutrientUnit.MILLIGRAM),
                sodium=NutrientValue(amount=0, measurement=NutrientUnit.MILLIGRAM),
                fiber=NutrientValue(amount=0, measurement=NutrientUnit.GRAM),
                sugar=NutrientValue(amount=0, measurement=NutrientUnit.GRAM),
                added_sugar=NutrientValue(amount=0, measurement=NutrientUnit.GRAM),
                fats=Fats(
                    total=NutrientValue(amount=0, measurement=NutrientUnit.GRAM),
                    saturated=NutrientValue(amount=0, measurement=NutrientUnit.GRAM),
                    monounsaturated=NutrientValue(
                        amount=0, measurement=NutrientUnit.GRAM
                    ),
                    polyunsaturated=NutrientValue(
                        amount=0, measurement=NutrientUnit.GRAM
                    ),
                    trans=NutrientValue(amount=0, measurement=NutrientUnit.GRAM),
                ),
            ),
            "vitamins": Vitamins(
                vitamin_a=NutrientValue(amount=0, measurement=NutrientUnit.MICROGRAM),
                vitamin_b6=NutrientValue(amount=0, measurement=NutrientUnit.MICROGRAM),
                vitamin_b12=NutrientValue(amount=0, measurement=NutrientUnit.MICROGRAM),
                vitamin_c=NutrientValue(amount=0, measurement=NutrientUnit.MICROGRAM),
                vitamin_d=NutrientValue(amount=0, measurement=NutrientUnit.MICROGRAM),
                vitamin_e=NutrientValue(amount=0, measurement=NutrientUnit.MICROGRAM),
                vitamin_k=NutrientValue(amount=0, measurement=NutrientUnit.MICROGRAM),
            ),
            "minerals": Minerals(
                calcium=NutrientValue(amount=0, measurement=NutrientUnit.MILLIGRAM),
                iron=NutrientValue(amount=0, measurement=NutrientUnit.MILLIGRAM),
                magnesium=NutrientValue(amount=0, measurement=NutrientUnit.MILLIGRAM),
                potassium=NutrientValue(amount=0, measurement=NutrientUnit.MILLIGRAM),
                zinc=NutrientValue(amount=0, measurement=NutrientUnit.MILLIGRAM),
            ),
        }

    def _accumulate_totals(
        self,
        totals: dict[str, Any],
        response: IngredientNutritionalInfoResponse,
    ) -> None:
        """Add ingredient nutrition to running totals.

        Args:
            totals: Running totals to update.
            response: Ingredient response to add.
        """
        if response.macro_nutrients:
            self._add_macros(totals["macros"], response.macro_nutrients)
        if response.vitamins:
            self._add_vitamins(totals["vitamins"], response.vitamins)
        if response.minerals:
            self._add_minerals(totals["minerals"], response.minerals)

    def _add_macros(self, totals: MacroNutrients, source: MacroNutrients) -> None:
        """Add macronutrient values to totals."""
        self._add_nutrient_value(totals.calories, source.calories)
        self._add_nutrient_value(totals.carbs, source.carbs)
        self._add_nutrient_value(totals.protein, source.protein)
        self._add_nutrient_value(totals.cholesterol, source.cholesterol)
        self._add_nutrient_value(totals.sodium, source.sodium)
        self._add_nutrient_value(totals.fiber, source.fiber)
        self._add_nutrient_value(totals.sugar, source.sugar)
        self._add_nutrient_value(totals.added_sugar, source.added_sugar)
        if totals.fats and source.fats:
            self._add_nutrient_value(totals.fats.total, source.fats.total)
            self._add_nutrient_value(totals.fats.saturated, source.fats.saturated)
            self._add_nutrient_value(
                totals.fats.monounsaturated, source.fats.monounsaturated
            )
            self._add_nutrient_value(
                totals.fats.polyunsaturated, source.fats.polyunsaturated
            )
            self._add_nutrient_value(totals.fats.trans, source.fats.trans)

    def _add_vitamins(self, totals: Vitamins, source: Vitamins) -> None:
        """Add vitamin values to totals."""
        self._add_nutrient_value(totals.vitamin_a, source.vitamin_a)
        self._add_nutrient_value(totals.vitamin_b6, source.vitamin_b6)
        self._add_nutrient_value(totals.vitamin_b12, source.vitamin_b12)
        self._add_nutrient_value(totals.vitamin_c, source.vitamin_c)
        self._add_nutrient_value(totals.vitamin_d, source.vitamin_d)
        self._add_nutrient_value(totals.vitamin_e, source.vitamin_e)
        self._add_nutrient_value(totals.vitamin_k, source.vitamin_k)

    def _add_minerals(self, totals: Minerals, source: Minerals) -> None:
        """Add mineral values to totals."""
        self._add_nutrient_value(totals.calcium, source.calcium)
        self._add_nutrient_value(totals.iron, source.iron)
        self._add_nutrient_value(totals.magnesium, source.magnesium)
        self._add_nutrient_value(totals.potassium, source.potassium)
        self._add_nutrient_value(totals.zinc, source.zinc)

    def _add_nutrient_value(
        self,
        total: NutrientValue | None,
        source: NutrientValue | None,
    ) -> None:
        """Add a source nutrient value to a total."""
        if total is not None and source is not None and source.amount is not None:
            total.amount = (total.amount or 0) + source.amount
