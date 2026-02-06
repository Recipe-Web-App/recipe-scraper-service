"""Unit tests for ingredient substitutions endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.ingredients import get_ingredient_substitutions
from app.schemas.enums import IngredientUnit
from app.schemas.ingredient import Ingredient
from app.schemas.recommendations import (
    ConversionRatio,
    IngredientSubstitution,
    RecommendedSubstitutionsResponse,
)
from app.services.substitution.exceptions import LLMGenerationError


pytestmark = pytest.mark.unit


class TestGetIngredientSubstitutions:
    """Tests for get_ingredient_substitutions endpoint."""

    @pytest.fixture
    def mock_user(self) -> MagicMock:
        """Create a mock authenticated user."""
        user = MagicMock()
        user.id = "user-123"
        return user

    @pytest.fixture
    def mock_substitution_service(self) -> MagicMock:
        """Create mock substitution service."""
        return MagicMock()

    @pytest.fixture
    def sample_response(self) -> RecommendedSubstitutionsResponse:
        """Create sample response for testing."""
        return RecommendedSubstitutionsResponse(
            ingredient=Ingredient(
                ingredient_id=None,
                name="butter",
                quantity=None,
            ),
            recommended_substitutions=[
                IngredientSubstitution(
                    ingredient="coconut oil",
                    quantity=None,
                    conversion_ratio=ConversionRatio(
                        ratio=1.0,
                        measurement=IngredientUnit.CUP,
                    ),
                ),
                IngredientSubstitution(
                    ingredient="olive oil",
                    quantity=None,
                    conversion_ratio=ConversionRatio(
                        ratio=0.75,
                        measurement=IngredientUnit.CUP,
                    ),
                ),
            ],
            limit=50,
            offset=0,
            count=2,
        )

    async def test_returns_substitutions_with_default_pagination(
        self,
        mock_user: MagicMock,
        mock_substitution_service: MagicMock,
        sample_response: RecommendedSubstitutionsResponse,
    ) -> None:
        """Should return substitutions with default pagination."""
        mock_substitution_service.get_substitutions = AsyncMock(
            return_value=sample_response
        )

        result = await get_ingredient_substitutions(
            ingredient_id="butter",
            user=mock_user,
            substitution_service=mock_substitution_service,
        )

        assert result.ingredient.name == "butter"
        assert len(result.recommended_substitutions) == 2
        assert result.limit == 50
        assert result.offset == 0

    async def test_returns_substitutions_with_custom_pagination(
        self,
        mock_user: MagicMock,
        mock_substitution_service: MagicMock,
        sample_response: RecommendedSubstitutionsResponse,
    ) -> None:
        """Should accept custom pagination parameters."""
        mock_substitution_service.get_substitutions = AsyncMock(
            return_value=sample_response
        )

        await get_ingredient_substitutions(
            ingredient_id="butter",
            user=mock_user,
            substitution_service=mock_substitution_service,
            limit=10,
            offset=5,
        )

        mock_substitution_service.get_substitutions.assert_called_once()
        call_kwargs = mock_substitution_service.get_substitutions.call_args[1]
        assert call_kwargs["limit"] == 10
        assert call_kwargs["offset"] == 5

    async def test_passes_quantity_to_service_when_provided(
        self,
        mock_user: MagicMock,
        mock_substitution_service: MagicMock,
        sample_response: RecommendedSubstitutionsResponse,
    ) -> None:
        """Should pass quantity to service when provided."""
        mock_substitution_service.get_substitutions = AsyncMock(
            return_value=sample_response
        )

        await get_ingredient_substitutions(
            ingredient_id="butter",
            user=mock_user,
            substitution_service=mock_substitution_service,
            amount=1.0,
            measurement=IngredientUnit.CUP,
        )

        call_kwargs = mock_substitution_service.get_substitutions.call_args[1]
        assert call_kwargs["quantity"] is not None
        assert call_kwargs["quantity"].amount == 1.0
        assert call_kwargs["quantity"].measurement == IngredientUnit.CUP

    async def test_raises_400_when_only_amount_provided(
        self,
        mock_user: MagicMock,
        mock_substitution_service: MagicMock,
    ) -> None:
        """Should raise 400 when only amount is provided."""
        with pytest.raises(HTTPException) as exc_info:
            await get_ingredient_substitutions(
                ingredient_id="butter",
                user=mock_user,
                substitution_service=mock_substitution_service,
                amount=1.0,
                measurement=None,
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "INVALID_QUANTITY_PARAMS"

    async def test_raises_400_when_only_measurement_provided(
        self,
        mock_user: MagicMock,
        mock_substitution_service: MagicMock,
    ) -> None:
        """Should raise 400 when only measurement is provided."""
        with pytest.raises(HTTPException) as exc_info:
            await get_ingredient_substitutions(
                ingredient_id="butter",
                user=mock_user,
                substitution_service=mock_substitution_service,
                amount=None,
                measurement=IngredientUnit.CUP,
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "INVALID_QUANTITY_PARAMS"

    async def test_raises_404_when_ingredient_not_found(
        self,
        mock_user: MagicMock,
        mock_substitution_service: MagicMock,
    ) -> None:
        """Should raise 404 when service returns None."""
        mock_substitution_service.get_substitutions = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_ingredient_substitutions(
                ingredient_id="unknown",
                user=mock_user,
                substitution_service=mock_substitution_service,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error"] == "INGREDIENT_NOT_FOUND"

    async def test_raises_503_when_llm_unavailable(
        self,
        mock_user: MagicMock,
        mock_substitution_service: MagicMock,
    ) -> None:
        """Should raise 503 when LLM generation fails."""
        mock_substitution_service.get_substitutions = AsyncMock(
            side_effect=LLMGenerationError(
                message="LLM unavailable",
                ingredient="butter",
            )
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_ingredient_substitutions(
                ingredient_id="butter",
                user=mock_user,
                substitution_service=mock_substitution_service,
            )

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["error"] == "LLM_UNAVAILABLE"

    async def test_returns_empty_list_when_count_only(
        self,
        mock_user: MagicMock,
        mock_substitution_service: MagicMock,
        sample_response: RecommendedSubstitutionsResponse,
    ) -> None:
        """Should return empty substitutions list when countOnly=true."""
        mock_substitution_service.get_substitutions = AsyncMock(
            return_value=sample_response
        )

        result = await get_ingredient_substitutions(
            ingredient_id="butter",
            user=mock_user,
            substitution_service=mock_substitution_service,
            count_only=True,
        )

        # Endpoint clears the list when count_only
        assert result.recommended_substitutions == []
        assert result.count == 2  # Count should still be present

    async def test_handles_ingredient_id_with_spaces(
        self,
        mock_user: MagicMock,
        mock_substitution_service: MagicMock,
        sample_response: RecommendedSubstitutionsResponse,
    ) -> None:
        """Should handle ingredient IDs with spaces."""
        mock_substitution_service.get_substitutions = AsyncMock(
            return_value=sample_response
        )

        await get_ingredient_substitutions(
            ingredient_id="all-purpose flour",
            user=mock_user,
            substitution_service=mock_substitution_service,
        )

        call_kwargs = mock_substitution_service.get_substitutions.call_args[1]
        assert call_kwargs["ingredient_id"] == "all-purpose flour"

    async def test_no_quantity_passed_when_not_provided(
        self,
        mock_user: MagicMock,
        mock_substitution_service: MagicMock,
        sample_response: RecommendedSubstitutionsResponse,
    ) -> None:
        """Should pass None for quantity when not provided."""
        mock_substitution_service.get_substitutions = AsyncMock(
            return_value=sample_response
        )

        await get_ingredient_substitutions(
            ingredient_id="butter",
            user=mock_user,
            substitution_service=mock_substitution_service,
        )

        call_kwargs = mock_substitution_service.get_substitutions.call_args[1]
        assert call_kwargs["quantity"] is None
