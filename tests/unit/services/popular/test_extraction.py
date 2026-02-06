"""Unit tests for dynamic engagement metrics extraction."""

from __future__ import annotations

import pytest

from app.services.popular.extraction import (
    extract_engagement_metrics,
    extract_recipe_links,
    is_recipe_page,
)


pytestmark = pytest.mark.unit


class TestExtractEngagementMetricsFromJsonLD:
    """Tests for JSON-LD based metrics extraction."""

    def test_extracts_aggregate_rating_from_jsonld(self) -> None:
        """Should extract rating metrics from JSON-LD aggregateRating."""
        html = """
        <html>
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test Recipe",
            "aggregateRating": {
                "@type": "AggregateRating",
                "ratingValue": "4.5",
                "ratingCount": "1523",
                "reviewCount": "342"
            }
        }
        </script>
        </html>
        """
        metrics = extract_engagement_metrics(html)

        assert metrics.rating == 4.5
        assert metrics.rating_count == 1523
        assert metrics.reviews == 342

    def test_extracts_rating_from_graph_structure(self) -> None:
        """Should extract metrics from @graph JSON-LD structure."""
        html = """
        <html>
        <script type="application/ld+json">
        {
            "@graph": [
                {"@type": "WebSite", "name": "Recipe Site"},
                {
                    "@type": "Recipe",
                    "name": "Graph Recipe",
                    "aggregateRating": {
                        "ratingValue": 4.2,
                        "ratingCount": 500
                    }
                }
            ]
        }
        </script>
        </html>
        """
        metrics = extract_engagement_metrics(html)

        assert metrics.rating == 4.2
        assert metrics.rating_count == 500

    def test_handles_missing_aggregate_rating(self) -> None:
        """Should return None metrics when aggregateRating is missing."""
        html = """
        <html>
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "No Rating Recipe"
        }
        </script>
        </html>
        """
        metrics = extract_engagement_metrics(html)

        assert metrics.rating is None
        assert metrics.rating_count is None
        assert metrics.reviews is None

    def test_handles_numeric_rating_value(self) -> None:
        """Should handle numeric rating values (not strings)."""
        html = """
        <html>
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "aggregateRating": {
                "ratingValue": 4.7,
                "ratingCount": 100
            }
        }
        </script>
        </html>
        """
        metrics = extract_engagement_metrics(html)

        assert metrics.rating == 4.7
        assert metrics.rating_count == 100

    def test_clamps_rating_to_max_five(self) -> None:
        """Should return None if rating exceeds 5."""
        html = """
        <html>
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "aggregateRating": {
                "ratingValue": "95",
                "ratingCount": "100"
            }
        }
        </script>
        </html>
        """
        metrics = extract_engagement_metrics(html)

        # Rating > 5 should be rejected
        assert metrics.rating is None
        assert metrics.rating_count == 100


class TestExtractEngagementMetricsFromMicrodata:
    """Tests for microdata (itemprop) based extraction."""

    def test_extracts_rating_from_itemprop(self) -> None:
        """Should extract rating from itemprop attributes."""
        html = """
        <html>
        <div itemtype="http://schema.org/Recipe">
            <meta itemprop="ratingValue" content="4.3">
            <meta itemprop="ratingCount" content="250">
            <meta itemprop="reviewCount" content="50">
        </div>
        </html>
        """
        metrics = extract_engagement_metrics(html)

        assert metrics.rating == 4.3
        assert metrics.rating_count == 250
        assert metrics.reviews == 50

    def test_extracts_from_span_with_itemprop(self) -> None:
        """Should extract from span elements with itemprop."""
        html = """
        <html>
        <span itemprop="ratingValue">4.8</span>
        <span itemprop="ratingCount">1000</span>
        </html>
        """
        metrics = extract_engagement_metrics(html)

        assert metrics.rating == 4.8
        assert metrics.rating_count == 1000


