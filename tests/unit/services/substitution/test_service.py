"""Unit tests for SubstitutionService."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import orjson
import pytest

from app.database.repositories.nutrition import NutritionData
from app.llm.exceptions import (
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
    LLMValidationError,
)
from app.llm.prompts.substitution import SubstitutionListResult, SubstitutionResult
from app.schemas.enums import IngredientUnit
from app.schemas.ingredient import Quantity
from app.services.substitution.exceptions import LLMGenerationError
from app.services.substitution.service import SubstitutionService


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_cache_client() -> MagicMock:
    """Create mock Redis cache client."""
    client = MagicMock()
    client.get = AsyncMock(return_value=None)
    client.setex = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Create mock LLM client."""
    client = MagicMock()
    client.generate_structured = AsyncMock()
    return client


@pytest.fixture
def mock_nutrition_repository() -> MagicMock:
    """Create mock NutritionRepository."""
    repo = MagicMock()
    repo.get_by_ingredient_name = AsyncMock(return_value=None)
    repo.get_by_ingredient_name_fuzzy = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def sample_nutrition_data() -> NutritionData:
    """Create sample nutrition data for testing."""
    return NutritionData(
        ingredient_id=1,
        ingredient_name="butter",
        fdc_id=12345,
        usda_food_description="Butter, salted",
        serving_size_g=Decimal(100),
        food_group="DAIRY",
    )


@pytest.fixture
def sample_substitution_result() -> SubstitutionListResult:
    """Create sample substitution result."""
    return SubstitutionListResult(
        substitutions=[
            SubstitutionResult(
                ingredient="coconut oil",
                ratio=1.0,
                measurement="CUP",
                notes="Best for baking",
                confidence=0.9,
            ),
            SubstitutionResult(
                ingredient="olive oil",
                ratio=0.75,
                measurement="CUP",
                notes="Best for savory",
                confidence=0.85,
            ),
            SubstitutionResult(
                ingredient="applesauce",
                ratio=0.5,
                measurement="CUP",
                notes="Good for baking",
                confidence=0.8,
            ),
        ]
    )


@pytest.fixture
def service(
    mock_cache_client: MagicMock,
    mock_llm_client: MagicMock,
    mock_nutrition_repository: MagicMock,
) -> SubstitutionService:
    """Create SubstitutionService with mocked dependencies."""
    return SubstitutionService(
        cache_client=mock_cache_client,
        llm_client=mock_llm_client,
        nutrition_repository=mock_nutrition_repository,
    )


