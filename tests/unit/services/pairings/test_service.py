"""Unit tests for PairingsService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import orjson
import pytest

from app.llm.exceptions import LLMTimeoutError, LLMUnavailableError, LLMValidationError
from app.llm.prompts.pairings import PairingListResult, PairingResult
from app.services.pairings.constants import PAIRINGS_CACHE_TTL_SECONDS
from app.services.pairings.exceptions import LLMGenerationError
from app.services.pairings.service import PairingsService, RecipeContext


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
def sample_pairing_result() -> PairingListResult:
    """Create sample pairing result."""
    return PairingListResult(
        pairings=[
            PairingResult(
                recipe_name="Roasted Asparagus with Parmesan",
                url="https://www.allrecipes.com/recipe/123/roasted-asparagus/",
                pairing_reason="Light vegetable side that complements rich salmon",
                cuisine_type="American",
                confidence=0.95,
            ),
            PairingResult(
                recipe_name="Lemon Rice Pilaf",
                url="https://www.foodnetwork.com/recipes/lemon-rice-pilaf",
                pairing_reason="Citrus notes echo the lemon in the salmon",
                cuisine_type="Mediterranean",
                confidence=0.9,
            ),
            PairingResult(
                recipe_name="Caesar Salad",
                url="https://www.epicurious.com/recipes/caesar-salad",
                pairing_reason="Classic pairing with fish dishes",
                cuisine_type="Italian",
                confidence=0.85,
            ),
        ]
    )


@pytest.fixture
def sample_recipe_context() -> RecipeContext:
    """Create sample recipe context."""
    return RecipeContext(
        recipe_id=123,
        title="Grilled Salmon with Lemon and Dill",
        description="A delicious grilled salmon recipe with fresh lemon and dill",
        ingredients=["salmon fillet", "lemon", "dill", "olive oil", "garlic"],
    )


@pytest.fixture
def service(
    mock_cache_client: MagicMock,
    mock_llm_client: MagicMock,
) -> PairingsService:
    """Create PairingsService with mocked dependencies."""
    return PairingsService(
        cache_client=mock_cache_client,
        llm_client=mock_llm_client,
    )


class TestPairingsServiceLifecycle:
    """Tests for service lifecycle methods."""

    async def test_initialize_sets_initialized_flag(
        self,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should set initialized flag on initialize."""
        service = PairingsService(
            cache_client=mock_cache_client,
            llm_client=mock_llm_client,
        )
        assert service._initialized is False

        await service.initialize()

        assert service._initialized is True

        await service.shutdown()

    async def test_shutdown_completes_without_error(
        self,
        service: PairingsService,
    ) -> None:
        """Should shutdown without error."""
        await service.initialize()
        await service.shutdown()  # Should not raise


