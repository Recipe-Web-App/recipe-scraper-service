"""Shopping service for retrieving ingredient pricing information.

Provides methods for:
- Single ingredient pricing lookup
- Two-tier lookup strategy (direct ingredient → food group fallback)
- Redis caching with 24-hour TTL
- Unit conversion and price scaling
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import orjson

from app.cache.redis import get_cache_client
from app.database.repositories.nutrition import NutritionRepository
from app.database.repositories.shopping import PricingRepository
from app.observability.logging import get_logger
from app.schemas.enums import IngredientUnit
from app.schemas.ingredient import Quantity
from app.schemas.shopping import IngredientShoppingInfoResponse
from app.services.nutrition.converter import UnitConverter
from app.services.nutrition.exceptions import ConversionError
from app.services.shopping.constants import (
    SHOPPING_CACHE_KEY_PREFIX,
    SHOPPING_CACHE_TTL_SECONDS,
    TIER_1_CONFIDENCE,
    TIER_2_CONFIDENCE,
)
from app.services.shopping.exceptions import IngredientNotFoundError


if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = get_logger(__name__)


class ShoppingService:
    """Service for retrieving shopping/pricing information.

    Orchestrates:
    1. Redis cache lookups
    2. PostgreSQL database queries via PricingRepository
    3. Two-tier pricing lookup (direct ingredient → food group fallback)
    4. Unit conversion to grams
    5. Price calculation based on quantity
    6. Transformation to API response schemas

    Cache Strategy:
    - Cache key: "shopping:{ingredient_id}:{amount}:{unit}"
    - TTL: 24 hours
    - Caches computed responses including price
    """

    def __init__(
        self,
        cache_client: Redis[bytes] | None = None,
        repository: PricingRepository | None = None,
        nutrition_repository: NutritionRepository | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            cache_client: Optional Redis client for caching.
            repository: Optional PricingRepository instance.
            nutrition_repository: Optional NutritionRepository for unit conversion.
        """
        self._cache_client = cache_client
        self._repository = repository
        self._nutrition_repository = nutrition_repository
        self._converter: UnitConverter | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize service resources.

        Called during application startup. Sets up repository if not injected.
        """
        if self._cache_client is None:
            try:
                self._cache_client = await get_cache_client()
            except Exception:
                logger.warning("Redis not available, caching disabled")

        if self._repository is None:
            self._repository = PricingRepository()

        if self._nutrition_repository is None:
            self._nutrition_repository = NutritionRepository()

        # Create converter with nutrition repository for portion weight lookups
        self._converter = UnitConverter(nutrition_repository=self._nutrition_repository)

        self._initialized = True
        logger.info("ShoppingService initialized")

    async def shutdown(self) -> None:
        """Cleanup service resources.

        Called during application shutdown.
        """
        self._initialized = False
        logger.info("ShoppingService shutdown")

    async def get_ingredient_shopping_info(
        self,
        ingredient_id: int,
        quantity: Quantity | None = None,
    ) -> IngredientShoppingInfoResponse:
        """Get shopping/pricing information for a single ingredient.

        Args:
            ingredient_id: Database ID of the ingredient.
            quantity: Optional quantity with amount and unit for price calculation.
                      If not provided, returns price per 100g.

        Returns:
            Shopping information with estimated price.

        Raises:
            IngredientNotFoundError: If ingredient doesn't exist.
            ConversionError: If unit conversion fails.
        """
        if not self._initialized or self._repository is None:
            msg = "ShoppingService not initialized"
            logger.error(msg)
            raise RuntimeError(msg)

        # Default to 100g if no quantity specified
        if quantity is None:
            quantity = Quantity(amount=100.0, measurement=IngredientUnit.G)

        # Check cache first
        cache_key = self._make_cache_key(ingredient_id, quantity)
        cached = await self._get_from_cache(cache_key)
        if cached is not None:
            logger.debug(
                "Cache hit for shopping info",
                ingredient_id=ingredient_id,
                cache_key=cache_key,
            )
            return cached

        # Get ingredient details (name and food_group)
        ingredient = await self._repository.get_ingredient_details(ingredient_id)
        if ingredient is None:
            msg = f"Ingredient not found: {ingredient_id}"
            raise IngredientNotFoundError(msg, ingredient_id=ingredient_id)

        # Try Tier 1: Direct ingredient pricing
        pricing = await self._repository.get_price_by_ingredient_id(ingredient_id)

        # Fallback to Tier 2: Food group pricing
        if pricing is None and ingredient.food_group:
            pricing = await self._repository.get_price_by_food_group(
                ingredient.food_group
            )

        # Calculate price if pricing data available
        estimated_price: str | None = None
        price_confidence: float | None = None
        data_source: str | None = None
        currency = "USD"

        if pricing is not None:
            # Convert quantity to grams
            try:
                grams = await self._convert_to_grams(quantity, ingredient.name)
            except ConversionError:
                logger.warning(
                    "Unit conversion failed for shopping info",
                    ingredient_id=ingredient_id,
                    ingredient_name=ingredient.name,
                    unit=str(quantity.measurement),
                )
                raise

            # Calculate price: (grams / 100) * price_per_100g
            price = self._calculate_price(pricing.price_per_100g, grams)
            estimated_price = f"{price:.2f}"
            currency = pricing.currency
            data_source = pricing.data_source

            # Set confidence based on tier
            if pricing.tier == 1:
                price_confidence = float(TIER_1_CONFIDENCE)
            else:
                price_confidence = float(TIER_2_CONFIDENCE)

            logger.debug(
                "Price calculated",
                ingredient_id=ingredient_id,
                ingredient_name=ingredient.name,
                tier=pricing.tier,
                price=estimated_price,
                grams=float(grams),
            )
        else:
            logger.debug(
                "No pricing data available",
                ingredient_id=ingredient_id,
                ingredient_name=ingredient.name,
                food_group=ingredient.food_group,
            )

        # Build response
        response = IngredientShoppingInfoResponse(
            ingredient_name=ingredient.name,
            quantity=quantity,
            estimated_price=estimated_price,
            price_confidence=price_confidence,
            data_source=data_source,
            currency=currency,
        )

        # Cache the result
        await self._cache_result(cache_key, response)

        return response

    async def _convert_to_grams(
        self,
        quantity: Quantity,
        ingredient_name: str,
    ) -> Decimal:
        """Convert quantity to grams using UnitConverter.

        Args:
            quantity: Quantity to convert.
            ingredient_name: Ingredient name for portion weight lookup.

        Returns:
            Amount in grams.

        Raises:
            ConversionError: If conversion fails.
        """
        if self._converter is None:
            # Fallback: assume 1:1 for grams, rough estimates for others
            if quantity.measurement == IngredientUnit.G:
                return Decimal(str(quantity.amount))
            if quantity.measurement == IngredientUnit.KG:
                return Decimal(str(quantity.amount)) * Decimal(1000)
            # Default to 100g per unit for unknown conversions
            return Decimal(str(quantity.amount)) * Decimal(100)

        return await self._converter.to_grams(quantity, ingredient_name)

    def _calculate_price(
        self,
        price_per_100g: Decimal,
        grams: Decimal,
    ) -> Decimal:
        """Calculate price for a given quantity in grams.

        Args:
            price_per_100g: Price per 100 grams.
            grams: Quantity in grams.

        Returns:
            Calculated price.
        """
        return (grams / Decimal(100)) * price_per_100g

    def _make_cache_key(
        self,
        ingredient_id: int,
        quantity: Quantity,
    ) -> str:
        """Generate cache key for shopping info.

        Args:
            ingredient_id: Ingredient database ID.
            quantity: Quantity for the lookup.

        Returns:
            Cache key string.
        """
        return f"{SHOPPING_CACHE_KEY_PREFIX}:{ingredient_id}:{quantity.amount}:{quantity.measurement}"

    async def _get_from_cache(
        self,
        cache_key: str,
    ) -> IngredientShoppingInfoResponse | None:
        """Get cached shopping info.

        Args:
            cache_key: Cache key to look up.

        Returns:
            Cached response or None if not found.
        """
        if self._cache_client is None:
            return None

        try:
            data = await self._cache_client.get(cache_key)
            if data is None:
                return None

            parsed = orjson.loads(data)
            return IngredientShoppingInfoResponse.model_validate(parsed)

        except Exception as e:
            logger.warning(
                "Cache read failed",
                cache_key=cache_key,
                error=str(e),
            )
            return None

    async def _cache_result(
        self,
        cache_key: str,
        response: IngredientShoppingInfoResponse,
    ) -> None:
        """Cache shopping info response.

        Args:
            cache_key: Cache key to store under.
            response: Response to cache.
        """
        if self._cache_client is None:
            return

        try:
            data = orjson.dumps(response.model_dump(by_alias=True))
            await self._cache_client.setex(
                cache_key,
                SHOPPING_CACHE_TTL_SECONDS,
                data,
            )
            logger.debug(
                "Cached shopping info",
                cache_key=cache_key,
                ttl=SHOPPING_CACHE_TTL_SECONDS,
            )
        except Exception as e:
            logger.warning(
                "Cache write failed",
                cache_key=cache_key,
                error=str(e),
            )
