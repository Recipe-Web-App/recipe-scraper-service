"""Unit tests for AllergenRepository."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database.repositories.allergen import AllergenData, AllergenRepository


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_pool() -> MagicMock:
    """Create mock asyncpg connection pool."""
    pool = MagicMock()
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return pool


@pytest.fixture
def repository(mock_pool: MagicMock) -> AllergenRepository:
    """Create AllergenRepository with mocked pool."""
    return AllergenRepository(pool=mock_pool)


@pytest.fixture
def sample_row() -> dict[str, object]:
    """Create sample database row."""
    return {
        "ingredient_id": 1,
        "ingredient_name": "flour",
        "usda_food_description": "Wheat flour, white, all-purpose",
        "data_source": "USDA",
        "profile_confidence": Decimal("1.00"),
        "allergen_type": "GLUTEN",
        "presence_type": "CONTAINS",
        "confidence_score": Decimal("0.99"),
        "source_notes": "Contains wheat gluten",
    }


class TestAllergenDataModel:
    """Tests for AllergenData DTO."""

    def test_allergen_data_creation(self, sample_row: dict[str, object]) -> None:
        """Should create AllergenData with all fields."""
        data = AllergenData(
            ingredient_id=1,
            ingredient_name="flour",
            usda_food_description="Wheat flour, white, all-purpose",
            allergen_type="GLUTEN",
            presence_type="CONTAINS",
            confidence_score=Decimal("0.99"),
            source_notes="Contains wheat gluten",
            data_source="USDA",
            profile_confidence=Decimal("1.00"),
        )
        assert data.ingredient_id == 1
        assert data.ingredient_name == "flour"
        assert data.allergen_type == "GLUTEN"

    def test_allergen_data_defaults(self) -> None:
        """Should handle None values for optional fields."""
        data = AllergenData(
            ingredient_id=1,
            ingredient_name="test",
            usda_food_description=None,
            allergen_type="MILK",
            presence_type="CONTAINS",
            confidence_score=Decimal("1.0"),
            source_notes=None,
            data_source="USDA",
            profile_confidence=Decimal("1.0"),
        )
        assert data.usda_food_description is None
        assert data.source_notes is None


class TestGetByIngredientName:
    """Tests for get_by_ingredient_name method."""

    async def test_returns_empty_list_when_not_found(
        self,
        repository: AllergenRepository,
        mock_pool: MagicMock,
    ) -> None:
        """Should return empty list when ingredient not found."""
        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.fetch.return_value = []

        result = await repository.get_by_ingredient_name("nonexistent")

        assert result == []

    async def test_returns_allergen_list(
        self,
        repository: AllergenRepository,
        mock_pool: MagicMock,
        sample_row: dict[str, object],
    ) -> None:
        """Should return list of AllergenData for found ingredient."""
        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.fetch.return_value = [sample_row]

        result = await repository.get_by_ingredient_name("flour")

        assert len(result) == 1
        assert result[0].ingredient_name == "flour"
        assert result[0].allergen_type == "GLUTEN"

    async def test_filters_out_null_allergen_types(
        self,
        repository: AllergenRepository,
        mock_pool: MagicMock,
        sample_row: dict[str, object],
    ) -> None:
        """Should filter out rows with null allergen_type."""
        null_row = dict(sample_row)
        null_row["allergen_type"] = None

        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.fetch.return_value = [sample_row, null_row]

        result = await repository.get_by_ingredient_name("flour")

        assert len(result) == 1

    async def test_multiple_allergens(
        self,
        repository: AllergenRepository,
        mock_pool: MagicMock,
        sample_row: dict[str, object],
    ) -> None:
        """Should return multiple allergens for same ingredient."""
        wheat_row = dict(sample_row)
        wheat_row["allergen_type"] = "WHEAT"

        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.fetch.return_value = [sample_row, wheat_row]

        result = await repository.get_by_ingredient_name("flour")

        assert len(result) == 2
        allergen_types = {r.allergen_type for r in result}
        assert allergen_types == {"GLUTEN", "WHEAT"}


class TestGetByIngredientNames:
    """Tests for get_by_ingredient_names method."""

    async def test_empty_list_input(
        self,
        repository: AllergenRepository,
    ) -> None:
        """Should return empty dict for empty input."""
        result = await repository.get_by_ingredient_names([])

        assert result == {}

    async def test_batch_lookup(
        self,
        repository: AllergenRepository,
        mock_pool: MagicMock,
        sample_row: dict[str, object],
    ) -> None:
        """Should return dict mapping names to allergen data."""
        butter_row = dict(sample_row)
        butter_row["ingredient_name"] = "butter"
        butter_row["allergen_type"] = "MILK"

        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.fetch.return_value = [sample_row, butter_row]

        result = await repository.get_by_ingredient_names(["flour", "butter"])

        assert "flour" in result
        assert "butter" in result
        assert result["flour"][0].allergen_type == "GLUTEN"
        assert result["butter"][0].allergen_type == "MILK"

    async def test_partial_matches(
        self,
        repository: AllergenRepository,
        mock_pool: MagicMock,
        sample_row: dict[str, object],
    ) -> None:
        """Should only return found ingredients."""
        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.fetch.return_value = [sample_row]

        result = await repository.get_by_ingredient_names(["flour", "missing"])

        assert "flour" in result
        assert "missing" not in result


class TestGetByIngredientNameFuzzy:
    """Tests for get_by_ingredient_name_fuzzy method."""

    async def test_returns_empty_when_not_found(
        self,
        repository: AllergenRepository,
        mock_pool: MagicMock,
    ) -> None:
        """Should return empty list when no fuzzy match found."""
        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.fetchrow.return_value = None
        conn.fetch.return_value = []

        result = await repository.get_by_ingredient_name_fuzzy("nonexistent")

        assert result == []

    async def test_returns_fuzzy_match_results(
        self,
        repository: AllergenRepository,
        mock_pool: MagicMock,
        sample_row: dict[str, object],
    ) -> None:
        """Should return allergen data for fuzzy matched ingredient."""
        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.fetchrow.return_value = sample_row
        conn.fetch.return_value = [sample_row]

        result = await repository.get_by_ingredient_name_fuzzy("flor")  # Misspelled

        assert len(result) == 1
        assert result[0].allergen_type == "GLUTEN"

    async def test_logs_fuzzy_match_when_different_name(
        self,
        repository: AllergenRepository,
        mock_pool: MagicMock,
        sample_row: dict[str, object],
    ) -> None:
        """Should log debug message when fuzzy match differs from query."""
        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.fetchrow.return_value = sample_row
        conn.fetch.return_value = [sample_row]

        result = await repository.get_by_ingredient_name_fuzzy("flor")  # Misspelled

        # Result should be returned
        assert len(result) == 1
        assert result[0].ingredient_name == "flour"

    async def test_handles_pg_trgm_not_available(
        self,
        repository: AllergenRepository,
        mock_pool: MagicMock,
    ) -> None:
        """Should return empty list when pg_trgm extension not available."""
        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.fetchrow.side_effect = Exception(
            "function similarity(text, text) does not exist"
        )

        result = await repository.get_by_ingredient_name_fuzzy("flour")

        assert result == []

    async def test_raises_on_other_errors(
        self,
        repository: AllergenRepository,
        mock_pool: MagicMock,
    ) -> None:
        """Should raise on non-pg_trgm errors."""
        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.fetchrow.side_effect = Exception("Connection error")

        with pytest.raises(Exception, match="Connection error"):
            await repository.get_by_ingredient_name_fuzzy("flour")


class TestPoolProperty:
    """Tests for pool property."""

    async def test_pool_returns_injected_pool(
        self,
        repository: AllergenRepository,
        mock_pool: MagicMock,
    ) -> None:
        """Should return injected pool."""
        assert repository.pool is mock_pool

    async def test_pool_gets_global_pool_when_none(self) -> None:
        """Should get global pool when none injected."""
        from unittest.mock import patch

        repository = AllergenRepository(pool=None)
        mock_global_pool = MagicMock()

        with patch(
            "app.database.repositories.allergen.get_database_pool",
            return_value=mock_global_pool,
        ):
            result = repository.pool

        assert result is mock_global_pool


class TestBatchLookupEdgeCases:
    """Tests for batch lookup edge cases."""

    async def test_filters_null_allergen_types_in_batch(
        self,
        repository: AllergenRepository,
        mock_pool: MagicMock,
        sample_row: dict[str, object],
    ) -> None:
        """Should filter null allergen types in batch lookup."""
        null_row = dict(sample_row)
        null_row["allergen_type"] = None

        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.fetch.return_value = [sample_row, null_row]

        result = await repository.get_by_ingredient_names(["flour"])

        # Should only have one allergen (null filtered out)
        assert len(result.get("flour", [])) == 1

    async def test_groups_multiple_allergens_per_ingredient(
        self,
        repository: AllergenRepository,
        mock_pool: MagicMock,
        sample_row: dict[str, object],
    ) -> None:
        """Should group multiple allergens under same ingredient name."""
        wheat_row = dict(sample_row)
        wheat_row["allergen_type"] = "WHEAT"

        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.fetch.return_value = [sample_row, wheat_row]

        result = await repository.get_by_ingredient_names(["flour"])

        assert len(result.get("flour", [])) == 2
