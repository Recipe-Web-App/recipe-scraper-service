"""Unit tests for AllergenService."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import orjson
import pytest

from app.clients.open_food_facts.client import (
    OpenFoodFactsAllergen,
    OpenFoodFactsProduct,
)
from app.database.repositories.allergen import AllergenData
from app.schemas.allergen import (
    AllergenDataSource,
    AllergenInfo,
    AllergenPresenceType,
    IngredientAllergenResponse,
)
from app.schemas.enums import Allergen
from app.schemas.ingredient import Ingredient
from app.services.allergen.service import AllergenService


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_cache_client() -> MagicMock:
    """Create mock Redis cache client."""
    client = MagicMock()
    client.get = AsyncMock(return_value=None)
    client.setex = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_repository() -> MagicMock:
    """Create mock AllergenRepository."""
    repo = MagicMock()
    repo.get_by_ingredient_name = AsyncMock(return_value=[])
    repo.get_by_ingredient_name_fuzzy = AsyncMock(return_value=[])
    repo.get_by_ingredient_names = AsyncMock(return_value={})
    return repo


@pytest.fixture
def mock_off_client() -> MagicMock:
    """Create mock OpenFoodFactsClient."""
    client = MagicMock()
    client.search_by_name = AsyncMock(return_value=None)
    client.initialize = AsyncMock()
    client.shutdown = AsyncMock()
    return client


@pytest.fixture
def sample_allergen_data() -> AllergenData:
    """Create sample allergen data for testing."""
    return AllergenData(
        ingredient_id=1,
        ingredient_name="flour",
        usda_food_description="Wheat flour, white, all-purpose",
        allergen_type="GLUTEN",
        presence_type="CONTAINS",
        confidence_score=Decimal("0.99"),
        source_notes="Contains wheat gluten",
        data_source="USDA",
        profile_confidence=Decimal("1.0"),
    )


@pytest.fixture
def service(
    mock_cache_client: MagicMock,
    mock_repository: MagicMock,
    mock_off_client: MagicMock,
) -> AllergenService:
    """Create AllergenService with mocked dependencies."""
    return AllergenService(
        cache_client=mock_cache_client,
        repository=mock_repository,
        off_client=mock_off_client,
    )


class TestServiceLifecycle:
    """Tests for service lifecycle methods."""

    async def test_initialize_sets_flag(
        self,
        mock_cache_client: MagicMock,
        mock_repository: MagicMock,
        mock_off_client: MagicMock,
    ) -> None:
        """Should set initialized flag on initialize."""
        service = AllergenService(
            cache_client=mock_cache_client,
            repository=mock_repository,
            off_client=mock_off_client,
        )
        assert not service._initialized

        await service.initialize()

        assert service._initialized

        await service.shutdown()

    async def test_initialize_creates_default_dependencies(
        self,
    ) -> None:
        """Should create repository and OFF client if not provided."""
        service = AllergenService()
        await service.initialize()

        assert service._repository is not None
        assert service._off_client is not None

        await service.shutdown()

    async def test_shutdown_clears_flag(
        self,
        service: AllergenService,
    ) -> None:
        """Should clear initialized flag on shutdown."""
        await service.initialize()
        await service.shutdown()

        assert not service._initialized


class TestGetIngredientAllergens:
    """Tests for get_ingredient_allergens method."""

    async def test_returns_none_when_not_initialized(
        self,
        service: AllergenService,
    ) -> None:
        """Should return None if service not initialized."""
        result = await service.get_ingredient_allergens("flour")
        assert result is None

    async def test_returns_cached_result(
        self,
        service: AllergenService,
        mock_cache_client: MagicMock,
    ) -> None:
        """Should return cached result if available."""
        await service.initialize()

        cached_response = IngredientAllergenResponse(
            ingredient_name="flour",
            allergens=[AllergenInfo(allergen=Allergen.GLUTEN)],
            data_source=AllergenDataSource.USDA,
        )
        mock_cache_client.get.return_value = orjson.dumps(
            cached_response.model_dump(mode="json")
        )

        result = await service.get_ingredient_allergens("flour")

        assert result is not None
        assert result.ingredient_name == "flour"
        assert result.allergens[0].allergen == Allergen.GLUTEN

        await service.shutdown()

    async def test_returns_database_result(
        self,
        service: AllergenService,
        mock_repository: MagicMock,
        sample_allergen_data: AllergenData,
    ) -> None:
        """Should return result from database."""
        await service.initialize()
        mock_repository.get_by_ingredient_name.return_value = [sample_allergen_data]

        result = await service.get_ingredient_allergens("flour")

        assert result is not None
        assert result.ingredient_name == "flour"
        assert result.allergens[0].allergen == Allergen.GLUTEN
        assert result.data_source == AllergenDataSource.USDA

        await service.shutdown()

    async def test_falls_back_to_fuzzy_match(
        self,
        service: AllergenService,
        mock_repository: MagicMock,
        sample_allergen_data: AllergenData,
    ) -> None:
        """Should fall back to fuzzy match if exact match fails."""
        await service.initialize()
        mock_repository.get_by_ingredient_name.return_value = []
        mock_repository.get_by_ingredient_name_fuzzy.return_value = [
            sample_allergen_data
        ]

        result = await service.get_ingredient_allergens("flur")

        assert result is not None
        mock_repository.get_by_ingredient_name_fuzzy.assert_called_once()

        await service.shutdown()

    async def test_falls_back_to_open_food_facts(
        self,
        service: AllergenService,
        mock_off_client: MagicMock,
    ) -> None:
        """Should fall back to OFF if database lookup fails."""
        await service.initialize()

        mock_off_client.search_by_name.return_value = OpenFoodFactsProduct(
            product_name="Wheat Flour",
            allergens=(
                OpenFoodFactsAllergen(Allergen.GLUTEN, "CONTAINS"),
                OpenFoodFactsAllergen(Allergen.WHEAT, "CONTAINS"),
            ),
        )

        result = await service.get_ingredient_allergens("flour")

        assert result is not None
        assert result.data_source == AllergenDataSource.OPEN_FOOD_FACTS
        assert len(result.allergens) == 2

        await service.shutdown()

    async def test_returns_none_when_not_found(
        self,
        service: AllergenService,
    ) -> None:
        """Should return None when no data found in any tier."""
        await service.initialize()

        result = await service.get_ingredient_allergens("unknown-ingredient")

        assert result is None

        await service.shutdown()

    async def test_caches_successful_result(
        self,
        service: AllergenService,
        mock_cache_client: MagicMock,
        mock_repository: MagicMock,
        sample_allergen_data: AllergenData,
    ) -> None:
        """Should cache result on success."""
        await service.initialize()
        mock_repository.get_by_ingredient_name.return_value = [sample_allergen_data]

        await service.get_ingredient_allergens("flour")

        mock_cache_client.setex.assert_called_once()

        await service.shutdown()


class TestGetRecipeAllergens:
    """Tests for get_recipe_allergens method."""

    async def test_aggregates_allergens(
        self,
        service: AllergenService,
        mock_repository: MagicMock,
        sample_allergen_data: AllergenData,
    ) -> None:
        """Should aggregate allergens from multiple ingredients."""
        await service.initialize()

        flour_data = sample_allergen_data
        butter_data = AllergenData(
            ingredient_id=2,
            ingredient_name="butter",
            usda_food_description="Butter, salted",
            allergen_type="MILK",
            presence_type="CONTAINS",
            confidence_score=Decimal("1.0"),
            source_notes=None,
            data_source="USDA",
            profile_confidence=Decimal("1.0"),
        )

        # Mock to return different data based on call
        mock_repository.get_by_ingredient_name.side_effect = [
            [flour_data],
            [butter_data],
        ]

        ingredients = [
            Ingredient(ingredient_id=1, name="flour"),
            Ingredient(ingredient_id=2, name="butter"),
        ]

        result = await service.get_recipe_allergens(ingredients)

        assert Allergen.GLUTEN in result.contains
        assert Allergen.MILK in result.contains
        assert len(result.missing_ingredients) == 0

        await service.shutdown()

    async def test_tracks_missing_ingredients(
        self,
        service: AllergenService,
    ) -> None:
        """Should track ingredient IDs without allergen data."""
        await service.initialize()

        ingredients = [
            Ingredient(ingredient_id=1, name="unknown1"),
            Ingredient(ingredient_id=2, name="unknown2"),
        ]

        result = await service.get_recipe_allergens(ingredients)

        assert 1 in result.missing_ingredients
        assert 2 in result.missing_ingredients

        await service.shutdown()

    async def test_includes_details_when_requested(
        self,
        service: AllergenService,
        mock_repository: MagicMock,
        sample_allergen_data: AllergenData,
    ) -> None:
        """Should include per-ingredient details when requested."""
        await service.initialize()
        mock_repository.get_by_ingredient_name.return_value = [sample_allergen_data]

        ingredients = [Ingredient(ingredient_id=1, name="flour")]

        result = await service.get_recipe_allergens(ingredients, include_details=True)

        assert result.ingredient_details is not None
        assert "flour" in result.ingredient_details

        await service.shutdown()

    async def test_excludes_details_by_default(
        self,
        service: AllergenService,
        mock_repository: MagicMock,
        sample_allergen_data: AllergenData,
    ) -> None:
        """Should not include per-ingredient details by default."""
        await service.initialize()
        mock_repository.get_by_ingredient_name.return_value = [sample_allergen_data]

        ingredients = [Ingredient(ingredient_id=1, name="flour")]

        result = await service.get_recipe_allergens(ingredients)

        assert result.ingredient_details is None

        await service.shutdown()


class TestAllergenAggregation:
    """Tests for _aggregate_allergens method."""

    def test_deduplicates_allergens(self) -> None:
        """Should keep highest confidence for duplicate allergens."""
        service = AllergenService()

        responses = [
            IngredientAllergenResponse(
                allergens=[AllergenInfo(allergen=Allergen.GLUTEN, confidence_score=0.8)]
            ),
            IngredientAllergenResponse(
                allergens=[
                    AllergenInfo(allergen=Allergen.GLUTEN, confidence_score=0.95)
                ]
            ),
        ]

        _contains, _may_contain, all_allergens = service._aggregate_allergens(responses)

        assert len(all_allergens) == 1
        assert all_allergens[0].confidence_score == 0.95

    def test_separates_contains_and_may_contain(self) -> None:
        """Should separate CONTAINS from MAY_CONTAIN/TRACES."""
        service = AllergenService()

        responses = [
            IngredientAllergenResponse(
                allergens=[
                    AllergenInfo(
                        allergen=Allergen.GLUTEN,
                        presence_type=AllergenPresenceType.CONTAINS,
                    ),
                    AllergenInfo(
                        allergen=Allergen.TREE_NUTS,
                        presence_type=AllergenPresenceType.MAY_CONTAIN,
                    ),
                ]
            )
        ]

        contains, may_contain, _ = service._aggregate_allergens(responses)

        assert Allergen.GLUTEN in contains
        assert Allergen.TREE_NUTS in may_contain
        assert Allergen.GLUTEN not in may_contain
        assert Allergen.TREE_NUTS not in contains

    def test_upgrades_may_contain_to_contains(self) -> None:
        """Should upgrade to CONTAINS if any ingredient definitely contains."""
        service = AllergenService()

        responses = [
            IngredientAllergenResponse(
                allergens=[
                    AllergenInfo(
                        allergen=Allergen.MILK,
                        presence_type=AllergenPresenceType.MAY_CONTAIN,
                    )
                ]
            ),
            IngredientAllergenResponse(
                allergens=[
                    AllergenInfo(
                        allergen=Allergen.MILK,
                        presence_type=AllergenPresenceType.CONTAINS,
                    )
                ]
            ),
        ]

        contains, may_contain, _ = service._aggregate_allergens(responses)

        assert Allergen.MILK in contains
        assert Allergen.MILK not in may_contain


class TestCaching:
    """Tests for caching methods."""

    async def test_cache_key_normalized(
        self,
        service: AllergenService,
    ) -> None:
        """Should normalize ingredient names in cache keys."""
        key1 = service._make_cache_key("FLOUR")
        key2 = service._make_cache_key("flour")
        key3 = service._make_cache_key("  flour  ")

        assert key1 == key2 == key3
        assert key1 == "allergen:flour"

    async def test_cache_read_handles_errors(
        self,
        service: AllergenService,
        mock_cache_client: MagicMock,
    ) -> None:
        """Should handle cache read errors gracefully."""
        await service.initialize()
        mock_cache_client.get.side_effect = Exception("Redis error")

        result = await service._get_from_cache("flour")

        assert result is None

        await service.shutdown()

    async def test_cache_write_handles_errors(
        self,
        service: AllergenService,
        mock_cache_client: MagicMock,
    ) -> None:
        """Should handle cache write errors gracefully."""
        await service.initialize()
        mock_cache_client.setex.side_effect = Exception("Redis error")

        response = IngredientAllergenResponse(ingredient_name="flour")

        # Should not raise
        await service._cache_result("flour", response)

        await service.shutdown()
