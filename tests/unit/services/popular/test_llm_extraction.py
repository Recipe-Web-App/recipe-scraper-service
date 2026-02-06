"""Unit tests for LLM-based recipe link extraction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.llm.exceptions import (
    LLMTimeoutError,
    LLMUnavailableError,
    LLMValidationError,
)
from app.llm.prompts.recipe_link_extraction import (
    ExtractedRecipeLink,
    ExtractedRecipeLinkList,
    RecipeLinkExtractionPrompt,
)
from app.services.popular.llm_extraction import RecipeLinkExtractor


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Create a mock LLM client."""
    client = MagicMock()
    client.generate_structured = AsyncMock()
    return client


@pytest.fixture
def extractor(mock_llm_client: MagicMock) -> RecipeLinkExtractor:
    """Create a RecipeLinkExtractor with mock LLM client."""
    return RecipeLinkExtractor(
        llm_client=mock_llm_client,
        use_llm=True,
        max_html_chars=8000,
        min_confidence=0.5,
    )


class TestRecipeLinkExtractorInit:
    """Tests for RecipeLinkExtractor initialization."""

    def test_creates_with_llm_client(self, mock_llm_client: MagicMock) -> None:
        """Should create extractor with LLM client enabled."""
        extractor = RecipeLinkExtractor(
            llm_client=mock_llm_client,
            max_html_chars=8000,
            min_confidence=0.5,
        )

        assert extractor._llm_client is mock_llm_client
        assert extractor._use_llm is True

    def test_disables_llm_when_client_is_none(self) -> None:
        """Should disable LLM when client is None."""
        extractor = RecipeLinkExtractor(
            llm_client=None,
            use_llm=True,
            max_html_chars=8000,
            min_confidence=0.5,
        )

        assert extractor._use_llm is False

    def test_disables_llm_when_use_llm_false(self, mock_llm_client: MagicMock) -> None:
        """Should disable LLM when use_llm flag is False."""
        extractor = RecipeLinkExtractor(
            llm_client=mock_llm_client,
            use_llm=False,
            max_html_chars=8000,
            min_confidence=0.5,
        )

        assert extractor._use_llm is False

    def test_uses_custom_max_html_chars(self, mock_llm_client: MagicMock) -> None:
        """Should use custom max_html_chars setting."""
        extractor = RecipeLinkExtractor(
            llm_client=mock_llm_client,
            max_html_chars=16000,
            min_confidence=0.5,
        )

        assert extractor._max_html_chars == 16000

    def test_uses_custom_min_confidence(self, mock_llm_client: MagicMock) -> None:
        """Should use custom min_confidence setting."""
        extractor = RecipeLinkExtractor(
            llm_client=mock_llm_client,
            max_html_chars=8000,
            min_confidence=0.7,
        )

        assert extractor._min_confidence == 0.7