class TestExtractEngagementMetricsFromHtmlPatterns:
    """Tests for HTML pattern-based extraction."""

    def test_extracts_rating_from_aria_label(self) -> None:
        """Should extract rating from aria-label attribute."""
        html = """
        <html>
        <div class="rating" aria-label="4.5 out of 5 stars">
            <span class="stars"></span>
        </div>
        </html>
        """
        metrics = extract_engagement_metrics(html)

        assert metrics.rating == 4.5

    def test_extracts_rating_from_title_attribute(self) -> None:
        """Should extract rating from title attribute."""
        html = """
        <html>
        <div class="star-rating" title="Rating: 4.2/5">
            <span class="stars"></span>
        </div>
        </html>
        """
        metrics = extract_engagement_metrics(html)

        assert metrics.rating == 4.2

    def test_extracts_rating_count_from_class_pattern(self) -> None:
        """Should extract count from elements with rating-count class."""
        html = """
        <html>
        <span class="rating-count">1,234 ratings</span>
        </html>
        """
        metrics = extract_engagement_metrics(html)

        assert metrics.rating_count == 1234

    def test_extracts_review_count_from_class_pattern(self) -> None:
        """Should extract count from elements with review-count class."""
        html = """
        <html>
        <span class="review-count">(567 reviews)</span>
        </html>
        """
        metrics = extract_engagement_metrics(html)

        assert metrics.reviews == 567

    def test_extracts_favorites_from_class_pattern(self) -> None:
        """Should extract favorites from elements with favorites class."""
        html = """
        <html>
        <span class="favorites">890 saves</span>
        </html>
        """
        metrics = extract_engagement_metrics(html)

        assert metrics.favorites == 890

    def test_skips_count_elements_for_rating(self) -> None:
        """Should not extract rating from elements with 'count' in class."""
        html = """
        <html>
        <span class="rating-count">4,500</span>
        </html>
        """
        metrics = extract_engagement_metrics(html)

        # Should be extracted as rating_count, not rating
        assert metrics.rating is None
        assert metrics.rating_count == 4500


class TestExtractEngagementMetricsPriority:
    """Tests for extraction priority (JSON-LD > microdata > HTML)."""

    def test_jsonld_takes_priority_over_microdata(self) -> None:
        """JSON-LD values should override microdata values."""
        html = """
        <html>
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "aggregateRating": {
                "ratingValue": "4.5",
                "ratingCount": "100"
            }
        }
        </script>
        <meta itemprop="ratingValue" content="3.0">
        <meta itemprop="ratingCount" content="50">
        </html>
        """
        metrics = extract_engagement_metrics(html)

        assert metrics.rating == 4.5
        assert metrics.rating_count == 100

    def test_microdata_fills_missing_jsonld(self) -> None:
        """Microdata should fill in missing JSON-LD values."""
        html = """
        <html>
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "aggregateRating": {
                "ratingValue": "4.5"
            }
        }
        </script>
        <meta itemprop="ratingCount" content="200">
        <meta itemprop="reviewCount" content="75">
        </html>
        """
        metrics = extract_engagement_metrics(html)

        assert metrics.rating == 4.5
        assert metrics.rating_count == 200
        assert metrics.reviews == 75


class TestExtractEngagementMetricsEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handles_empty_html(self) -> None:
        """Should return empty metrics for empty HTML."""
        metrics = extract_engagement_metrics("")

        assert metrics.rating is None
        assert metrics.rating_count is None
        assert metrics.reviews is None
        assert metrics.favorites is None

    def test_handles_malformed_jsonld(self) -> None:
        """Should handle malformed JSON-LD gracefully."""
        html = """
        <html>
        <script type="application/ld+json">
        { invalid json }
        </script>
        </html>
        """
        metrics = extract_engagement_metrics(html)

        # Should not raise, just return empty metrics
        assert metrics.rating is None

    def test_handles_no_recipe_in_jsonld(self) -> None:
        """Should handle JSON-LD without Recipe type."""
        html = """
        <html>
        <script type="application/ld+json">
        {
            "@type": "Organization",
            "name": "Not a Recipe"
        }
        </script>
        </html>
        """
        metrics = extract_engagement_metrics(html)

        assert metrics.rating is None

    def test_has_any_metrics_property(self) -> None:
        """Should correctly report whether any metrics were found."""
        empty_metrics = extract_engagement_metrics("<html></html>")
        assert empty_metrics.has_any_metrics is False

        html = """
        <html>
        <script type="application/ld+json">
        {"@type": "Recipe", "aggregateRating": {"ratingValue": "4.0"}}
        </script>
        </html>
        """
        metrics_with_rating = extract_engagement_metrics(html)
        assert metrics_with_rating.has_any_metrics is True