class TestGetPairings:
    """Tests for get_pairings method."""

    async def test_returns_none_when_not_initialized(
        self,
        service: PairingsService,
        sample_recipe_context: RecipeContext,
    ) -> None:
        """Should return None if service not initialized."""
        # Don't call initialize
        result = await service.get_pairings(sample_recipe_context)
        assert result is None

    async def test_returns_none_when_llm_not_available(
        self,
        mock_cache_client: MagicMock,
        sample_recipe_context: RecipeContext,
    ) -> None:
        """Should return None when LLM client not provided."""
        service = PairingsService(
            cache_client=mock_cache_client,
            llm_client=None,  # No LLM client
        )
        await service.initialize()

        result = await service.get_pairings(sample_recipe_context)
        assert result is None

        await service.shutdown()

    async def test_returns_pairings_from_cache_hit(
        self,
        service: PairingsService,
        mock_cache_client: MagicMock,
        sample_pairing_result: PairingListResult,
        sample_recipe_context: RecipeContext,
    ) -> None:
        """Should return cached pairings on cache hit."""
        await service.initialize()

        # Set up cache hit
        cached_data = orjson.dumps(sample_pairing_result.model_dump(mode="json"))
        mock_cache_client.get.return_value = cached_data

        result = await service.get_pairings(sample_recipe_context)

        assert result is not None
        assert len(result.pairing_suggestions) == 3
        mock_cache_client.get.assert_called_once()

        await service.shutdown()

    async def test_generates_via_llm_on_cache_miss(
        self,
        service: PairingsService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
        sample_pairing_result: PairingListResult,
        sample_recipe_context: RecipeContext,
    ) -> None:
        """Should generate via LLM on cache miss."""
        await service.initialize()

        # Set up cache miss
        mock_cache_client.get.return_value = None
        mock_llm_client.generate_structured.return_value = sample_pairing_result

        result = await service.get_pairings(sample_recipe_context)

        assert result is not None
        assert len(result.pairing_suggestions) == 3
        mock_llm_client.generate_structured.assert_called_once()

        await service.shutdown()

    async def test_caches_llm_result(
        self,
        service: PairingsService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
        sample_pairing_result: PairingListResult,
        sample_recipe_context: RecipeContext,
    ) -> None:
        """Should cache LLM result with correct TTL."""
        await service.initialize()

        # Set up cache miss
        mock_cache_client.get.return_value = None
        mock_llm_client.generate_structured.return_value = sample_pairing_result

        await service.get_pairings(sample_recipe_context)

        # Verify cache was written with correct TTL
        mock_cache_client.setex.assert_called_once()
        call_args = mock_cache_client.setex.call_args
        assert call_args[0][1] == PAIRINGS_CACHE_TTL_SECONDS

        await service.shutdown()

    async def test_applies_pagination_correctly(
        self,
        service: PairingsService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
        sample_pairing_result: PairingListResult,
        sample_recipe_context: RecipeContext,
    ) -> None:
        """Should apply limit and offset correctly."""
        await service.initialize()

        mock_cache_client.get.return_value = None
        mock_llm_client.generate_structured.return_value = sample_pairing_result

        result = await service.get_pairings(sample_recipe_context, limit=2, offset=0)

        assert result is not None
        assert len(result.pairing_suggestions) == 2
        assert result.count == 3  # Total count should be 3
        assert result.limit == 2
        assert result.offset == 0

        await service.shutdown()

    async def test_applies_offset_correctly(
        self,
        service: PairingsService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
        sample_pairing_result: PairingListResult,
        sample_recipe_context: RecipeContext,
    ) -> None:
        """Should apply offset correctly."""
        await service.initialize()

        mock_cache_client.get.return_value = None
        mock_llm_client.generate_structured.return_value = sample_pairing_result

        result = await service.get_pairings(sample_recipe_context, limit=10, offset=1)

        assert result is not None
        assert len(result.pairing_suggestions) == 2  # 3 - 1 offset = 2
        assert result.count == 3  # Total count should still be 3
        assert result.offset == 1

        await service.shutdown()


