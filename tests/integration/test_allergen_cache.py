"""Integration tests for allergen cache operations.

Tests cover:
- AllergenService cache read/write with real Redis
- Cache key generation and normalization
- TTL behavior
- Cache hit/miss scenarios
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import orjson
import pytest
from redis.asyncio import Redis

from app.database.repositories.allergen import AllergenData
from app.schemas.allergen import (
    AllergenDataSource,
    AllergenInfo,
    AllergenPresenceType,
    IngredientAllergenResponse,
)
from app.schemas.enums import Allergen
from app.services.allergen.constants import (
    ALLERGEN_CACHE_KEY_PREFIX,
    ALLERGEN_CACHE_TTL_SECONDS,
)
from app.services.allergen.service import AllergenService


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


pytestmark = pytest.mark.integration


class TestAllergenServiceCacheIntegration:
    """Integration tests for AllergenService caching with real Redis."""

    @pytest.fixture
    async def redis_cache(
        self,
        redis_url: str,
    ) -> AsyncGenerator[Redis[bytes]]:
        """Create Redis client for cache testing."""
        client: Redis[bytes] = Redis.from_url(redis_url, decode_responses=False)
        await client.flushdb()
        try:
            yield client
        finally:
            await client.aclose()  # type: ignore[attr-defined]

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        """Create mock repository that returns no data by default."""
        repo = MagicMock()
        repo.get_by_ingredient_name = AsyncMock(return_value=[])
        repo.get_by_ingredient_name_fuzzy = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def mock_off_client(self) -> MagicMock:
        """Create mock OFF client that returns no data."""
        client = MagicMock()
        client.search_by_name = AsyncMock(return_value=None)
        client.initialize = AsyncMock()
        client.shutdown = AsyncMock()
        return client

    @pytest.fixture
    async def allergen_service(
        self,
        redis_cache: Redis[bytes],
        mock_repository: MagicMock,
        mock_off_client: MagicMock,
    ) -> AsyncGenerator[AllergenService]:
        """Create AllergenService with real Redis cache."""
        service = AllergenService(
            cache_client=redis_cache,
            repository=mock_repository,
            off_client=mock_off_client,
        )
        await service.initialize()
        yield service
        await service.shutdown()

    @pytest.fixture
    def flour_allergen_data(self) -> AllergenData:
        """Sample allergen data for flour."""
        return AllergenData(
            ingredient_id=1,
            ingredient_name="flour",
            usda_food_description="Wheat flour, white, all-purpose",
            allergen_type="GLUTEN",
            presence_type="CONTAINS",
            confidence_score=Decimal("1.0"),
            source_notes="Contains wheat gluten",
            data_source="USDA",
            profile_confidence=Decimal("1.0"),
        )

    async def test_cache_miss_then_hit(
        self,
        allergen_service: AllergenService,
        mock_repository: MagicMock,
        redis_cache: Redis[bytes],
        flour_allergen_data: AllergenData,
    ) -> None:
        """Should cache result after database lookup."""
        mock_repository.get_by_ingredient_name.return_value = [flour_allergen_data]

        # First call - cache miss, hits database
        result1 = await allergen_service.get_ingredient_allergens("flour")

        assert result1 is not None
        assert result1.ingredient_name == "flour"
        assert mock_repository.get_by_ingredient_name.call_count == 1

        # Verify cache was populated
        cache_key = f"{ALLERGEN_CACHE_KEY_PREFIX}:flour"
        cached_data = await redis_cache.get(cache_key)
        assert cached_data is not None

        # Reset mock call count
        mock_repository.get_by_ingredient_name.reset_mock()

        # Second call - should hit cache
        result2 = await allergen_service.get_ingredient_allergens("flour")

        assert result2 is not None
        assert result2.ingredient_name == "flour"
        assert mock_repository.get_by_ingredient_name.call_count == 0

    async def test_cache_key_normalization(
        self,
        allergen_service: AllergenService,
        mock_repository: MagicMock,
        redis_cache: Redis[bytes],
        flour_allergen_data: AllergenData,
    ) -> None:
        """Should normalize cache keys (lowercase)."""
        mock_repository.get_by_ingredient_name.return_value = [flour_allergen_data]

        # Call with lowercase
        await allergen_service.get_ingredient_allergens("flour")

        # Verify normalized key exists
        cache_key = f"{ALLERGEN_CACHE_KEY_PREFIX}:flour"
        assert await redis_cache.exists(cache_key) == 1

        # Reset mock
        mock_repository.get_by_ingredient_name.reset_mock()

        # Call with uppercase - should hit cache
        result = await allergen_service.get_ingredient_allergens("FLOUR")

        assert result is not None
        assert mock_repository.get_by_ingredient_name.call_count == 0

    async def test_cache_ttl_is_set(
        self,
        allergen_service: AllergenService,
        mock_repository: MagicMock,
        redis_cache: Redis[bytes],
        flour_allergen_data: AllergenData,
    ) -> None:
        """Should set correct TTL on cached data."""
        mock_repository.get_by_ingredient_name.return_value = [flour_allergen_data]

        await allergen_service.get_ingredient_allergens("flour")

        cache_key = f"{ALLERGEN_CACHE_KEY_PREFIX}:flour"
        ttl = await redis_cache.ttl(cache_key)

        # TTL should be close to configured value (30 days)
        assert ttl > 0
        assert ttl <= ALLERGEN_CACHE_TTL_SECONDS

    async def test_cached_data_structure(
        self,
        allergen_service: AllergenService,
        mock_repository: MagicMock,
        redis_cache: Redis[bytes],
        flour_allergen_data: AllergenData,
    ) -> None:
        """Should cache data in correct JSON structure."""
        mock_repository.get_by_ingredient_name.return_value = [flour_allergen_data]

        await allergen_service.get_ingredient_allergens("flour")

        cache_key = f"{ALLERGEN_CACHE_KEY_PREFIX}:flour"
        cached_bytes = await redis_cache.get(cache_key)
        assert cached_bytes is not None

        # Deserialize and verify structure
        cached_data = orjson.loads(cached_bytes)
        assert cached_data["ingredientName"] == "flour"
        assert len(cached_data["allergens"]) == 1
        assert cached_data["allergens"][0]["allergen"] == "GLUTEN"
        assert cached_data["dataSource"] == "USDA"

    async def test_cache_not_written_for_not_found(
        self,
        allergen_service: AllergenService,
        redis_cache: Redis[bytes],
    ) -> None:
        """Should not cache when no allergen data found."""
        result = await allergen_service.get_ingredient_allergens("unknown-ingredient")

        assert result is None

        cache_key = f"{ALLERGEN_CACHE_KEY_PREFIX}:unknown-ingredient"
        assert await redis_cache.exists(cache_key) == 0

    async def test_prepopulated_cache_is_used(
        self,
        allergen_service: AllergenService,
        mock_repository: MagicMock,
        redis_cache: Redis[bytes],
    ) -> None:
        """Should use pre-populated cache data."""
        # Pre-populate cache
        cached_response = IngredientAllergenResponse(
            ingredient_id=99,
            ingredient_name="prepopulated",
            allergens=[
                AllergenInfo(
                    allergen=Allergen.PEANUTS,
                    presence_type=AllergenPresenceType.CONTAINS,
                )
            ],
            data_source=AllergenDataSource.USDA,
        )
        cache_key = f"{ALLERGEN_CACHE_KEY_PREFIX}:prepopulated"
        await redis_cache.setex(
            cache_key,
            3600,
            orjson.dumps(cached_response.model_dump(mode="json")),
        )

        # Fetch - should use cache
        result = await allergen_service.get_ingredient_allergens("prepopulated")

        assert result is not None
        assert result.ingredient_id == 99
        assert result.allergens[0].allergen == Allergen.PEANUTS
        assert mock_repository.get_by_ingredient_name.call_count == 0


class TestAllergenCacheEdgeCases:
    """Edge case tests for allergen caching."""

    @pytest.fixture
    async def redis_cache(
        self,
        redis_url: str,
    ) -> AsyncGenerator[Redis[bytes]]:
        """Create Redis client for edge case tests."""
        client: Redis[bytes] = Redis.from_url(redis_url, decode_responses=False)
        await client.flushdb()
        try:
            yield client
        finally:
            await client.aclose()  # type: ignore[attr-defined]

    async def test_corrupted_cache_data_handled_gracefully(
        self,
        redis_cache: Redis[bytes],
    ) -> None:
        """Should handle corrupted cache data without crashing."""
        mock_repository = MagicMock()
        mock_repository.get_by_ingredient_name = AsyncMock(return_value=[])
        mock_repository.get_by_ingredient_name_fuzzy = AsyncMock(return_value=[])

        mock_off_client = MagicMock()
        mock_off_client.search_by_name = AsyncMock(return_value=None)
        mock_off_client.initialize = AsyncMock()
        mock_off_client.shutdown = AsyncMock()

        service = AllergenService(
            cache_client=redis_cache,
            repository=mock_repository,
            off_client=mock_off_client,
        )
        await service.initialize()

        # Write corrupted data to cache
        cache_key = f"{ALLERGEN_CACHE_KEY_PREFIX}:corrupted"
        await redis_cache.setex(cache_key, 3600, b"not valid json {{{")

        # Should not crash, should fall through to database lookup
        result = await service.get_ingredient_allergens("corrupted")

        # Will be None since mock repository returns empty
        assert result is None

        await service.shutdown()

    async def test_special_characters_in_ingredient_name(
        self,
        redis_cache: Redis[bytes],
    ) -> None:
        """Should handle special characters in ingredient names."""
        mock_repository = MagicMock()
        special_data = AllergenData(
            ingredient_id=1,
            ingredient_name="crème fraîche",
            usda_food_description="Crème fraîche",
            allergen_type="MILK",
            presence_type="CONTAINS",
            confidence_score=Decimal("1.0"),
            source_notes=None,
            data_source="USDA",
            profile_confidence=Decimal("1.0"),
        )
        mock_repository.get_by_ingredient_name = AsyncMock(return_value=[special_data])
        mock_repository.get_by_ingredient_name_fuzzy = AsyncMock(return_value=[])

        mock_off_client = MagicMock()
        mock_off_client.search_by_name = AsyncMock(return_value=None)
        mock_off_client.initialize = AsyncMock()
        mock_off_client.shutdown = AsyncMock()

        service = AllergenService(
            cache_client=redis_cache,
            repository=mock_repository,
            off_client=mock_off_client,
        )
        await service.initialize()

        result = await service.get_ingredient_allergens("Crème Fraîche")

        assert result is not None
        assert result.ingredient_name == "crème fraîche"

        # Verify cached with normalized key
        cache_key = f"{ALLERGEN_CACHE_KEY_PREFIX}:crème fraîche"
        assert await redis_cache.exists(cache_key) == 1

        await service.shutdown()

    async def test_ingredient_with_no_allergens_not_cached(
        self,
        redis_cache: Redis[bytes],
    ) -> None:
        """Should not cache when ingredient has no allergen data."""
        mock_repository = MagicMock()
        # Repository returns empty list for ingredient with no allergens
        # (chicken has a profile but no allergen entries in ingredient_allergens)
        mock_repository.get_by_ingredient_name = AsyncMock(return_value=[])
        mock_repository.get_by_ingredient_name_fuzzy = AsyncMock(return_value=[])

        mock_off_client = MagicMock()
        mock_off_client.search_by_name = AsyncMock(return_value=None)
        mock_off_client.initialize = AsyncMock()
        mock_off_client.shutdown = AsyncMock()

        service = AllergenService(
            cache_client=redis_cache,
            repository=mock_repository,
            off_client=mock_off_client,
        )
        await service.initialize()

        result = await service.get_ingredient_allergens("chicken")

        # No allergen data found means None is returned
        assert result is None

        # Should not be cached
        cache_key = f"{ALLERGEN_CACHE_KEY_PREFIX}:chicken"
        assert await redis_cache.exists(cache_key) == 0

        await service.shutdown()