class TestExtractRecipeLinks:
    """Tests for recipe link extraction from listing pages."""

    def test_extracts_links_from_article_containers(self) -> None:
        """Should extract recipe links from article elements."""
        html = """
        <html>
        <article class="recipe-card">
            <a href="/recipe/12345/chocolate-cake">Chocolate Cake Recipe</a>
        </article>
        <article class="recipe-card">
            <a href="/recipe/67890/apple-pie">Classic Apple Pie</a>
        </article>
        </html>
        """
        links = extract_recipe_links(html, "https://example.com")

        assert len(links) == 2
        assert links[0] == (
            "Chocolate Cake Recipe",
            "https://example.com/recipe/12345/chocolate-cake",
        )
        assert links[1] == (
            "Classic Apple Pie",
            "https://example.com/recipe/67890/apple-pie",
        )

    def test_extracts_links_from_div_containers(self) -> None:
        """Should extract recipe links from div containers with recipe class."""
        html = """
        <html>
        <div class="recipe-item">
            <h3><a href="/recipe/123/chicken-noodle-soup">Chicken Noodle Soup</a></h3>
        </div>
        </html>
        """
        links = extract_recipe_links(html, "https://example.com")

        assert len(links) == 1
        assert links[0][0] == "Chicken Noodle Soup"

    def test_resolves_relative_urls(self) -> None:
        """Should convert relative URLs to absolute."""
        html = """
        <html>
        <article class="card">
            <a href="/recipe/456/test-recipe-name">Amazing Test Recipe</a>
        </article>
        </html>
        """
        links = extract_recipe_links(html, "https://example.com/popular")

        assert len(links) == 1
        assert links[0][1] == "https://example.com/recipe/456/test-recipe-name"

    def test_handles_absolute_urls(self) -> None:
        """Should preserve absolute URLs."""
        html = """
        <html>
        <article class="recipe">
            <a href="https://other.com/recipe/123/">Amazing External Recipe</a>
        </article>
        </html>
        """
        links = extract_recipe_links(html, "https://example.com")

        assert len(links) == 1
        assert links[0][1] == "https://other.com/recipe/123/"

    def test_skips_non_recipe_links(self) -> None:
        """Should skip links that don't look like recipe links."""
        html = """
        <html>
        <article class="item">
            <a href="/category/desserts">Desserts Category</a>
        </article>
        <article class="item">
            <a href="/recipe/789/best-chocolate-cake">Best Chocolate Cake</a>
        </article>
        </html>
        """
        links = extract_recipe_links(html, "https://example.com")

        assert len(links) == 1
        assert "cake" in links[0][1].lower()

    def test_deduplicates_urls(self) -> None:
        """Should not return duplicate URLs."""
        html = """
        <html>
        <article class="recipe">
            <a href="/recipe/999/duplicate-test-recipe">Duplicate Test Recipe</a>
        </article>
        <article class="recipe">
            <a href="/recipe/999/duplicate-test-recipe">Same Recipe Again</a>
        </article>
        </html>
        """
        links = extract_recipe_links(html, "https://example.com")

        assert len(links) == 1

    def test_extracts_name_from_heading(self) -> None:
        """Should prefer heading text for recipe name when link has generic text."""
        html = """
        <html>
        <article class="recipe-card">
            <h2><a href="/recipe/111/best-chocolate-cake">Best Ever Chocolate Cake</a></h2>
        </article>
        </html>
        """
        links = extract_recipe_links(html, "https://example.com")

        assert len(links) == 1
        assert links[0][0] == "Best Ever Chocolate Cake"

    def test_handles_empty_html(self) -> None:
        """Should return empty list for empty HTML."""
        links = extract_recipe_links("", "https://example.com")

        assert links == []

    def test_handles_no_containers(self) -> None:
        """Should fall back to any recipe-like links when no containers found."""
        html = """
        <html>
        <a href="/recipe/222/standalone-recipe-name">Standalone Recipe Name</a>
        </html>
        """
        links = extract_recipe_links(html, "https://example.com")

        assert len(links) == 1