class TestErrorHandling:
    """Tests for error handling."""

    async def test_raises_llm_generation_error_on_timeout(
        self,
        service: PairingsService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
        sample_recipe_context: RecipeContext,
    ) -> None:
        """Should raise LLMGenerationError on LLM timeout."""
        await service.initialize()

        mock_cache_client.get.return_value = None
        mock_llm_client.generate_structured.side_effect = LLMTimeoutError("Timeout")

        with pytest.raises(LLMGenerationError) as exc_info:
            await service.get_pairings(sample_recipe_context)

        assert exc_info.value.recipe_id == 123
        assert exc_info.value.cause is not None

        await service.shutdown()

    async def test_raises_llm_generation_error_on_unavailable(
        self,
        service: PairingsService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
        sample_recipe_context: RecipeContext,
    ) -> None:
        """Should raise LLMGenerationError when LLM unavailable."""
        await service.initialize()

        mock_cache_client.get.return_value = None
        mock_llm_client.generate_structured.side_effect = LLMUnavailableError(
            "Unavailable"
        )

        with pytest.raises(LLMGenerationError) as exc_info:
            await service.get_pairings(sample_recipe_context)

        assert "unavailable" in str(exc_info.value).lower()

        await service.shutdown()

    async def test_raises_llm_generation_error_on_validation_failure(
        self,
        service: PairingsService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
        sample_recipe_context: RecipeContext,
    ) -> None:
        """Should raise LLMGenerationError on validation failure."""
        await service.initialize()

        mock_cache_client.get.return_value = None
        mock_llm_client.generate_structured.side_effect = LLMValidationError(
            "Invalid response"
        )

        with pytest.raises(LLMGenerationError) as exc_info:
            await service.get_pairings(sample_recipe_context)

        assert "invalid" in str(exc_info.value).lower()

        await service.shutdown()

    async def test_handles_cache_read_error_gracefully(
        self,
        service: PairingsService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
        sample_pairing_result: PairingListResult,
        sample_recipe_context: RecipeContext,
    ) -> None:
        """Should handle cache read errors gracefully and generate via LLM."""
        await service.initialize()

        # Cache throws exception
        mock_cache_client.get.side_effect = Exception("Cache read error")
        mock_llm_client.generate_structured.return_value = sample_pairing_result

        # Should not raise, should fall back to LLM
        result = await service.get_pairings(sample_recipe_context)

        assert result is not None
        mock_llm_client.generate_structured.assert_called_once()

        await service.shutdown()

    async def test_handles_cache_write_error_gracefully(
        self,
        service: PairingsService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
        sample_pairing_result: PairingListResult,
        sample_recipe_context: RecipeContext,
    ) -> None:
        """Should handle cache write errors gracefully."""
        await service.initialize()

        mock_cache_client.get.return_value = None
        mock_cache_client.setex.side_effect = Exception("Cache write error")
        mock_llm_client.generate_structured.return_value = sample_pairing_result

        # Should not raise, should return result despite cache error
        result = await service.get_pairings(sample_recipe_context)

        assert result is not None

        await service.shutdown()


class TestCacheKeyGeneration:
    """Tests for cache key generation."""

    async def test_cache_key_uses_recipe_id(
        self,
        service: PairingsService,
    ) -> None:
        """Should create cache key using recipe ID."""
        cache_key = service._make_cache_key(123)
        assert cache_key == "pairing:123"

    async def test_cache_key_format(
        self,
        service: PairingsService,
    ) -> None:
        """Should have correct cache key format."""
        cache_key = service._make_cache_key(456)
        assert cache_key.startswith("pairing:")
        assert "456" in cache_key


class TestResponseTransformation:
    """Tests for response transformation."""

    async def test_transforms_pairing_result_to_web_recipe(
        self,
        service: PairingsService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
        sample_pairing_result: PairingListResult,
        sample_recipe_context: RecipeContext,
    ) -> None:
        """Should transform PairingResult to WebRecipe correctly."""
        await service.initialize()

        mock_cache_client.get.return_value = None
        mock_llm_client.generate_structured.return_value = sample_pairing_result

        result = await service.get_pairings(sample_recipe_context)

        assert result is not None
        # Verify WebRecipe fields
        first_pairing = result.pairing_suggestions[0]
        assert first_pairing.recipe_name == "Roasted Asparagus with Parmesan"
        assert (
            first_pairing.url
            == "https://www.allrecipes.com/recipe/123/roasted-asparagus/"
        )

        await service.shutdown()

    async def test_response_includes_recipe_id(
        self,
        service: PairingsService,
        mock_cache_client: MagicMock,
        mock_llm_client: MagicMock,
        sample_pairing_result: PairingListResult,
        sample_recipe_context: RecipeContext,
    ) -> None:
        """Should include recipe_id in response."""
        await service.initialize()

        mock_cache_client.get.return_value = None
        mock_llm_client.generate_structured.return_value = sample_pairing_result

        result = await service.get_pairings(sample_recipe_context)

        assert result is not None
        assert result.recipe_id == 123

        await service.shutdown()
