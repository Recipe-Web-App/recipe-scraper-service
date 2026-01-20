"""Unit tests for IngredientParser class."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.llm.exceptions import (
    LLMTimeoutError,
    LLMUnavailableError,
    LLMValidationError,
)
from app.llm.prompts import IngredientUnit, ParsedIngredient, ParsedIngredientList
from app.parsing.exceptions import (
    IngredientParsingError,
    IngredientParsingTimeoutError,
    IngredientParsingValidationError,
)
from app.parsing.ingredient import IngredientParser


if TYPE_CHECKING:
    from app.llm.client.protocol import LLMClientProtocol


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Create a mock LLM client."""
    client = MagicMock(spec=["generate_structured"])
    client.generate_structured = AsyncMock()
    return client


@pytest.fixture
def parser(mock_llm_client: LLMClientProtocol) -> IngredientParser:
    """Create an IngredientParser with mock client."""
    return IngredientParser(mock_llm_client)


class TestIngredientParserParseBatch:
    """Tests for parse_batch method."""

    async def test_returns_empty_list_for_empty_input(
        self,
        parser: IngredientParser,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should return empty list when given empty input."""
        result = await parser.parse_batch([])

        assert result == []
        mock_llm_client.generate_structured.assert_not_called()

    async def test_calls_llm_with_formatted_prompt(
        self,
        parser: IngredientParser,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should call LLM with properly formatted prompt."""
        mock_llm_client.generate_structured.return_value = ParsedIngredientList(
            ingredients=[
                ParsedIngredient(
                    name="flour",
                    quantity=2.0,
                    unit=IngredientUnit.CUP,
                ),
            ]
        )

        await parser.parse_batch(["2 cups flour"])

        mock_llm_client.generate_structured.assert_called_once()
        call_kwargs = mock_llm_client.generate_structured.call_args.kwargs
        assert "2 cups flour" in call_kwargs["prompt"]
        assert call_kwargs["schema"] is ParsedIngredientList

    async def test_returns_parsed_ingredients(
        self,
        parser: IngredientParser,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should return list of ParsedIngredient objects."""
        expected = [
            ParsedIngredient(
                name="all-purpose flour",
                quantity=2.0,
                unit=IngredientUnit.CUP,
                notes="sifted",
            ),
            ParsedIngredient(
                name="salt",
                quantity=0.5,
                unit=IngredientUnit.TSP,
            ),
        ]
        mock_llm_client.generate_structured.return_value = ParsedIngredientList(
            ingredients=expected
        )

        result = await parser.parse_batch(
            [
                "2 cups all-purpose flour, sifted",
                "1/2 tsp salt",
            ]
        )

        assert len(result) == 2
        assert result[0].name == "all-purpose flour"
        assert result[0].quantity == 2.0
        assert result[0].unit == IngredientUnit.CUP
        assert result[0].notes == "sifted"
        assert result[1].name == "salt"
        assert result[1].quantity == 0.5
        assert result[1].unit == IngredientUnit.TSP

    async def test_raises_validation_error_on_count_mismatch(
        self,
        parser: IngredientParser,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should raise error when output count doesn't match input."""
        # Return only 1 ingredient when 2 were provided
        mock_llm_client.generate_structured.return_value = ParsedIngredientList(
            ingredients=[
                ParsedIngredient(
                    name="flour",
                    quantity=2.0,
                    unit=IngredientUnit.CUP,
                ),
            ]
        )

        with pytest.raises(
            IngredientParsingValidationError,
            match="Expected 2 parsed ingredients, got 1",
        ):
            await parser.parse_batch(["2 cups flour", "1 tsp salt"])

    async def test_raises_timeout_error_on_llm_timeout(
        self,
        parser: IngredientParser,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should raise IngredientParsingTimeoutError on LLM timeout."""
        mock_llm_client.generate_structured.side_effect = LLMTimeoutError(
            "Request timed out"
        )

        with pytest.raises(IngredientParsingTimeoutError):
            await parser.parse_batch(["2 cups flour"])

    async def test_raises_validation_error_on_llm_validation_error(
        self,
        parser: IngredientParser,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should raise IngredientParsingValidationError on schema mismatch."""
        mock_llm_client.generate_structured.side_effect = LLMValidationError(
            "Invalid schema"
        )

        with pytest.raises(IngredientParsingValidationError):
            await parser.parse_batch(["2 cups flour"])

    async def test_raises_parsing_error_on_llm_unavailable(
        self,
        parser: IngredientParser,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should raise IngredientParsingError on LLM unavailable."""
        mock_llm_client.generate_structured.side_effect = LLMUnavailableError(
            "Service down"
        )

        with pytest.raises(IngredientParsingError, match="LLM service unavailable"):
            await parser.parse_batch(["2 cups flour"])

    async def test_raises_parsing_error_on_unexpected_exception(
        self,
        parser: IngredientParser,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should wrap unexpected exceptions in IngredientParsingError."""
        mock_llm_client.generate_structured.side_effect = RuntimeError("Unexpected")

        with pytest.raises(IngredientParsingError, match="Failed to parse"):
            await parser.parse_batch(["2 cups flour"])

    async def test_passes_skip_cache_option(
        self,
        parser: IngredientParser,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should pass skip_cache option to LLM client."""
        mock_llm_client.generate_structured.return_value = ParsedIngredientList(
            ingredients=[
                ParsedIngredient(
                    name="flour",
                    quantity=2.0,
                    unit=IngredientUnit.CUP,
                ),
            ]
        )

        await parser.parse_batch(["2 cups flour"], skip_cache=True)

        call_kwargs = mock_llm_client.generate_structured.call_args.kwargs
        assert call_kwargs["skip_cache"] is True


class TestIngredientParserParseSingle:
    """Tests for parse_single method."""

    async def test_returns_single_parsed_ingredient(
        self,
        parser: IngredientParser,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should return a single ParsedIngredient."""
        expected = ParsedIngredient(
            name="garlic",
            quantity=3.0,
            unit=IngredientUnit.CLOVE,
            notes="minced",
        )
        mock_llm_client.generate_structured.return_value = ParsedIngredientList(
            ingredients=[expected]
        )

        result = await parser.parse_single("3 cloves garlic, minced")

        assert result.name == "garlic"
        assert result.quantity == 3.0
        assert result.unit == IngredientUnit.CLOVE
        assert result.notes == "minced"

    async def test_passes_skip_cache_option(
        self,
        parser: IngredientParser,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should pass skip_cache option when parsing single ingredient."""
        mock_llm_client.generate_structured.return_value = ParsedIngredientList(
            ingredients=[
                ParsedIngredient(
                    name="salt",
                    quantity=1.0,
                    unit=IngredientUnit.PINCH,
                ),
            ]
        )

        await parser.parse_single("a pinch of salt", skip_cache=True)

        call_kwargs = mock_llm_client.generate_structured.call_args.kwargs
        assert call_kwargs["skip_cache"] is True


class TestIngredientParsingPrompt:
    """Tests for the IngredientParsingPrompt class."""

    async def test_prompt_format_includes_all_ingredients(
        self,
        parser: IngredientParser,
    ) -> None:
        """Should include all ingredients in formatted prompt."""
        prompt = parser._prompt.format(
            ingredients=["2 cups flour", "1 tsp salt", "3 eggs"]
        )

        assert "2 cups flour" in prompt
        assert "1 tsp salt" in prompt
        assert "3 eggs" in prompt

    async def test_prompt_format_raises_on_missing_ingredients(
        self,
        parser: IngredientParser,
    ) -> None:
        """Should raise ValueError if ingredients arg is missing."""
        with pytest.raises(ValueError, match="Missing required 'ingredients'"):
            parser._prompt.format()

    async def test_prompt_has_system_prompt(
        self,
        parser: IngredientParser,
    ) -> None:
        """Should have a system prompt defined."""
        assert parser._prompt.system_prompt is not None
        assert "ingredient parser" in parser._prompt.system_prompt.lower()

    async def test_prompt_temperature_is_deterministic(
        self,
        parser: IngredientParser,
    ) -> None:
        """Should use temperature 0 for deterministic parsing."""
        assert parser._prompt.temperature == 0.0