class TestIsRecipePage:
    """Tests for recipe page validation function."""

    def test_is_recipe_page_with_jsonld(self) -> None:
        """Should return True when page has Recipe JSON-LD."""
        html = """
        <html>
        <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Recipe",
            "name": "Chocolate Cake",
            "aggregateRating": {"ratingValue": 4.5}
        }
        </script>
        </head>
        <body><h1>Chocolate Cake</h1></body>
        </html>
        """
        assert is_recipe_page(html) is True

    def test_is_recipe_page_with_microdata(self) -> None:
        """Should return True when page has Recipe microdata."""
        html = """
        <html>
        <body>
        <div itemscope itemtype="https://schema.org/Recipe">
            <h1 itemprop="name">Apple Pie</h1>
        </div>
        </body>
        </html>
        """
        assert is_recipe_page(html) is True

    def test_is_recipe_page_with_content_structure(self) -> None:
        """Should return True when page has ingredients and instructions."""
        html = """
        <html>
        <body>
            <h1>Banana Bread</h1>
            <div class="recipe-ingredients">
                <ul><li>2 bananas</li></ul>
            </div>
            <div class="recipe-instructions">
                <ol><li>Mix ingredients</li></ol>
            </div>
        </body>
        </html>
        """
        assert is_recipe_page(html) is True

    def test_is_recipe_page_category_returns_false(self) -> None:
        """Should return False for category/collection pages."""
        html = """
        <html>
        <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": "Healthy Breakfast Recipes"
        }
        </script>
        </head>
        <body>
            <h1>Healthy Breakfast Recipes</h1>
            <div class="recipe-list">
                <a href="/recipe/1">Recipe 1</a>
                <a href="/recipe/2">Recipe 2</a>
            </div>
        </body>
        </html>
        """
        assert is_recipe_page(html) is False

    def test_is_recipe_page_empty_returns_false(self) -> None:
        """Should return False for empty HTML."""
        assert is_recipe_page("") is False

    def test_is_recipe_page_no_schema_no_structure_returns_false(self) -> None:
        """Should return False when no recipe indicators present."""
        html = """
        <html>
        <body>
            <h1>About Us</h1>
            <p>Welcome to our website.</p>
        </body>
        </html>
        """
        assert is_recipe_page(html) is False


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestFindRecipeInJsonld:
    """Tests for _find_recipe_in_jsonld helper."""

    def test_finds_recipe_with_type_as_list(self) -> None:
        """Should find recipe when @type is a list containing Recipe."""
        from app.services.popular.extraction import _find_recipe_in_jsonld

        data = {"@type": ["Recipe", "Thing"], "name": "Test Recipe"}
        result = _find_recipe_in_jsonld(data)

        assert result is not None
        assert result["name"] == "Test Recipe"

    def test_finds_recipe_in_nested_graph(self) -> None:
        """Should find recipe in deeply nested @graph structure."""
        from app.services.popular.extraction import _find_recipe_in_jsonld

        data = {
            "@graph": [
                {"@type": "WebSite"},
                {"@type": "Recipe", "name": "Nested Recipe"},
            ]
        }
        result = _find_recipe_in_jsonld(data)

        assert result is not None
        assert result["name"] == "Nested Recipe"

    def test_returns_none_for_non_recipe_type(self) -> None:
        """Should return None when no Recipe type found."""
        from app.services.popular.extraction import _find_recipe_in_jsonld

        data = {"@type": "Organization", "name": "Company"}
        result = _find_recipe_in_jsonld(data)

        assert result is None

    def test_handles_empty_data(self) -> None:
        """Should return None for empty data."""
        from app.services.popular.extraction import _find_recipe_in_jsonld

        assert _find_recipe_in_jsonld({}) is None
        assert _find_recipe_in_jsonld([]) is None
        assert _find_recipe_in_jsonld(None) is None


class TestGetElementValue:
    """Tests for _get_element_value helper."""

    def test_gets_value_from_content_attribute(self) -> None:
        """Should prefer content attribute."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _get_element_value

        html = '<meta content="4.5" />'
        soup = BeautifulSoup(html, "html.parser")
        elem = soup.find("meta")

        assert _get_element_value(elem) == "4.5"

    def test_gets_value_from_value_attribute(self) -> None:
        """Should use value attribute when content missing."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _get_element_value

        html = '<input value="100" />'
        soup = BeautifulSoup(html, "html.parser")
        elem = soup.find("input")

        assert _get_element_value(elem) == "100"

    def test_falls_back_to_text_content(self) -> None:
        """Should use text content when no attributes present."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _get_element_value

        html = "<span>4.8</span>"
        soup = BeautifulSoup(html, "html.parser")
        elem = soup.find("span")

        assert _get_element_value(elem) == "4.8"

    def test_returns_none_for_empty_element(self) -> None:
        """Should return None for empty element."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _get_element_value

        html = "<span></span>"
        soup = BeautifulSoup(html, "html.parser")
        elem = soup.find("span")

        assert _get_element_value(elem) is None


