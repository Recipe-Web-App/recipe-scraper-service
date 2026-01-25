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