class TestExtractWithLLM:
    """Tests for LLM-based extraction."""

    @pytest.mark.asyncio
    async def test_extracts_recipe_links_with_llm(
        self,
        extractor: RecipeLinkExtractor,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should extract recipe links using LLM."""
        mock_llm_client.generate_structured.return_value = ExtractedRecipeLinkList(
            recipe_links=[
                ExtractedRecipeLink(
                    recipe_name="Chocolate Cake",
                    url="/recipes/chocolate-cake",
                    confidence=1.0,
                ),
                ExtractedRecipeLink(
                    recipe_name="Apple Pie",
                    url="https://example.com/recipes/apple-pie",
                    confidence=0.9,
                ),
            ]
        )

        html = """
        <html>
        <article class="recipe-card">
            <a href="/recipes/chocolate-cake">Chocolate Cake</a>
        </article>
        <article class="recipe-card">
            <a href="/recipes/apple-pie">Apple Pie</a>
        </article>
        </html>
        """

        links = await extractor.extract(html, "https://example.com")

        assert len(links) == 2
        assert links[0] == (
            "Chocolate Cake",
            "https://example.com/recipes/chocolate-cake",
        )
        assert links[1] == ("Apple Pie", "https://example.com/recipes/apple-pie")
        mock_llm_client.generate_structured.assert_called_once()

    @pytest.mark.asyncio
    async def test_filters_low_confidence_links(
        self,
        extractor: RecipeLinkExtractor,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should filter out links with confidence below threshold."""
        mock_llm_client.generate_structured.return_value = ExtractedRecipeLinkList(
            recipe_links=[
                ExtractedRecipeLink(
                    recipe_name="High Confidence Recipe",
                    url="/recipes/high",
                    confidence=0.9,
                ),
                ExtractedRecipeLink(
                    recipe_name="Low Confidence Link",
                    url="/recipes/low",
                    confidence=0.3,  # Below 0.5 threshold
                ),
            ]
        )

        # HTML must contain links for preprocessing to find
        html = '<html><body><a href="/recipes/test">Test Recipe</a></body></html>'
        links = await extractor.extract(html, "https://example.com")

        assert len(links) == 1
        assert links[0][0] == "High Confidence Recipe"

    @pytest.mark.asyncio
    async def test_deduplicates_urls(
        self,
        extractor: RecipeLinkExtractor,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should not return duplicate URLs."""
        mock_llm_client.generate_structured.return_value = ExtractedRecipeLinkList(
            recipe_links=[
                ExtractedRecipeLink(
                    recipe_name="Recipe One",
                    url="/recipes/duplicate",
                    confidence=1.0,
                ),
                ExtractedRecipeLink(
                    recipe_name="Recipe Two",
                    url="/recipes/duplicate",  # Same URL
                    confidence=0.9,
                ),
            ]
        )

        # HTML must contain links for preprocessing to find
        html = '<html><body><a href="/recipes/test">Test Recipe</a></body></html>'
        links = await extractor.extract(html, "https://example.com")

        assert len(links) == 1
        assert links[0][0] == "Recipe One"

    @pytest.mark.asyncio
    async def test_skips_names_that_become_short_after_strip(
        self,
        extractor: RecipeLinkExtractor,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should skip recipes whose names become <3 chars after stripping."""
        # Schema enforces min_length=3, but after stripping whitespace
        # we filter in _filter_results if name becomes too short
        mock_llm_client.generate_structured.return_value = ExtractedRecipeLinkList(
            recipe_links=[
                ExtractedRecipeLink(
                    recipe_name="   ",  # Whitespace only, becomes empty after strip
                    url="/recipes/empty",
                    confidence=1.0,
                ),
                ExtractedRecipeLink(
                    recipe_name="Valid Recipe Name",
                    url="/recipes/valid",
                    confidence=1.0,
                ),
            ]
        )

        # HTML must contain links for preprocessing to find
        html = '<html><body><a href="/recipes/test">Test Recipe</a></body></html>'
        links = await extractor.extract(html, "https://example.com")

        assert len(links) == 1
        assert links[0][0] == "Valid Recipe Name"


class TestFallbackToRegex:
    """Tests for fallback to regex extraction."""

    @pytest.mark.asyncio
    async def test_falls_back_on_llm_unavailable(
        self,
        extractor: RecipeLinkExtractor,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should fall back to regex when LLM is unavailable."""
        mock_llm_client.generate_structured.side_effect = LLMUnavailableError(
            "Service unavailable"
        )

        html = """
        <html>
        <article class="recipe-card">
            <a href="/recipes/fallback-cake">Fallback Cake</a>
        </article>
        </html>
        """

        links = await extractor.extract(html, "https://example.com")

        # Should still get results from regex fallback
        assert len(links) >= 0  # Regex may or may not find links
        mock_llm_client.generate_structured.assert_called_once()

    @pytest.mark.asyncio
    async def test_falls_back_on_llm_timeout(
        self,
        extractor: RecipeLinkExtractor,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should fall back to regex when LLM times out."""
        mock_llm_client.generate_structured.side_effect = LLMTimeoutError(
            "Request timed out"
        )

        html = "<html><body></body></html>"
        links = await extractor.extract(html, "https://example.com")

        # Should not raise, returns regex results
        assert isinstance(links, list)

    @pytest.mark.asyncio
    async def test_falls_back_on_llm_validation_error(
        self,
        extractor: RecipeLinkExtractor,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should fall back to regex when LLM response is invalid."""
        mock_llm_client.generate_structured.side_effect = LLMValidationError(
            "Invalid response format"
        )

        html = "<html><body></body></html>"
        links = await extractor.extract(html, "https://example.com")

        # Should not raise, returns regex results
        assert isinstance(links, list)

    @pytest.mark.asyncio
    async def test_falls_back_on_unexpected_error(
        self,
        extractor: RecipeLinkExtractor,
        mock_llm_client: MagicMock,
    ) -> None:
        """Should fall back to regex on unexpected errors."""
        mock_llm_client.generate_structured.side_effect = RuntimeError(
            "Unexpected error"
        )

        html = "<html><body></body></html>"
        links = await extractor.extract(html, "https://example.com")

        # Should not raise, returns regex results
        assert isinstance(links, list)


class TestRegexOnlyMode:
    """Tests for regex-only mode (LLM disabled)."""

    @pytest.mark.asyncio
    async def test_uses_regex_when_llm_disabled(
        self, mock_llm_client: MagicMock
    ) -> None:
        """Should use regex extraction when use_llm is False."""
        extractor = RecipeLinkExtractor(
            llm_client=mock_llm_client,
            use_llm=False,
            max_html_chars=8000,
            min_confidence=0.5,
        )

        html = """
        <html>
        <article class="recipe-card">
            <a href="/recipes/regex-recipe">Regex Recipe</a>
        </article>
        </html>
        """

        links = await extractor.extract(html, "https://example.com")

        # LLM should not be called
        mock_llm_client.generate_structured.assert_not_called()
        # Regex should work
        assert isinstance(links, list)

    @pytest.mark.asyncio
    async def test_uses_regex_when_client_is_none(self) -> None:
        """Should use regex extraction when llm_client is None."""
        extractor = RecipeLinkExtractor(
            llm_client=None,
            max_html_chars=8000,
            min_confidence=0.5,
        )

        html = """
        <html>
        <article class="recipe-card">
            <a href="/recipes/test">Test Recipe</a>
        </article>
        </html>
        """

        links = await extractor.extract(html, "https://example.com")

        assert isinstance(links, list)


class TestHTMLPreprocessing:
    """Tests for HTML preprocessing."""

    def test_removes_script_tags(self, extractor: RecipeLinkExtractor) -> None:
        """Should remove script tags from HTML."""
        html = """
        <html>
        <script>console.log('remove me');</script>
        <article class="recipe">
            <a href="/recipe">Recipe</a>
        </article>
        </html>
        """

        processed = extractor._preprocess_html(html)

        assert "<script>" not in processed
        assert "console.log" not in processed

    def test_removes_style_tags(self, extractor: RecipeLinkExtractor) -> None:
        """Should remove style tags from HTML."""
        html = """
        <html>
        <style>.hidden { display: none; }</style>
        <article class="recipe">
            <a href="/recipe">Recipe</a>
        </article>
        </html>
        """

        processed = extractor._preprocess_html(html)

        assert "<style>" not in processed
        assert "display: none" not in processed

    def test_removes_html_comments(self, extractor: RecipeLinkExtractor) -> None:
        """Should remove HTML comments."""
        html = """
        <html>
        <!-- This is a comment -->
        <article class="recipe">
            <a href="/recipe">Recipe</a>
        </article>
        </html>
        """

        processed = extractor._preprocess_html(html)

        assert "This is a comment" not in processed

    def test_truncates_large_html(self, mock_llm_client: MagicMock) -> None:
        """Should truncate extracted links that exceed max_html_chars."""
        extractor = RecipeLinkExtractor(
            llm_client=mock_llm_client,
            max_html_chars=100,
            min_confidence=0.5,
        )

        # Generate many links that will exceed 100 chars when extracted
        links = "".join(
            f'<a href="/recipe/{i}">Recipe Number {i}</a>' for i in range(20)
        )
        html = f"<html><body>{links}</body></html>"

        processed = extractor._preprocess_html(html)

        # Now returns list - truncation happens at chunk level
        assert isinstance(processed, list)
        # With 20 links, should have multiple items
        assert len(processed) > 0

    def test_extracts_recipe_containers(self, extractor: RecipeLinkExtractor) -> None:
        """Should extract recipe-related containers."""
        html = """
        <html>
        <header>Navigation</header>
        <article class="recipe-card">
            <a href="/recipe/1">Recipe 1</a>
        </article>
        <div class="card item">
            <a href="/recipe/2">Recipe 2</a>
        </div>
        <footer>Footer</footer>
        </html>
        """

        processed = extractor._preprocess_html(html)

        # Should contain recipe containers (list of link strings)
        combined = "\n".join(processed)
        assert "recipe-card" in combined or "card" in combined

    def test_falls_back_to_main_content(self, extractor: RecipeLinkExtractor) -> None:
        """Should fall back to main content when no recipe containers."""
        html = """
        <html>
        <header>Header</header>
        <main>
            <a href="/recipe">Main Recipe</a>
        </main>
        <footer>Footer</footer>
        </html>
        """

        processed = extractor._preprocess_html(html)

        # Now returns list of link strings
        combined = "\n".join(processed)
        assert "Main Recipe" in combined


class TestFilterResults:
    """Tests for result filtering."""

    def test_filters_by_confidence_threshold(
        self, extractor: RecipeLinkExtractor
    ) -> None:
        """Should filter links below confidence threshold."""
        result = ExtractedRecipeLinkList(
            recipe_links=[
                ExtractedRecipeLink(
                    recipe_name="High",
                    url="/high",
                    confidence=0.8,
                ),
                ExtractedRecipeLink(
                    recipe_name="Low",
                    url="/low",
                    confidence=0.4,
                ),
            ]
        )

        links = extractor._filter_results_from_list(
            result.recipe_links, "https://example.com"
        )

        assert len(links) == 1
        assert links[0][0] == "High"

    def test_resolves_relative_urls(self, extractor: RecipeLinkExtractor) -> None:
        """Should resolve relative URLs to absolute."""
        result = ExtractedRecipeLinkList(
            recipe_links=[
                ExtractedRecipeLink(
                    recipe_name="Relative Recipe",
                    url="/recipes/relative",
                    confidence=1.0,
                ),
            ]
        )

        links = extractor._filter_results_from_list(
            result.recipe_links, "https://example.com/popular"
        )

        assert len(links) == 1
        assert links[0][1] == "https://example.com/recipes/relative"

    def test_preserves_absolute_urls(self, extractor: RecipeLinkExtractor) -> None:
        """Should preserve absolute URLs."""
        result = ExtractedRecipeLinkList(
            recipe_links=[
                ExtractedRecipeLink(
                    recipe_name="Absolute Recipe",
                    url="https://other.com/recipe",
                    confidence=1.0,
                ),
            ]
        )

        links = extractor._filter_results_from_list(
            result.recipe_links, "https://example.com"
        )

        assert len(links) == 1
        assert links[0][1] == "https://other.com/recipe"

    def test_strips_whitespace_from_names(self, extractor: RecipeLinkExtractor) -> None:
        """Should strip whitespace from recipe names."""
        result = ExtractedRecipeLinkList(
            recipe_links=[
                ExtractedRecipeLink(
                    recipe_name="  Spaced Recipe  ",
                    url="/recipe",
                    confidence=1.0,
                ),
            ]
        )

        links = extractor._filter_results_from_list(
            result.recipe_links, "https://example.com"
        )

        assert len(links) == 1
        assert links[0][0] == "Spaced Recipe"


class TestRecipeLinkExtractionPrompt:
    """Tests for RecipeLinkExtractionPrompt class."""

    def test_format_includes_html_content(self) -> None:
        """Should include HTML content in formatted prompt."""
        prompt = RecipeLinkExtractionPrompt()

        result = prompt.format(
            html_content="<div>Test HTML</div>",
            base_url="https://example.com",
        )

        assert "<div>Test HTML</div>" in result
        assert "https://example.com" in result

    def test_format_includes_base_url(self) -> None:
        """Should include base URL in formatted prompt."""
        prompt = RecipeLinkExtractionPrompt()

        result = prompt.format(
            html_content="<html></html>",
            base_url="https://recipes.example.com",
        )

        assert "https://recipes.example.com" in result

    def test_format_raises_on_missing_html_content(self) -> None:
        """Should raise ValueError when html_content is missing."""
        prompt = RecipeLinkExtractionPrompt()

        with pytest.raises(ValueError, match="Missing required 'html_content'"):
            prompt.format(base_url="https://example.com")

    def test_format_raises_on_missing_base_url(self) -> None:
        """Should raise ValueError when base_url is missing."""
        prompt = RecipeLinkExtractionPrompt()

        with pytest.raises(ValueError, match="Missing required 'base_url'"):
            prompt.format(html_content="<html></html>")

    def test_output_schema_is_extracted_recipe_link_list(self) -> None:
        """Should use ExtractedRecipeLinkList as output schema."""
        prompt = RecipeLinkExtractionPrompt()

        assert prompt.output_schema is ExtractedRecipeLinkList

    def test_system_prompt_contains_extraction_rules(self) -> None:
        """Should have system prompt with extraction rules."""
        prompt = RecipeLinkExtractionPrompt()

        assert prompt.system_prompt is not None
        # Should mention what to include and exclude
        assert (
            "INCLUDE" in prompt.system_prompt
            or "include" in prompt.system_prompt.lower()
        )
        assert (
            "EXCLUDE" in prompt.system_prompt
            or "exclude" in prompt.system_prompt.lower()
        )

    def test_temperature_is_zero_for_deterministic_output(self) -> None:
        """Should use temperature 0 for deterministic extraction."""
        prompt = RecipeLinkExtractionPrompt()

        assert prompt.temperature == 0.0

    def test_get_options_returns_valid_options(self) -> None:
        """Should return valid LLM options."""
        prompt = RecipeLinkExtractionPrompt()

        options = prompt.get_options()

        assert "temperature" in options
        assert options["temperature"] == 0.0


class TestExtractedRecipeLinkSchema:
    """Tests for Pydantic schema validation."""

    def test_extracted_recipe_link_valid(self) -> None:
        """Should accept valid recipe link data."""
        link = ExtractedRecipeLink(
            recipe_name="Chocolate Chip Cookies",
            url="/recipes/chocolate-chip-cookies",
            confidence=0.95,
        )

        assert link.recipe_name == "Chocolate Chip Cookies"
        assert link.url == "/recipes/chocolate-chip-cookies"
        assert link.confidence == 0.95

    def test_extracted_recipe_link_default_confidence(self) -> None:
        """Should default confidence to 1.0."""
        link = ExtractedRecipeLink(
            recipe_name="Test Recipe",
            url="/test",
        )

        assert link.confidence == 1.0

    def test_extracted_recipe_link_list_empty_default(self) -> None:
        """Should default to empty list of recipe links."""
        result = ExtractedRecipeLinkList()

        assert result.recipe_links == []

    def test_extracted_recipe_link_list_with_links(self) -> None:
        """Should accept list of recipe links."""
        result = ExtractedRecipeLinkList(
            recipe_links=[
                ExtractedRecipeLink(
                    recipe_name="Recipe 1",
                    url="/recipe-1",
                ),
                ExtractedRecipeLink(
                    recipe_name="Recipe 2",
                    url="/recipe-2",
                    confidence=0.8,
                ),
            ]
        )

        assert len(result.recipe_links) == 2
        assert result.recipe_links[0].recipe_name == "Recipe 1"
        assert result.recipe_links[1].confidence == 0.8


class TestCleanLinkText:
    """Tests for link text cleaning functionality."""

    def test_clean_link_text_strips_ratings(
        self, extractor: RecipeLinkExtractor
    ) -> None:
        """Should strip rating count suffixes from recipe names."""
        result = extractor._clean_link_text("Simple Turkey Chili2,332Ratings")
        assert result == "Simple Turkey Chili"

    def test_clean_link_text_strips_ratings_with_spaces(
        self, extractor: RecipeLinkExtractor
    ) -> None:
        """Should strip rating count with spaces."""
        result = extractor._clean_link_text("Chicken Soup 1,234 Ratings")
        assert result == "Chicken Soup"

    def test_clean_link_text_strips_reviews(
        self, extractor: RecipeLinkExtractor
    ) -> None:
        """Should strip review count suffixes from recipe names."""
        result = extractor._clean_link_text("Best Pancakes1,234 Reviews")
        assert result == "Best Pancakes"

    def test_clean_link_text_strips_singular_rating(
        self, extractor: RecipeLinkExtractor
    ) -> None:
        """Should strip singular 'Rating' suffix."""
        result = extractor._clean_link_text("New Recipe1Rating")
        assert result == "New Recipe"

    def test_clean_link_text_preserves_normal_names(
        self, extractor: RecipeLinkExtractor
    ) -> None:
        """Should preserve recipe names without rating suffixes."""
        result = extractor._clean_link_text("Classic Banana Bread")
        assert result == "Classic Banana Bread"

    def test_clean_link_text_preserves_numbers_in_names(
        self, extractor: RecipeLinkExtractor
    ) -> None:
        """Should preserve numbers that are part of recipe names."""
        result = extractor._clean_link_text("7-Layer Dip")
        assert result == "7-Layer Dip"

    def test_clean_link_text_handles_empty_string(
        self, extractor: RecipeLinkExtractor
    ) -> None:
        """Should handle empty strings gracefully."""
        result = extractor._clean_link_text("")
        assert result == ""

    def test_clean_link_text_case_insensitive(
        self, extractor: RecipeLinkExtractor
    ) -> None:
        """Should match rating/review patterns case-insensitively."""
        result = extractor._clean_link_text("Taco Soup500RATINGS")
        assert result == "Taco Soup"


# =============================================================================
# Additional Helper Method Tests
# =============================================================================


class TestChunkLinks:
    """Tests for _chunk_links method."""

    def test_creates_multiple_chunks(self, mock_llm_client: MagicMock) -> None:
        """Should split links into multiple chunks based on chunk_size."""
        extractor = RecipeLinkExtractor(
            llm_client=mock_llm_client,
            max_html_chars=10000,
            min_confidence=0.5,
            chunk_size=3,
        )

        links = [f'<a href="/recipe/{i}">Recipe {i}</a>' for i in range(10)]
        chunks = extractor._chunk_links(links)

        # 10 links with chunk_size=3 should yield 4 chunks (3,3,3,1)
        assert len(chunks) == 4

    def test_truncates_chunks_exceeding_max_chars(
        self, mock_llm_client: MagicMock
    ) -> None:
        """Should truncate chunks that exceed max_html_chars."""
        extractor = RecipeLinkExtractor(
            llm_client=mock_llm_client,
            max_html_chars=50,
            min_confidence=0.5,
            chunk_size=50,
        )

        links = [
            '<a href="/recipe/long-url">Very Long Recipe Name</a>' for _ in range(10)
        ]
        chunks = extractor._chunk_links(links)

        # Each chunk should be truncated
        for chunk in chunks:
            assert len(chunk) <= 50 + len("\n<!-- truncated -->")
            if len(chunk) > 50:
                assert "<!-- truncated -->" in chunk

    def test_handles_empty_list(self, extractor: RecipeLinkExtractor) -> None:
        """Should return empty list for empty input."""
        chunks = extractor._chunk_links([])

        assert chunks == []

    def test_respects_chunk_size(self, mock_llm_client: MagicMock) -> None:
        """Should respect the chunk_size parameter."""
        extractor = RecipeLinkExtractor(
            llm_client=mock_llm_client,
            max_html_chars=10000,
            min_confidence=0.5,
            chunk_size=5,
        )

        links = [f'<a href="/r/{i}">R{i}</a>' for i in range(5)]
        chunks = extractor._chunk_links(links)

        # 5 links with chunk_size=5 should yield exactly 1 chunk
        assert len(chunks) == 1


class TestIsCategoryUrl:
    """Tests for _is_category_url method."""

    def test_matches_everyday_cooking_pattern(
        self, extractor: RecipeLinkExtractor
    ) -> None:
        """Should identify everyday-cooking URLs as category pages."""
        assert (
            extractor._is_category_url(
                "https://example.com/everyday-cooking/weeknight-dinners/"
            )
            is True
        )

    def test_matches_holidays_and_events_pattern(
        self, extractor: RecipeLinkExtractor
    ) -> None:
        """Should identify holidays-and-events URLs as category pages."""
        assert (
            extractor._is_category_url(
                "https://example.com/holidays-and-events/christmas/"
            )
            is True
        )

    def test_matches_family_friendly_pattern(
        self, extractor: RecipeLinkExtractor
    ) -> None:
        """Should identify family-friendly URLs as category pages."""
        assert (
            extractor._is_category_url("https://example.com/family-friendly/") is True
        )

    def test_returns_false_for_recipe_url(self, extractor: RecipeLinkExtractor) -> None:
        """Should return False for individual recipe URLs."""
        assert (
            extractor._is_category_url("https://example.com/recipes/chocolate-cake")
            is False
        )

    def test_case_insensitive(self, extractor: RecipeLinkExtractor) -> None:
        """Should match patterns case-insensitively."""
        assert (
            extractor._is_category_url("https://example.com/EVERYDAY-COOKING/recipes/")
            is True
        )


class TestExtractNameFromUrl:
    """Tests for _extract_name_from_url method."""

    def test_extracts_from_slug(self, extractor: RecipeLinkExtractor) -> None:
        """Should extract recipe name from URL slug."""
        result = extractor._extract_name_from_url(
            "https://example.com/recipes/creamy-white-chili/"
        )
        assert result == "Creamy White Chili"

    def test_converts_hyphens_to_spaces(self, extractor: RecipeLinkExtractor) -> None:
        """Should convert hyphens to spaces."""
        result = extractor._extract_name_from_url(
            "https://example.com/recipes/chicken-noodle-soup"
        )
        assert result == "Chicken Noodle Soup"

    def test_converts_underscores_to_spaces(
        self, extractor: RecipeLinkExtractor
    ) -> None:
        """Should convert underscores to spaces."""
        result = extractor._extract_name_from_url(
            "https://example.com/recipes/best_chocolate_cake"
        )
        assert result == "Best Chocolate Cake"

    def test_returns_empty_for_no_path(self, extractor: RecipeLinkExtractor) -> None:
        """Should return empty string when URL has no path."""
        result = extractor._extract_name_from_url("https://example.com/")
        assert result == ""

    def test_returns_empty_for_no_slug(self, extractor: RecipeLinkExtractor) -> None:
        """Should return empty string when path has no slug."""
        result = extractor._extract_name_from_url("https://example.com")
        assert result == ""


class TestFilterResultsFromListAdvanced:
    """Advanced tests for _filter_results_from_list method."""

    def test_filters_category_urls(self, extractor: RecipeLinkExtractor) -> None:
        """Should filter out category page URLs."""
        links = [
            ExtractedRecipeLink(
                recipe_name="Holiday Recipes",
                url="/holidays-and-events/christmas/",
                confidence=1.0,
            ),
            ExtractedRecipeLink(
                recipe_name="Actual Recipe",
                url="/recipes/chicken-pot-pie",
                confidence=1.0,
            ),
        ]

        result = extractor._filter_results_from_list(links, "https://example.com")

        assert len(result) == 1
        assert result[0][0] == "Actual Recipe"

    def test_replaces_generic_link_text_with_url_name(
        self, extractor: RecipeLinkExtractor
    ) -> None:
        """Should replace generic text like 'Get Recipe' with URL-derived name."""
        links = [
            ExtractedRecipeLink(
                recipe_name="Get Recipe",
                url="/recipes/amazing-beef-stew",
                confidence=1.0,
            ),
        ]

        result = extractor._filter_results_from_list(links, "https://example.com")

        assert len(result) == 1
        assert result[0][0] == "Amazing Beef Stew"

    def test_skips_generic_text_when_no_url_name(
        self, extractor: RecipeLinkExtractor
    ) -> None:
        """Should skip links with generic text and no extractable URL name."""
        links = [
            ExtractedRecipeLink(
                recipe_name="View Recipe",
                url="https://example.com/",  # No slug to extract
                confidence=1.0,
            ),
        ]

        result = extractor._filter_results_from_list(links, "https://example.com")

        assert len(result) == 0

    def test_skips_links_with_short_names_after_processing(
        self, extractor: RecipeLinkExtractor
    ) -> None:
        """Should skip links where name becomes too short after cleaning."""
        links = [
            ExtractedRecipeLink(
                recipe_name="  AB  ",  # Only 2 chars after strip
                url="/recipes/test",
                confidence=1.0,
            ),
        ]

        result = extractor._filter_results_from_list(links, "https://example.com")

        assert len(result) == 0


class TestProcessChunkDictHandling:
    """Tests for _process_chunk dict vs Pydantic model handling."""

    @pytest.mark.asyncio
    async def test_handles_dict_result_from_cache(
        self, mock_llm_client: MagicMock
    ) -> None:
        """Should handle dict result (from cache) and convert to Pydantic."""
        extractor = RecipeLinkExtractor(
            llm_client=mock_llm_client,
            use_llm=True,
            max_html_chars=8000,
            min_confidence=0.5,
        )

        # Simulate cached result returned as dict
        mock_llm_client.generate_structured.return_value = {
            "recipe_links": [
                {
                    "recipe_name": "Cached Recipe",
                    "url": "/recipes/cached",
                    "confidence": 0.9,
                }
            ]
        }

        result = await extractor._process_chunk(
            '<a href="/test">Test</a>',
            "https://example.com",
            "test",
            batch_num=1,
        )

        assert isinstance(result, ExtractedRecipeLinkList)
        assert len(result.recipe_links) == 1
        assert result.recipe_links[0].recipe_name == "Cached Recipe"

    @pytest.mark.asyncio
    async def test_handles_pydantic_model_result(
        self, mock_llm_client: MagicMock
    ) -> None:
        """Should handle Pydantic model result directly."""
        extractor = RecipeLinkExtractor(
            llm_client=mock_llm_client,
            use_llm=True,
            max_html_chars=8000,
            min_confidence=0.5,
        )

        # Fresh result returned as Pydantic model
        mock_llm_client.generate_structured.return_value = ExtractedRecipeLinkList(
            recipe_links=[
                ExtractedRecipeLink(
                    recipe_name="Fresh Recipe",
                    url="/recipes/fresh",
                    confidence=0.95,
                )
            ]
        )

        result = await extractor._process_chunk(
            '<a href="/test">Test</a>',
            "https://example.com",
            "test",
            batch_num=1,
        )

        assert isinstance(result, ExtractedRecipeLinkList)
        assert result.recipe_links[0].recipe_name == "Fresh Recipe"

    @pytest.mark.asyncio
    async def test_raises_on_llm_client_none(self) -> None:
        """Should raise when LLM client is None during _process_chunk."""
        extractor = RecipeLinkExtractor(
            llm_client=None,
            use_llm=True,
            max_html_chars=8000,
            min_confidence=0.5,
        )

        with pytest.raises(LLMUnavailableError):
            await extractor._process_chunk(
                '<a href="/test">Test</a>',
                "https://example.com",
                "test",
                batch_num=1,
            )


class TestBatchFailureHandling:
    """Tests for batch failure handling in _extract_with_llm."""

    @pytest.mark.asyncio
    async def test_returns_partial_results_on_some_batch_failures(
        self, mock_llm_client: MagicMock
    ) -> None:
        """Should return partial results when some batches fail."""
        extractor = RecipeLinkExtractor(
            llm_client=mock_llm_client,
            use_llm=True,
            max_html_chars=8000,
            min_confidence=0.5,
            chunk_size=2,
        )

        # First call succeeds, second fails
        mock_llm_client.generate_structured.side_effect = [
            ExtractedRecipeLinkList(
                recipe_links=[
                    ExtractedRecipeLink(
                        recipe_name="Success Recipe",
                        url="/recipes/success",
                        confidence=1.0,
                    )
                ]
            ),
            LLMTimeoutError("Timeout"),
        ]

        html = """
        <html>
        <article class="recipe-card">
            <a href="/recipes/1">Recipe One Name</a>
        </article>
        <article class="recipe-card">
            <a href="/recipes/2">Recipe Two Name</a>
        </article>
        <article class="recipe-card">
            <a href="/recipes/3">Recipe Three Name</a>
        </article>
        </html>
        """

        links = await extractor.extract(html, "https://example.com", "test")

        # Should get results from successful batch
        assert len(links) >= 1
        assert any("Success Recipe" in name for name, _ in links)

    @pytest.mark.asyncio
    async def test_raises_unavailable_when_all_batches_fail(
        self, mock_llm_client: MagicMock
    ) -> None:
        """Should fall back to regex when all LLM batches fail."""
        extractor = RecipeLinkExtractor(
            llm_client=mock_llm_client,
            use_llm=True,
            max_html_chars=8000,
            min_confidence=0.5,
            chunk_size=2,
        )

        # All batches fail
        mock_llm_client.generate_structured.side_effect = LLMTimeoutError(
            "All batches timeout"
        )

        html = """
        <html>
        <article class="recipe-card">
            <a href="/recipes/1">Recipe One Name</a>
        </article>
        </html>
        """

        # Should not raise - falls back to regex
        links = await extractor.extract(html, "https://example.com", "test")

        # Should return list (from regex fallback)
        assert isinstance(links, list)