class TestParseRatingFromText:
    """Tests for _parse_rating_from_text helper."""

    def test_parses_x_out_of_5_format(self) -> None:
        """Should parse 'X out of 5' format."""
        from app.services.popular.extraction import _parse_rating_from_text

        assert _parse_rating_from_text("4.5 out of 5") == 4.5
        assert _parse_rating_from_text("Rating: 4 out of 5 stars") == 4.0

    def test_parses_x_slash_5_format(self) -> None:
        """Should parse 'X/5' format."""
        from app.services.popular.extraction import _parse_rating_from_text

        assert _parse_rating_from_text("4.2/5") == 4.2
        assert _parse_rating_from_text("Rating: 3.5/5") == 3.5

    def test_parses_standalone_decimal(self) -> None:
        """Should parse standalone decimal if in range."""
        from app.services.popular.extraction import _parse_rating_from_text

        assert _parse_rating_from_text("4.7") == 4.7
        assert _parse_rating_from_text("Rating is 3.8") == 3.8

    def test_returns_none_for_out_of_range(self) -> None:
        """Should return None for values outside 0-5 range."""
        from app.services.popular.extraction import _parse_rating_from_text

        # 7.5 is not a valid rating (outside 0-5)
        assert _parse_rating_from_text("7.5") is None

    def test_returns_none_for_no_number(self) -> None:
        """Should return None when no number found."""
        from app.services.popular.extraction import _parse_rating_from_text

        assert _parse_rating_from_text("No rating here") is None
        assert _parse_rating_from_text("") is None


class TestExtractCountFromText:
    """Tests for _extract_count_from_text helper."""

    def test_extracts_number_with_commas(self) -> None:
        """Should handle numbers with comma separators."""
        from app.services.popular.extraction import _extract_count_from_text

        assert _extract_count_from_text("1,234 reviews") == 1234
        assert _extract_count_from_text("10,000 ratings") == 10000

    def test_extracts_number_from_parentheses(self) -> None:
        """Should extract number from parentheses."""
        from app.services.popular.extraction import _extract_count_from_text

        assert _extract_count_from_text("(567)") == 567
        assert _extract_count_from_text("Reviews (123)") == 123

    def test_returns_none_for_empty_text(self) -> None:
        """Should return None for empty text."""
        from app.services.popular.extraction import _extract_count_from_text

        assert _extract_count_from_text("") is None
        assert _extract_count_from_text(None) is None


class TestIsRecipeLink:
    """Tests for _is_recipe_link helper."""

    def test_accepts_recipe_url_with_id(self) -> None:
        """Should accept recipe URLs with numeric IDs."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _is_recipe_link

        html = '<a href="/recipe/12345/chocolate-cake">Delicious Chocolate Cake</a>'
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")

        assert _is_recipe_link(link) is True

    def test_rejects_category_urls(self) -> None:
        """Should reject category/collection URLs."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _is_recipe_link

        html = '<a href="/category/desserts">All Dessert Recipes</a>'
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")

        assert _is_recipe_link(link) is False

    def test_rejects_short_link_text(self) -> None:
        """Should reject links with very short text."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _is_recipe_link

        html = '<a href="/recipe/123/test">Test</a>'
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")

        assert _is_recipe_link(link) is False

    def test_rejects_single_word_links(self) -> None:
        """Should reject single-word link text."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _is_recipe_link

        html = '<a href="/recipe/123/test">Recipes</a>'
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")

        assert _is_recipe_link(link) is False

    def test_rejects_navigation_text(self) -> None:
        """Should reject navigation-like link text."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _is_recipe_link

        html = '<a href="/recipe/123">Log In Now</a>'
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")

        assert _is_recipe_link(link) is False

    def test_returns_false_for_empty_href(self) -> None:
        """Should return False for empty href."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _is_recipe_link

        html = '<a href="">Link Text Here</a>'
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")

        assert _is_recipe_link(link) is False