class TestSubstitutionServiceLifecycle:
    """Tests for service lifecycle methods."""

    async def test_initialize_sets_initialized_flag(
        self,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should set initialized flag on initialize."""
        service = SubstitutionService(
            cache_client=mock_cache_client,
            llm_client=mock_llm_client,
        )
        assert service._initialized is False

        await service.initialize()

        assert service._initialized is True

        await service.shutdown()

    async def test_initialize_without_cache_client(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should try to get cache client if not provided."""
        from unittest.mock import patch

        mock_cache = MagicMock()
        service = SubstitutionService(
            cache_client=None,
            llm_client=mock_llm_client,
        )

        with patch(
            "app.services.substitution.service.get_cache_client",
            return_value=mock_cache,
        ):
            await service.initialize()

        assert service._initialized is True
        assert service._cache_client is mock_cache
        await service.shutdown()

    async def test_initialize_cache_unavailable_logs_warning(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should log warning when cache unavailable."""
        from unittest.mock import patch

        service = SubstitutionService(
            cache_client=None,
            llm_client=mock_llm_client,
        )

        with patch(
            "app.services.substitution.service.get_cache_client",
            side_effect=RuntimeError("Redis not available"),
        ):
            await service.initialize()

        # Should still initialize
        assert service._initialized is True
        # Cache should remain None
        assert service._cache_client is None
        await service.shutdown()

    async def test_shutdown_completes_without_error(
        self,
        service: SubstitutionService,
    ) -> None:
        """Should shutdown without error."""
        await service.initialize()
        await service.shutdown()  # Should not raise


class TestGetSubstitutions:
    """Tests for get_substitutions method."""

    async def test_returns_none_when_not_initialized(
        self,
        service: SubstitutionService,
    ) -> None:
        """Should return None if service not initialized."""
        # Don't call initialize
        result = await service.get_substitutions("butter")
        assert result is None

    async def test_returns_none_when_llm_not_available(
        self,
        mock_cache_client: MagicMock,
        mock_nutrition_repository: MagicMock,
    ) -> None:
        """Should return None when LLM client not provided."""
        service = SubstitutionService(
            cache_client=mock_cache_client,
            llm_client=None,  # No LLM client
            nutrition_repository=mock_nutrition_repository,
        )
        await service.initialize()

        result = await service.get_substitutions("butter")
        assert result is None

        await service.shutdown()

    async def test_returns_substitutions_from_cache_hit(
        self,
        service: SubstitutionService,
        mock_cache_client: MagicMock,
        sample_substitution_result: SubstitutionListResult,
    ) -> None:
        """Should return cached substitutions on cache hit."""
        await service.initialize()

        # Set up cache hit
        cached_data = orjson.dumps(sample_substitution_result.model_dump(mode="json"))
        mock_cache_client.get.return_value = cached_data

        result = await service.get_substitutions("butter")

        assert result is not None
        assert len(result.recommended_substitutions) == 3
        mock_cache_client.get.assert_called_once()

        await service.shutdown()

    async def test_generates_via_llm_on_cache_miss(
        self,
        service: SubstitutionService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
        sample_substitution_result: SubstitutionListResult,
    ) -> None:
        """Should generate via LLM on cache miss."""
        await service.initialize()

        # Set up cache miss
        mock_cache_client.get.return_value = None
        mock_llm_client.generate_structured.return_value = sample_substitution_result

        result = await service.get_substitutions("butter")

        assert result is not None
        assert len(result.recommended_substitutions) == 3
        mock_llm_client.generate_structured.assert_called_once()

        await service.shutdown()

    async def test_caches_llm_result(
        self,
        service: SubstitutionService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
        sample_substitution_result: SubstitutionListResult,
    ) -> None:
        """Should cache result after LLM generation."""
        await service.initialize()

        mock_cache_client.get.return_value = None
        mock_llm_client.generate_structured.return_value = sample_substitution_result

        await service.get_substitutions("butter")

        mock_cache_client.setex.assert_called_once()
        call_args = mock_cache_client.setex.call_args
        # Check TTL is 7 days (604800 seconds)
        assert call_args[0][1] == 604800

        await service.shutdown()

    async def test_applies_pagination_correctly(
        self,
        service: SubstitutionService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
        sample_substitution_result: SubstitutionListResult,
    ) -> None:
        """Should apply pagination to results."""
        await service.initialize()

        mock_cache_client.get.return_value = None
        mock_llm_client.generate_structured.return_value = sample_substitution_result

        # Request with limit=1, offset=1
        result = await service.get_substitutions("butter", limit=1, offset=1)

        assert result is not None
        assert len(result.recommended_substitutions) == 1
        assert result.recommended_substitutions[0].ingredient == "olive oil"
        assert result.count == 3  # Total count
        assert result.limit == 1
        assert result.offset == 1

        await service.shutdown()

    async def test_includes_quantity_in_response(
        self,
        service: SubstitutionService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
        sample_substitution_result: SubstitutionListResult,
    ) -> None:
        """Should include quantity in response when provided."""
        await service.initialize()

        mock_cache_client.get.return_value = None
        mock_llm_client.generate_structured.return_value = sample_substitution_result

        quantity = Quantity(amount=1.0, measurement=IngredientUnit.CUP)
        result = await service.get_substitutions("butter", quantity=quantity)

        assert result is not None
        assert result.ingredient.quantity is not None
        assert result.ingredient.quantity.amount == 1.0
        # Substitutions should have adjusted quantities
        for sub in result.recommended_substitutions:
            assert sub.quantity is not None

        await service.shutdown()

    async def test_resolves_ingredient_from_repository(
        self,
        service: SubstitutionService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
        mock_nutrition_repository: MagicMock,
        sample_nutrition_data: NutritionData,
        sample_substitution_result: SubstitutionListResult,
    ) -> None:
        """Should resolve ingredient name from nutrition repository."""
        await service.initialize()

        mock_cache_client.get.return_value = None
        mock_nutrition_repository.get_by_ingredient_name.return_value = (
            sample_nutrition_data
        )
        mock_llm_client.generate_structured.return_value = sample_substitution_result

        result = await service.get_substitutions("bttr")  # Misspelled

        assert result is not None
        assert result.ingredient.name == "butter"  # Resolved name

        await service.shutdown()


class TestGenerateSubstitutions:
    """Tests for _generate_substitutions internal method."""

    async def test_returns_none_when_llm_not_available(
        self,
        mock_cache_client: MagicMock,
        mock_nutrition_repository: MagicMock,
    ) -> None:
        """Should return None if LLM client not available."""
        service = SubstitutionService(
            cache_client=mock_cache_client,
            llm_client=None,
            nutrition_repository=mock_nutrition_repository,
        )
        await service.initialize()

        result = await service._generate_substitutions(
            ingredient_name="butter",
            food_group="DAIRY",
            quantity=None,
        )

        assert result is None
        await service.shutdown()

    async def test_handles_dict_result_from_cached_llm(
        self,
        service: SubstitutionService,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should handle dict result (from LLM cache) and convert to Pydantic."""
        await service.initialize()

        dict_result = {
            "substitutions": [
                {
                    "ingredient": "coconut oil",
                    "ratio": 1.0,
                    "measurement": "CUP",
                    "notes": "Best for baking",
                    "confidence": 0.9,
                }
            ]
        }
        mock_llm_client.generate_structured.return_value = dict_result

        result = await service._generate_substitutions(
            ingredient_name="butter",
            food_group="DAIRY",
            quantity=None,
        )

        assert result is not None
        assert isinstance(result, SubstitutionListResult)
        assert len(result.substitutions) == 1
        await service.shutdown()


class TestCacheOperations:
    """Tests for cache operation edge cases."""

    async def test_get_from_cache_returns_none_when_no_cache_client(
        self,
        mock_llm_client: MagicMock,
        mock_nutrition_repository: MagicMock,
    ) -> None:
        """Should return None when cache client is None."""
        service = SubstitutionService(
            cache_client=None,
            llm_client=mock_llm_client,
            nutrition_repository=mock_nutrition_repository,
        )

        result = await service._get_from_cache("butter")

        assert result is None

    async def test_save_to_cache_does_nothing_when_no_cache_client(
        self,
        mock_llm_client: MagicMock,
        mock_nutrition_repository: MagicMock,
        sample_substitution_result: SubstitutionListResult,
    ) -> None:
        """Should not error when cache client is None."""
        service = SubstitutionService(
            cache_client=None,
            llm_client=mock_llm_client,
            nutrition_repository=mock_nutrition_repository,
        )

        # Should not raise
        await service._save_to_cache("butter", sample_substitution_result)


class TestGetSubstitutionsExtended:
    """Extended tests for get_substitutions method."""

    async def test_returns_none_when_generation_returns_none(
        self,
        service: SubstitutionService,
        mock_cache_client: MagicMock,
    ) -> None:
        """Should return None when substitution generation returns None."""
        from unittest.mock import patch

        await service.initialize()

        mock_cache_client.get.return_value = None

        # Mock _generate_substitutions to return None
        with patch.object(service, "_generate_substitutions", return_value=None):
            result = await service.get_substitutions("butter")

        assert result is None
        await service.shutdown()

    async def test_fuzzy_match_when_exact_not_found(
        self,
        service: SubstitutionService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
        mock_nutrition_repository: MagicMock,
        sample_nutrition_data: NutritionData,
        sample_substitution_result: SubstitutionListResult,
    ) -> None:
        """Should try fuzzy match when exact match not found."""
        await service.initialize()

        mock_cache_client.get.return_value = None
        # Exact match returns None
        mock_nutrition_repository.get_by_ingredient_name.return_value = None
        # Fuzzy match returns data
        mock_nutrition_repository.get_by_ingredient_name_fuzzy.return_value = (
            sample_nutrition_data
        )
        mock_llm_client.generate_structured.return_value = sample_substitution_result

        result = await service.get_substitutions("bttr")

        assert result is not None
        mock_nutrition_repository.get_by_ingredient_name_fuzzy.assert_called_once()
        await service.shutdown()


class TestErrorHandling:
    """Tests for error handling."""

    async def test_raises_llm_generation_error_on_rate_limit(
        self,
        service: SubstitutionService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should raise LLMGenerationError on rate limit."""
        await service.initialize()

        mock_cache_client.get.return_value = None
        mock_llm_client.generate_structured.side_effect = LLMRateLimitError(
            "Rate limited"
        )

        with pytest.raises(LLMGenerationError) as exc_info:
            await service.get_substitutions("butter")

        assert "rate limit" in str(exc_info.value).lower()
        await service.shutdown()

    async def test_raises_llm_generation_error_on_generic_exception(
        self,
        service: SubstitutionService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should raise LLMGenerationError on generic exception."""
        await service.initialize()

        mock_cache_client.get.return_value = None
        mock_llm_client.generate_structured.side_effect = Exception("Something broke")

        with pytest.raises(LLMGenerationError) as exc_info:
            await service.get_substitutions("butter")

        assert "unexpected" in str(exc_info.value).lower()
        await service.shutdown()

    async def test_raises_llm_generation_error_on_timeout(
        self,
        service: SubstitutionService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should raise LLMGenerationError on LLM timeout."""
        await service.initialize()

        mock_cache_client.get.return_value = None
        mock_llm_client.generate_structured.side_effect = LLMTimeoutError(
            "Request timed out"
        )

        with pytest.raises(LLMGenerationError) as exc_info:
            await service.get_substitutions("butter")

        assert "unavailable" in str(exc_info.value).lower()

        await service.shutdown()

    async def test_raises_llm_generation_error_on_unavailable(
        self,
        service: SubstitutionService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should raise LLMGenerationError on LLM unavailable."""
        await service.initialize()

        mock_cache_client.get.return_value = None
        mock_llm_client.generate_structured.side_effect = LLMUnavailableError(
            "Service unavailable"
        )

        with pytest.raises(LLMGenerationError):
            await service.get_substitutions("butter")

        await service.shutdown()

    async def test_raises_llm_generation_error_on_validation_failure(
        self,
        service: SubstitutionService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should raise LLMGenerationError on response validation failure."""
        await service.initialize()

        mock_cache_client.get.return_value = None
        mock_llm_client.generate_structured.side_effect = LLMValidationError(
            "Invalid response"
        )

        with pytest.raises(LLMGenerationError) as exc_info:
            await service.get_substitutions("butter")

        assert "invalid" in str(exc_info.value).lower()

        await service.shutdown()

    async def test_handles_cache_read_error_gracefully(
        self,
        service: SubstitutionService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
        sample_substitution_result: SubstitutionListResult,
    ) -> None:
        """Should fall back to LLM on cache read error."""
        await service.initialize()

        # Simulate cache read error
        mock_cache_client.get.side_effect = Exception("Redis error")
        mock_llm_client.generate_structured.return_value = sample_substitution_result

        # Should not raise, should fall back to LLM
        result = await service.get_substitutions("butter")

        assert result is not None
        mock_llm_client.generate_structured.assert_called_once()

        await service.shutdown()

    async def test_handles_cache_write_error_gracefully(
        self,
        service: SubstitutionService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
        sample_substitution_result: SubstitutionListResult,
    ) -> None:
        """Should return result even on cache write error."""
        await service.initialize()

        mock_cache_client.get.return_value = None
        mock_cache_client.setex.side_effect = Exception("Redis error")
        mock_llm_client.generate_structured.return_value = sample_substitution_result

        # Should not raise, should return result
        result = await service.get_substitutions("butter")

        assert result is not None

        await service.shutdown()


class TestCacheKeyGeneration:
    """Tests for cache key generation."""

    def test_normalizes_ingredient_name(
        self,
        service: SubstitutionService,
    ) -> None:
        """Should normalize ingredient name in cache key."""
        key1 = service._make_cache_key("Butter")
        key2 = service._make_cache_key("butter")
        key3 = service._make_cache_key("  BUTTER  ")

        assert key1 == key2 == key3
        assert key1 == "substitution:butter"
