"""Unit tests for IngredientSubstitutionPrompt."""

from __future__ import annotations

import pytest

from app.llm.prompts.substitution import (
    IngredientSubstitutionPrompt,
    SubstitutionListResult,
    SubstitutionResult,
)


pytestmark = pytest.mark.unit


class TestIngredientSubstitutionPrompt:
    """Tests for IngredientSubstitutionPrompt class."""

    def test_output_schema_is_substitution_list_result(self) -> None:
        """Should have SubstitutionListResult as output schema."""
        prompt = IngredientSubstitutionPrompt()
        assert prompt.output_schema is SubstitutionListResult

    def test_system_prompt_is_set(self) -> None:
        """Should have a system prompt defined."""
        prompt = IngredientSubstitutionPrompt()
        assert prompt.system_prompt is not None
        assert "culinary expert" in prompt.system_prompt.lower()

    def test_temperature_is_set_for_creativity(self) -> None:
        """Should have temperature > 0 for some creativity."""
        prompt = IngredientSubstitutionPrompt()
        assert prompt.temperature == 0.3

    def test_max_tokens_is_set(self) -> None:
        """Should have max_tokens set."""
        prompt = IngredientSubstitutionPrompt()
        assert prompt.max_tokens == 2048

    def test_format_with_ingredient_name_only(self) -> None:
        """Should format prompt with just ingredient name."""
        prompt = IngredientSubstitutionPrompt()
        result = prompt.format(ingredient_name="butter")

        assert "butter" in result
        assert "substitution" in result.lower()

    def test_format_with_food_group(self) -> None:
        """Should include food group in prompt when provided."""
        prompt = IngredientSubstitutionPrompt()
        result = prompt.format(ingredient_name="butter", food_group="DAIRY")

        assert "butter" in result
        assert "DAIRY" in result

    def test_format_with_quantity(self) -> None:
        """Should include quantity context when provided."""
        prompt = IngredientSubstitutionPrompt()
        result = prompt.format(
            ingredient_name="butter",
            quantity={"amount": 1.0, "measurement": "CUP"},
        )

        assert "butter" in result
        assert "1.0" in result
        assert "CUP" in result

    def test_format_with_all_context(self) -> None:
        """Should include all context when provided."""
        prompt = IngredientSubstitutionPrompt()
        result = prompt.format(
            ingredient_name="butter",
            food_group="DAIRY",
            quantity={"amount": 2.0, "measurement": "TBSP"},
        )

        assert "butter" in result
        assert "DAIRY" in result
        assert "2.0" in result
        assert "TBSP" in result

    def test_format_raises_on_missing_ingredient_name(self) -> None:
        """Should raise ValueError when ingredient_name is missing."""
        prompt = IngredientSubstitutionPrompt()

        with pytest.raises(ValueError, match="ingredient_name"):
            prompt.format(food_group="DAIRY")

    def test_get_options_returns_temperature(self) -> None:
        """Should return options dict with temperature."""
        prompt = IngredientSubstitutionPrompt()
        options = prompt.get_options()

        assert "temperature" in options
        assert options["temperature"] == 0.3

    def test_get_options_returns_num_predict(self) -> None:
        """Should return options dict with num_predict (max_tokens)."""
        prompt = IngredientSubstitutionPrompt()
        options = prompt.get_options()

        assert "num_predict" in options
        assert options["num_predict"] == 2048

    def test_name_property(self) -> None:
        """Should return class name as prompt name."""
        prompt = IngredientSubstitutionPrompt()
        assert prompt.name == "IngredientSubstitutionPrompt"


class TestSubstitutionResultSchema:
    """Tests for SubstitutionResult schema validation."""

    def test_valid_substitution_result(self) -> None:
        """Should accept valid substitution data."""
        result = SubstitutionResult(
            ingredient="coconut oil",
            ratio=1.0,
            measurement="CUP",
            notes="Best for baking",
            confidence=0.9,
        )

        assert result.ingredient == "coconut oil"
        assert result.ratio == 1.0
        assert result.measurement == "CUP"
        assert result.notes == "Best for baking"
        assert result.confidence == 0.9

    def test_default_confidence(self) -> None:
        """Should use default confidence when not provided."""
        result = SubstitutionResult(
            ingredient="olive oil",
            ratio=0.75,
            measurement="CUP",
        )

        assert result.confidence == 0.8

    def test_rejects_ratio_below_zero(self) -> None:
        """Should reject ratio <= 0."""
        with pytest.raises(ValueError, match="greater than 0"):
            SubstitutionResult(
                ingredient="test",
                ratio=0,
                measurement="CUP",
            )

    def test_rejects_ratio_above_ten(self) -> None:
        """Should reject ratio > 10."""
        with pytest.raises(ValueError, match="less than or equal to 10"):
            SubstitutionResult(
                ingredient="test",
                ratio=11,
                measurement="CUP",
            )

    def test_rejects_confidence_above_one(self) -> None:
        """Should reject confidence > 1."""
        with pytest.raises(ValueError, match="less than or equal to 1"):
            SubstitutionResult(
                ingredient="test",
                ratio=1.0,
                measurement="CUP",
                confidence=1.5,
            )

    def test_rejects_empty_ingredient(self) -> None:
        """Should reject empty ingredient name."""
        with pytest.raises(ValueError, match="at least 1 character"):
            SubstitutionResult(
                ingredient="",
                ratio=1.0,
                measurement="CUP",
            )


class TestSubstitutionListResultSchema:
    """Tests for SubstitutionListResult schema validation."""

    def test_valid_list_result(self) -> None:
        """Should accept valid substitution list."""
        result = SubstitutionListResult(
            substitutions=[
                SubstitutionResult(
                    ingredient="coconut oil",
                    ratio=1.0,
                    measurement="CUP",
                ),
            ]
        )

        assert len(result.substitutions) == 1

    def test_rejects_empty_list(self) -> None:
        """Should reject empty substitutions list."""
        with pytest.raises(ValueError, match="at least 1 item"):
            SubstitutionListResult(substitutions=[])

    def test_accepts_multiple_substitutions(self) -> None:
        """Should accept list with multiple substitutions."""
        result = SubstitutionListResult(
            substitutions=[
                SubstitutionResult(
                    ingredient="coconut oil",
                    ratio=1.0,
                    measurement="CUP",
                ),
                SubstitutionResult(
                    ingredient="olive oil",
                    ratio=0.75,
                    measurement="CUP",
                ),
                SubstitutionResult(
                    ingredient="applesauce",
                    ratio=0.5,
                    measurement="CUP",
                ),
            ]
        )

        assert len(result.substitutions) == 3
