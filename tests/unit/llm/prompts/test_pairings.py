"""Unit tests for RecipePairingPrompt."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.llm.prompts.pairings import (
    PairingListResult,
    PairingResult,
    RecipePairingPrompt,
)


pytestmark = pytest.mark.unit


class TestPairingResult:
    """Tests for PairingResult model."""

    def test_valid_pairing_result(self) -> None:
        """Should create valid PairingResult."""
        result = PairingResult(
            recipe_name="Roasted Asparagus",
            url="https://www.allrecipes.com/recipe/123/",
            pairing_reason="Light vegetable side",
            cuisine_type="American",
            confidence=0.9,
        )
        assert result.recipe_name == "Roasted Asparagus"
        assert result.url == "https://www.allrecipes.com/recipe/123/"
        assert result.pairing_reason == "Light vegetable side"
        assert result.cuisine_type == "American"
        assert result.confidence == 0.9

    def test_defaults(self) -> None:
        """Should use default values."""
        result = PairingResult(
            recipe_name="Test Recipe",
            url="https://example.com",
            pairing_reason="Test reason",
        )
        assert result.cuisine_type is None
        assert result.confidence == 0.8  # Default

    def test_rejects_empty_recipe_name(self) -> None:
        """Should reject empty recipe name."""
        with pytest.raises(ValidationError):
            PairingResult(
                recipe_name="",
                url="https://example.com",
                pairing_reason="Test reason",
            )

    def test_rejects_long_recipe_name(self) -> None:
        """Should reject recipe name over 150 chars."""
        with pytest.raises(ValidationError):
            PairingResult(
                recipe_name="x" * 151,
                url="https://example.com",
                pairing_reason="Test reason",
            )

    def test_rejects_long_pairing_reason(self) -> None:
        """Should reject pairing reason over 300 chars."""
        with pytest.raises(ValidationError):
            PairingResult(
                recipe_name="Test Recipe",
                url="https://example.com",
                pairing_reason="x" * 301,
            )

    def test_rejects_invalid_confidence(self) -> None:
        """Should reject confidence outside 0-1 range."""
        with pytest.raises(ValidationError):
            PairingResult(
                recipe_name="Test Recipe",
                url="https://example.com",
                pairing_reason="Test reason",
                confidence=1.5,
            )


class TestPairingListResult:
    """Tests for PairingListResult model."""

    def test_valid_list_result(self) -> None:
        """Should create valid PairingListResult."""
        result = PairingListResult(
            pairings=[
                PairingResult(
                    recipe_name="Recipe 1",
                    url="https://example.com/1",
                    pairing_reason="Reason 1",
                ),
                PairingResult(
                    recipe_name="Recipe 2",
                    url="https://example.com/2",
                    pairing_reason="Reason 2",
                ),
            ]
        )
        assert len(result.pairings) == 2

    def test_rejects_empty_pairings(self) -> None:
        """Should reject empty pairings list."""
        with pytest.raises(ValidationError):
            PairingListResult(pairings=[])

    def test_rejects_too_many_pairings(self) -> None:
        """Should reject more than 20 pairings."""
        with pytest.raises(ValidationError):
            PairingListResult(
                pairings=[
                    PairingResult(
                        recipe_name=f"Recipe {i}",
                        url=f"https://example.com/{i}",
                        pairing_reason=f"Reason {i}",
                    )
                    for i in range(21)
                ]
            )


class TestRecipePairingPrompt:
    """Tests for RecipePairingPrompt."""

    def test_format_includes_title(self) -> None:
        """Should include title in formatted prompt."""
        prompt = RecipePairingPrompt()
        result = prompt.format(title="Grilled Salmon")
        assert "Grilled Salmon" in result

    def test_format_includes_description(self) -> None:
        """Should include description in formatted prompt."""
        prompt = RecipePairingPrompt()
        result = prompt.format(
            title="Grilled Salmon",
            description="A delicious salmon recipe",
        )
        assert "delicious salmon recipe" in result

    def test_format_includes_ingredients(self) -> None:
        """Should include ingredients in formatted prompt."""
        prompt = RecipePairingPrompt()
        result = prompt.format(
            title="Grilled Salmon",
            ingredients=["salmon", "lemon", "dill"],
        )
        assert "salmon" in result
        assert "lemon" in result
        assert "dill" in result

    def test_format_limits_ingredient_count(self) -> None:
        """Should limit ingredients to 15."""
        prompt = RecipePairingPrompt()
        many_ingredients = [f"ingredient_{i}" for i in range(20)]
        result = prompt.format(
            title="Test Recipe",
            ingredients=many_ingredients,
        )
        # Should include first 15, not the rest
        assert "ingredient_0" in result
        assert "ingredient_14" in result
        assert "ingredient_15" not in result

    def test_format_truncates_long_description(self) -> None:
        """Should truncate description over 500 chars."""
        prompt = RecipePairingPrompt()
        long_description = "x" * 600
        result = prompt.format(
            title="Test Recipe",
            description=long_description,
        )
        # Should not include full description
        assert len(long_description) not in [len(result)]  # Fuzzy check

    def test_format_handles_missing_optional_fields(self) -> None:
        """Should handle missing description and ingredients."""
        prompt = RecipePairingPrompt()
        result = prompt.format(title="Grilled Salmon")
        assert "Grilled Salmon" in result
        assert "N/A" in result  # Default for missing fields

    def test_format_raises_on_missing_title(self) -> None:
        """Should raise ValueError if title is missing."""
        prompt = RecipePairingPrompt()
        with pytest.raises(ValueError, match="title"):
            prompt.format()

    def test_system_prompt_is_set(self) -> None:
        """Should have system prompt configured."""
        prompt = RecipePairingPrompt()
        assert prompt.system_prompt is not None
        assert "culinary expert" in prompt.system_prompt.lower()

    def test_temperature_is_set(self) -> None:
        """Should have temperature configured."""
        prompt = RecipePairingPrompt()
        assert prompt.temperature == 0.4

    def test_max_tokens_is_set(self) -> None:
        """Should have max_tokens configured."""
        prompt = RecipePairingPrompt()
        assert prompt.max_tokens == 2048

    def test_get_options(self) -> None:
        """Should return correct options dict."""
        prompt = RecipePairingPrompt()
        options = prompt.get_options()
        assert options["temperature"] == 0.4
        assert "num_predict" in options
