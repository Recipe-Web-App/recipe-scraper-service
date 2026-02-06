"""Unit tests for API dependencies.

Tests cover all service dependency functions that retrieve services
from app.state and handle unavailability scenarios.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.dependencies import (
    get_allergen_service,
    get_ingredient_parser,
    get_nutrition_service,
    get_pairings_service,
    get_popular_recipes_service,
    get_recipe_management_client,
    get_redis_cache_client,
    get_scraper_service,
    get_shopping_service,
    get_substitution_service,
)


pytestmark = pytest.mark.unit


# =============================================================================
# Helper Fixtures
# =============================================================================


@pytest.fixture
def mock_request_with_service() -> MagicMock:
    """Create a mock request with a service in app.state."""

    def _create(service_name: str, service: MagicMock | None) -> MagicMock:
        request = MagicMock()
        request.app.state = MagicMock()
        setattr(request.app.state, service_name, service)
        return request

    return _create


@pytest.fixture
def mock_service() -> MagicMock:
    """Create a generic mock service."""
    return MagicMock()


# =============================================================================
# get_scraper_service Tests
# =============================================================================


class TestGetScraperService:
    """Tests for get_scraper_service dependency."""

    async def test_returns_service_when_available(
        self,
        mock_request_with_service: MagicMock,
        mock_service: MagicMock,
    ) -> None:
        """Should return scraper service from app.state."""
        request = mock_request_with_service("scraper_service", mock_service)

        result = await get_scraper_service(request)

        assert result is mock_service

    async def test_raises_503_when_service_not_initialized(
        self,
        mock_request_with_service: MagicMock,
    ) -> None:
        """Should raise 503 when scraper service is None."""
        request = mock_request_with_service("scraper_service", None)

        with pytest.raises(HTTPException) as exc_info:
            await get_scraper_service(request)

        assert exc_info.value.status_code == 503
        assert "Recipe scraper service not available" in exc_info.value.detail

    async def test_raises_503_when_attribute_missing(self) -> None:
        """Should raise 503 when scraper_service attribute doesn't exist."""
        request = MagicMock()
        request.app.state = MagicMock(spec=[])  # Empty spec, no attributes

        with pytest.raises(HTTPException) as exc_info:
            await get_scraper_service(request)

        assert exc_info.value.status_code == 503


# =============================================================================
# get_recipe_management_client Tests
# =============================================================================


class TestGetRecipeManagementClient:
    """Tests for get_recipe_management_client dependency."""

    async def test_returns_client_when_available(
        self,
        mock_request_with_service: MagicMock,
        mock_service: MagicMock,
    ) -> None:
        """Should return recipe management client from app.state."""
        request = mock_request_with_service("recipe_management_client", mock_service)

        result = await get_recipe_management_client(request)

        assert result is mock_service

    async def test_raises_503_when_client_not_initialized(
        self,
        mock_request_with_service: MagicMock,
    ) -> None:
        """Should raise 503 when recipe management client is None."""
        request = mock_request_with_service("recipe_management_client", None)

        with pytest.raises(HTTPException) as exc_info:
            await get_recipe_management_client(request)

        assert exc_info.value.status_code == 503
        assert "Recipe management service not available" in exc_info.value.detail


# =============================================================================
# get_ingredient_parser Tests
# =============================================================================