class TestResolveUrl:
    """Tests for _resolve_url helper."""

    def test_returns_absolute_url_unchanged(self) -> None:
        """Should return absolute URLs unchanged."""
        from app.services.popular.extraction import _resolve_url

        result = _resolve_url("https://example.com/recipe", "https://base.com")
        assert result == "https://example.com/recipe"

    def test_resolves_protocol_relative_url(self) -> None:
        """Should resolve protocol-relative URLs with https."""
        from app.services.popular.extraction import _resolve_url

        result = _resolve_url("//cdn.example.com/img.jpg", "https://base.com")
        assert result == "https://cdn.example.com/img.jpg"

    def test_resolves_root_relative_url(self) -> None:
        """Should resolve root-relative URLs."""
        from app.services.popular.extraction import _resolve_url

        result = _resolve_url("/recipe/123", "https://example.com/page/1")
        assert result == "https://example.com/recipe/123"

    def test_resolves_path_relative_url(self) -> None:
        """Should resolve path-relative URLs."""
        from app.services.popular.extraction import _resolve_url

        result = _resolve_url("subpage", "https://example.com/dir")
        assert result == "https://example.com/dir/subpage"

    def test_returns_none_for_empty_href(self) -> None:
        """Should return None for empty href."""
        from app.services.popular.extraction import _resolve_url

        assert _resolve_url("", "https://example.com") is None


class TestExtractLinkText:
    """Tests for _extract_link_text helper."""

    def test_extracts_direct_text(self) -> None:
        """Should extract direct text from link."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _extract_link_text

        html = "<a>Chocolate Cake Recipe</a>"
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")

        assert _extract_link_text(link) == "Chocolate Cake Recipe"

    def test_extracts_from_title_attribute(self) -> None:
        """Should use title attribute when no direct text."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _extract_link_text

        html = '<a title="Apple Pie Recipe"></a>'
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")

        assert _extract_link_text(link) == "Apple Pie Recipe"

    def test_extracts_from_aria_label(self) -> None:
        """Should use aria-label when no text or title."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _extract_link_text

        html = '<a aria-label="Banana Bread"></a>'
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")

        assert _extract_link_text(link) == "Banana Bread"

    def test_extracts_from_img_alt(self) -> None:
        """Should use img alt text as fallback."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _extract_link_text

        html = '<a><img alt="Delicious Cookie Recipe" /></a>'
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")

        assert _extract_link_text(link) == "Delicious Cookie Recipe"

    def test_strips_rating_suffixes(self) -> None:
        """Should strip rating/review suffixes from text."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _extract_link_text

        html = "<a>Chocolate Cake 500 Ratings</a>"
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")

        assert _extract_link_text(link) == "Chocolate Cake"


class TestParseFloat:
    """Tests for _parse_float helper."""

    def test_parses_string_float(self) -> None:
        """Should parse float from string."""
        from app.services.popular.extraction import _parse_float

        assert _parse_float("4.5") == 4.5
        assert _parse_float("3.0") == 3.0

    def test_parses_int(self) -> None:
        """Should parse int as float."""
        from app.services.popular.extraction import _parse_float

        assert _parse_float(4) == 4.0
        assert _parse_float("5") == 5.0

    def test_extracts_number_from_string(self) -> None:
        """Should extract number from longer string."""
        from app.services.popular.extraction import _parse_float

        assert _parse_float("Rating: 4.5 stars") == 4.5

    def test_respects_max_val(self) -> None:
        """Should return None if exceeds max_val."""
        from app.services.popular.extraction import _parse_float

        assert _parse_float("10", max_val=5.0) is None
        assert _parse_float("4.5", max_val=5.0) == 4.5

    def test_returns_none_for_invalid(self) -> None:
        """Should return None for invalid values."""
        from app.services.popular.extraction import _parse_float

        assert _parse_float(None) is None
        assert _parse_float("not a number") is None

    def test_extracts_positive_from_negative_string(self) -> None:
        """Should extract positive number from string with minus sign."""
        from app.services.popular.extraction import _parse_float

        # The regex extracts digits only, so -1.5 becomes 1.5
        assert _parse_float("-1.5") == 1.5


class TestParseInt:
    """Tests for _parse_int helper."""

    def test_parses_string_int(self) -> None:
        """Should parse int from string."""
        from app.services.popular.extraction import _parse_int

        assert _parse_int("100") == 100
        assert _parse_int("1234") == 1234

    def test_parses_float_to_int(self) -> None:
        """Should convert float to int."""
        from app.services.popular.extraction import _parse_int

        assert _parse_int(99.9) == 99
        assert _parse_int("50.5") == 50

    def test_removes_commas(self) -> None:
        """Should handle comma-separated numbers."""
        from app.services.popular.extraction import _parse_int

        assert _parse_int("1,234") == 1234
        assert _parse_int("10,000") == 10000

    def test_extracts_number_from_string(self) -> None:
        """Should extract number from longer string."""
        from app.services.popular.extraction import _parse_int

        assert _parse_int("500 reviews") == 500

    def test_returns_none_for_invalid(self) -> None:
        """Should return None for invalid values."""
        from app.services.popular.extraction import _parse_int

        assert _parse_int(None) is None
        assert _parse_int("no numbers here") is None


class TestFindRecipeInJsonldList:
    """Tests for _find_recipe_in_jsonld with list input."""

    def test_finds_recipe_in_list(self) -> None:
        """Should find Recipe in a list of JSON-LD objects."""
        from app.services.popular.extraction import _find_recipe_in_jsonld

        data = [
            {"@type": "WebSite", "name": "Recipe Site"},
            {"@type": "Recipe", "name": "Found Recipe"},
        ]
        result = _find_recipe_in_jsonld(data)

        assert result is not None
        assert result["name"] == "Found Recipe"

    def test_returns_none_for_empty_list(self) -> None:
        """Should return None for empty list."""
        from app.services.popular.extraction import _find_recipe_in_jsonld

        assert _find_recipe_in_jsonld([]) is None

    def test_returns_none_for_list_without_recipe(self) -> None:
        """Should return None when list has no Recipe type."""
        from app.services.popular.extraction import _find_recipe_in_jsonld

        data = [
            {"@type": "WebSite", "name": "Site"},
            {"@type": "Organization", "name": "Org"},
        ]
        assert _find_recipe_in_jsonld(data) is None


class TestExtractRatingValue:
    """Tests for _extract_rating_value helper."""

    def test_extracts_from_data_attribute(self) -> None:
        """Should extract rating from data-rating attribute."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _extract_rating_value

        html = '<span data-rating="4.5">Rating</span>'
        soup = BeautifulSoup(html, "html.parser")
        elem = soup.find("span")

        assert _extract_rating_value(elem) == 4.5

    def test_extracts_from_data_value_attribute(self) -> None:
        """Should extract rating from data-value attribute."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _extract_rating_value

        html = '<span data-value="4.2">Rating</span>'
        soup = BeautifulSoup(html, "html.parser")
        elem = soup.find("span")

        assert _extract_rating_value(elem) == 4.2

    def test_extracts_from_text_content(self) -> None:
        """Should extract rating from text content."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _extract_rating_value

        html = "<span>4.5 out of 5</span>"
        soup = BeautifulSoup(html, "html.parser")
        elem = soup.find("span")

        assert _extract_rating_value(elem) == 4.5

    def test_returns_none_when_no_rating(self) -> None:
        """Should return None when no rating found."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _extract_rating_value

        html = "<span>No rating here</span>"
        soup = BeautifulSoup(html, "html.parser")
        elem = soup.find("span")

        assert _extract_rating_value(elem) is None


class TestFindCountInHtml:
    """Tests for _find_count_in_html helper."""

    def test_finds_count_by_id(self) -> None:
        """Should find count in element with matching id."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _find_count_in_html

        html = '<div id="review-count">500</div>'
        soup = BeautifulSoup(html, "html.parser")

        result = _find_count_in_html(soup, ["review"])

        assert result == 500


