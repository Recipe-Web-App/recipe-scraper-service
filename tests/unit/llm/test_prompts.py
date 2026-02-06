"""Unit tests for BasePrompt class."""

from __future__ import annotations

from typing import Any, ClassVar

import pytest
from pydantic import BaseModel

from app.llm.prompts.base import BasePrompt


pytestmark = pytest.mark.unit


class SampleOutput(BaseModel):
    """Sample output schema for testing."""

    title: str
    count: int


class SimplePrompt(BasePrompt[SampleOutput]):
    """Simple prompt for testing."""

    output_schema: ClassVar[type[SampleOutput]] = SampleOutput
    system_prompt: ClassVar[str | None] = "You are a helpful assistant."
    temperature: ClassVar[float] = 0.2

    def format(self, text: str) -> str:
        return f"Process this: {text}"


class MinimalPrompt(BasePrompt[SampleOutput]):
    """Minimal prompt with defaults."""

    output_schema: ClassVar[type[SampleOutput]] = SampleOutput

    def format(self, **kwargs: Any) -> str:
        return "minimal prompt"


class TestBasePromptProperties:
    """Tests for BasePrompt properties."""

    def test_name_returns_class_name(self) -> None:
        """Should return the class name as prompt identifier."""
        prompt = SimplePrompt()

        assert prompt.name == "SimplePrompt"

    def test_output_schema_accessible(self) -> None:
        """Should expose the output schema class."""
        prompt = SimplePrompt()

        assert prompt.output_schema is SampleOutput

    def test_system_prompt_accessible(self) -> None:
        """Should expose the system prompt."""
        prompt = SimplePrompt()

        assert prompt.system_prompt == "You are a helpful assistant."

    def test_system_prompt_default_none(self) -> None:
        """Should default to None if not specified."""
        prompt = MinimalPrompt()

        assert prompt.system_prompt is None

    def test_temperature_accessible(self) -> None:
        """Should expose the temperature setting."""
        prompt = SimplePrompt()

        assert prompt.temperature == 0.2

    def test_temperature_default(self) -> None:
        """Should default to 0.1 if not specified."""
        prompt = MinimalPrompt()

        assert prompt.temperature == 0.1


class TestBasePromptFormat:
    """Tests for format method."""

    def test_format_with_kwargs(self) -> None:
        """Should format prompt with provided kwargs."""
        prompt = SimplePrompt()

        result = prompt.format(text="hello world")

        assert result == "Process this: hello world"

    def test_format_is_abstract(self) -> None:
        """Should not be able to instantiate without implementing format."""

        class IncompletePrompt(BasePrompt[SampleOutput]):
            output_schema = SampleOutput

        with pytest.raises(TypeError, match="abstract method"):
            IncompletePrompt()  # type: ignore[abstract]


class TestBasePromptOptions:
    """Tests for get_options method."""

    def test_get_options_includes_temperature(self) -> None:
        """Should include temperature in options."""
        prompt = SimplePrompt()

        options = prompt.get_options()

        assert options["temperature"] == 0.2

    def test_get_options_excludes_none_max_tokens(self) -> None:
        """Should not include num_predict if max_tokens is None."""
        prompt = MinimalPrompt()

        options = prompt.get_options()

        assert "num_predict" not in options

    def test_get_options_includes_max_tokens_when_set(self) -> None:
        """Should include num_predict if max_tokens is set."""

        class LimitedPrompt(BasePrompt[SampleOutput]):
            output_schema: ClassVar[type[SampleOutput]] = SampleOutput
            max_tokens: ClassVar[int | None] = 500

            def format(self, **kwargs: Any) -> str:
                return "limited"

        prompt = LimitedPrompt()
        options = prompt.get_options()

        assert options["num_predict"] == 500