class TestGetIngredientParser:
    """Tests for get_ingredient_parser dependency."""

    async def test_returns_parser_with_llm_client(self) -> None:
        """Should return IngredientParser when LLM client is available."""
        mock_llm_client = MagicMock()

        with patch(
            "app.api.dependencies.get_llm_client",
            return_value=mock_llm_client,
        ):
            result = await get_ingredient_parser()

        assert result is not None
        assert result._llm_client is mock_llm_client

    async def test_raises_503_when_llm_not_available(self) -> None:
        """Should raise 503 when get_llm_client raises RuntimeError."""
        with (
            patch(
                "app.api.dependencies.get_llm_client",
                side_effect=RuntimeError("LLM client not initialized"),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await get_ingredient_parser()

        assert exc_info.value.status_code == 503
        assert "Ingredient parsing service not available" in exc_info.value.detail


# =============================================================================
# get_popular_recipes_service Tests
# =============================================================================


class TestGetPopularRecipesService:
    """Tests for get_popular_recipes_service dependency."""

    async def test_returns_service_when_available(
        self,
        mock_request_with_service: MagicMock,
        mock_service: MagicMock,
    ) -> None:
        """Should return popular recipes service from app.state."""
        request = mock_request_with_service("popular_recipes_service", mock_service)

        result = await get_popular_recipes_service(request)

        assert result is mock_service

    async def test_raises_503_when_service_not_initialized(
        self,
        mock_request_with_service: MagicMock,
    ) -> None:
        """Should raise 503 when popular recipes service is None."""
        request = mock_request_with_service("popular_recipes_service", None)

        with pytest.raises(HTTPException) as exc_info:
            await get_popular_recipes_service(request)

        assert exc_info.value.status_code == 503
        assert "Popular recipes service not available" in exc_info.value.detail


# =============================================================================
# get_nutrition_service Tests
# =============================================================================


class TestGetNutritionService:
    """Tests for get_nutrition_service dependency."""

    async def test_returns_service_when_available(
        self,
        mock_request_with_service: MagicMock,
        mock_service: MagicMock,
    ) -> None:
        """Should return nutrition service from app.state."""
        request = mock_request_with_service("nutrition_service", mock_service)

        result = await get_nutrition_service(request)

        assert result is mock_service

    async def test_raises_503_when_service_not_initialized(
        self,
        mock_request_with_service: MagicMock,
    ) -> None:
        """Should raise 503 when nutrition service is None."""
        request = mock_request_with_service("nutrition_service", None)

        with pytest.raises(HTTPException) as exc_info:
            await get_nutrition_service(request)

        assert exc_info.value.status_code == 503
        assert "Nutrition service not available" in exc_info.value.detail


# =============================================================================
# get_allergen_service Tests
# =============================================================================


class TestGetAllergenService:
    """Tests for get_allergen_service dependency."""

    async def test_returns_service_when_available(
        self,
        mock_request_with_service: MagicMock,
        mock_service: MagicMock,
    ) -> None:
        """Should return allergen service from app.state."""
        request = mock_request_with_service("allergen_service", mock_service)

        result = await get_allergen_service(request)

        assert result is mock_service

    async def test_raises_503_when_service_not_initialized(
        self,
        mock_request_with_service: MagicMock,
    ) -> None:
        """Should raise 503 when allergen service is None."""
        request = mock_request_with_service("allergen_service", None)

        with pytest.raises(HTTPException) as exc_info:
            await get_allergen_service(request)

        assert exc_info.value.status_code == 503
        assert "Allergen service not available" in exc_info.value.detail


# =============================================================================
# get_redis_cache_client Tests
# =============================================================================


class TestGetRedisCacheClient:
    """Tests for get_redis_cache_client dependency."""

    async def test_returns_cache_client_when_available(self) -> None:
        """Should return Redis client when cache is available."""
        mock_cache = MagicMock()

        with patch(
            "app.api.dependencies.get_cache_client",
            new_callable=AsyncMock,
            return_value=mock_cache,
        ):
            result = await get_redis_cache_client()

        assert result is mock_cache

    async def test_returns_none_when_cache_unavailable(self) -> None:
        """Should return None when get_cache_client raises exception."""
        with patch(
            "app.api.dependencies.get_cache_client",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Redis not initialized"),
        ):
            result = await get_redis_cache_client()

        assert result is None

    async def test_handles_connection_error_gracefully(self) -> None:
        """Should return None on connection errors."""
        with patch(
            "app.api.dependencies.get_cache_client",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Cannot connect to Redis"),
        ):
            result = await get_redis_cache_client()

        assert result is None


# =============================================================================
# get_shopping_service Tests
# =============================================================================


class TestGetShoppingService:
    """Tests for get_shopping_service dependency."""

    async def test_returns_service_when_available(
        self,
        mock_request_with_service: MagicMock,
        mock_service: MagicMock,
    ) -> None:
        """Should return shopping service from app.state."""
        request = mock_request_with_service("shopping_service", mock_service)

        result = await get_shopping_service(request)

        assert result is mock_service

    async def test_raises_503_when_service_not_initialized(
        self,
        mock_request_with_service: MagicMock,
    ) -> None:
        """Should raise 503 when shopping service is None."""
        request = mock_request_with_service("shopping_service", None)

        with pytest.raises(HTTPException) as exc_info:
            await get_shopping_service(request)

        assert exc_info.value.status_code == 503
        assert "Shopping service not available" in exc_info.value.detail


# =============================================================================
# get_substitution_service Tests
# =============================================================================


class TestGetSubstitutionService:
    """Tests for get_substitution_service dependency."""

    async def test_returns_service_when_available(
        self,
        mock_request_with_service: MagicMock,
        mock_service: MagicMock,
    ) -> None:
        """Should return substitution service from app.state."""
        request = mock_request_with_service("substitution_service", mock_service)

        result = await get_substitution_service(request)

        assert result is mock_service

    async def test_raises_503_when_service_not_initialized(
        self,
        mock_request_with_service: MagicMock,
    ) -> None:
        """Should raise 503 when substitution service is None."""
        request = mock_request_with_service("substitution_service", None)

        with pytest.raises(HTTPException) as exc_info:
            await get_substitution_service(request)

        assert exc_info.value.status_code == 503
        assert "Substitution service not available" in exc_info.value.detail


# =============================================================================
# get_pairings_service Tests
# =============================================================================


class TestGetPairingsService:
    """Tests for get_pairings_service dependency."""

    async def test_returns_service_when_available(
        self,
        mock_request_with_service: MagicMock,
        mock_service: MagicMock,
    ) -> None:
        """Should return pairings service from app.state."""
        request = mock_request_with_service("pairings_service", mock_service)

        result = await get_pairings_service(request)

        assert result is mock_service

    async def test_raises_503_when_service_not_initialized(
        self,
        mock_request_with_service: MagicMock,
    ) -> None:
        """Should raise 503 when pairings service is None."""
        request = mock_request_with_service("pairings_service", None)

        with pytest.raises(HTTPException) as exc_info:
            await get_pairings_service(request)

        assert exc_info.value.status_code == 503
        assert "Pairings service not available" in exc_info.value.detail