class TestExtractCountFromElement:
    """Tests for _extract_count_from_element helper."""

    def test_extracts_from_data_count_attribute(self) -> None:
        """Should extract count from data-count attribute."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _extract_count_from_element

        html = '<span data-count="250">Reviews</span>'
        soup = BeautifulSoup(html, "html.parser")
        elem = soup.find("span")

        assert _extract_count_from_element(elem) == 250

    def test_extracts_from_data_total_attribute(self) -> None:
        """Should extract count from data-total attribute."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _extract_count_from_element

        html = '<span data-total="100">Ratings</span>'
        soup = BeautifulSoup(html, "html.parser")
        elem = soup.find("span")

        assert _extract_count_from_element(elem) == 100


class TestExtractCountFromTextEdgeCases:
    """Additional tests for _extract_count_from_text."""

    def test_returns_none_for_no_numbers(self) -> None:
        """Should return None when text has no numbers."""
        from app.services.popular.extraction import _extract_count_from_text

        assert _extract_count_from_text("no numbers at all") is None


class TestIsRecipeLinkFalseCase:
    """Tests for _is_recipe_link returning False."""

    def test_returns_false_for_non_recipe_link(self) -> None:
        """Should return False for links that don't match recipe patterns."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _is_recipe_link

        html = '<a href="/about-us">About Us</a>'
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")

        assert _is_recipe_link(link) is False

    def test_returns_false_for_category_link(self) -> None:
        """Should return False for category links."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _is_recipe_link

        html = '<a href="/category/desserts">Desserts</a>'
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")

        assert _is_recipe_link(link) is False


class TestExtractRecipeName:
    """Tests for _extract_recipe_name helper."""

    def test_extracts_from_heading_in_container(self) -> None:
        """Should extract name from heading when link text is short."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _extract_recipe_name

        html = """
        <article>
            <h2>Delicious Chocolate Cake</h2>
            <a href="/recipe/123">Go</a>
        </article>
        """
        soup = BeautifulSoup(html, "html.parser")
        container = soup.find("article")
        link = container.find("a")

        result = _extract_recipe_name(link, container)

        assert result == "Delicious Chocolate Cake"

    def test_extracts_from_title_class_element(self) -> None:
        """Should extract name from element with title/name class."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _extract_recipe_name

        html = """
        <article>
            <span class="recipe-title">Banana Bread Recipe</span>
            <a href="/recipe/456">Go</a>
        </article>
        """
        soup = BeautifulSoup(html, "html.parser")
        container = soup.find("article")
        link = container.find("a")

        result = _extract_recipe_name(link, container)

        assert result == "Banana Bread Recipe"

    def test_strips_ratings_suffix_from_heading(self) -> None:
        """Should strip rating suffix from heading text."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _extract_recipe_name

        html = """
        <article>
            <h3>Apple Pie 1,500 Ratings</h3>
            <a href="/recipe/789">See</a>
        </article>
        """
        soup = BeautifulSoup(html, "html.parser")
        container = soup.find("article")
        link = container.find("a")

        result = _extract_recipe_name(link, container)

        assert result == "Apple Pie"

    def test_strips_reviews_suffix_from_title_element(self) -> None:
        """Should strip review suffix from title element."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _extract_recipe_name

        html = """
        <article>
            <div class="card-title">Pasta Primavera 250 Reviews</div>
            <a href="/recipe/abc">Go</a>
        </article>
        """
        soup = BeautifulSoup(html, "html.parser")
        container = soup.find("article")
        link = container.find("a")

        result = _extract_recipe_name(link, container)

        assert result == "Pasta Primavera"

    def test_returns_none_when_no_name_found(self) -> None:
        """Should return None when no suitable name found."""
        from bs4 import BeautifulSoup

        from app.services.popular.extraction import _extract_recipe_name

        html = """
        <article>
            <a href="/recipe/xyz">Go</a>
        </article>
        """
        soup = BeautifulSoup(html, "html.parser")
        container = soup.find("article")
        link = container.find("a")

        result = _extract_recipe_name(link, container)

        assert result is None


class TestExtractRecipeLinksHelpers:
    """Tests for helper functions inside extract_recipe_links."""

    def test_extracts_name_from_url_slug(self) -> None:
        """Should extract and format name from URL slug."""
        html = """
        <html>
        <article class="recipe-card">
            <a href="/recipes/chocolate-chip-cookies">View Recipe</a>
        </article>
        </html>
        """
        links = extract_recipe_links(html, "https://example.com")

        # Should have extracted link with name from URL
        assert len(links) > 0
        # The name should be derived from the URL slug
        assert any("Chocolate Chip Cookies" in name for name, _ in links)

    def test_replaces_generic_link_text_with_url_name(self) -> None:
        """Should replace generic text like 'view recipe' with URL-derived name."""
        html = """
        <html>
        <article class="recipe-item">
            <a href="/recipes/garlic-butter-shrimp">view recipe</a>
        </article>
        </html>
        """
        links = extract_recipe_links(html, "https://example.com")

        # Should replace "view recipe" with name from URL
        assert len(links) > 0
        # Should not have "view recipe" as the name
        assert not any(name.lower() == "view recipe" for name, _ in links)

    def test_handles_empty_url_path(self) -> None:
        """Should handle URL with empty path gracefully."""
        html = """
        <html>
        <article class="recipe-card">
            <a href="/">Home</a>
        </article>
        </html>
        """
        links = extract_recipe_links(html, "https://example.com")

        # Should not crash and may return empty or filtered results
        assert isinstance(links, list)
