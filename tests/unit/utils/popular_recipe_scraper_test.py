"""Unit tests for the popular recipe web scraper utility."""

import json
from unittest.mock import Mock, patch

import httpx
import pytest
from bs4 import BeautifulSoup, Tag

from app.exceptions.custom_exceptions import RecipeScrapingError
from app.utils.popular_recipe_web_scraper import (
    MAX_RECIPE_NAME_LENGTH,
    MIN_RECIPE_NAME_LENGTH,
    MIN_VALID_RECIPE_NAME_LENGTH,
    _clean_recipe_name,
    _extract_json_ld_recipes,
    _extract_microdata_recipes,
    _extract_recipe_card_links,
    _extract_recipe_links,
    _extract_recipe_name,
    _extract_recipe_url_links,
    _extract_structured_recipe_links,
    _is_category_name,
    _is_recipe_url,
    _is_valid_recipe_name,
    _resolve_url,
    scrape_popular_recipes,
)


class TestScrapePopularRecipes:
    """Unit tests for the main scrape_popular_recipes function."""

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper.httpx.Client")
    @patch("app.utils.popular_recipe_web_scraper._extract_recipe_links")
    def test_scrape_popular_recipes_success(
        self, mock_extract_links: Mock, mock_client_class: Mock
    ) -> None:
        """Test successful recipe scraping."""
        # Arrange
        url = "https://example.com/recipes"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = "<html><body>Test content</body></html>"

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        mock_extract_links.return_value = [
            ("https://example.com/recipe1", "Chocolate Cake"),
            ("https://example.com/recipe2", "Pasta Bolognese"),
        ]

        # Act
        with patch("app.utils.popular_recipe_web_scraper.WebRecipe") as mock_web_recipe:
            mock_web_recipe.side_effect = lambda recipe_name, url: Mock(
                recipe_name=recipe_name, url=url
            )
            result = scrape_popular_recipes(url, max_recipes=5)

        # Assert
        assert len(result) == 2
        mock_client.get.assert_called_once()
        mock_extract_links.assert_called_once()

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper.httpx.Client")
    def test_scrape_popular_recipes_http_error(self, mock_client_class: Mock) -> None:
        """Test recipe scraping with HTTP error."""
        # Arrange
        url = "https://example.com/recipes"
        mock_response = Mock()
        mock_response.status_code = 404

        mock_client = Mock()
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        # Act & Assert
        with pytest.raises(RecipeScrapingError):
            scrape_popular_recipes(url)

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper.httpx.Client")
    def test_scrape_popular_recipes_network_error(
        self, mock_client_class: Mock
    ) -> None:
        """Test recipe scraping with network error."""
        # Arrange
        url = "https://example.com/recipes"

        mock_client = Mock()
        mock_client.get.side_effect = httpx.RequestError("Network error")
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        # Act & Assert
        with pytest.raises(RecipeScrapingError):
            scrape_popular_recipes(url)

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper.httpx.Client")
    def test_scrape_popular_recipes_parsing_error(
        self, mock_client_class: Mock
    ) -> None:
        """Test recipe scraping with parsing error."""
        # Arrange
        url = "https://example.com/recipes"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = "<html><body>Test content</body></html>"

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        # Act & Assert
        with patch(
            "app.utils.popular_recipe_web_scraper.BeautifulSoup",
            side_effect=Exception("Parse error"),
        ):
            with pytest.raises(RecipeScrapingError):
                scrape_popular_recipes(url)


class TestExtractRecipeLinks:
    """Unit tests for the _extract_recipe_links function."""

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper._extract_recipe_url_links")
    @patch("app.utils.popular_recipe_web_scraper._extract_structured_recipe_links")
    @patch("app.utils.popular_recipe_web_scraper._extract_recipe_card_links")
    def test_extract_recipe_links_multiple_strategies(
        self, mock_card_links: Mock, mock_structured_links: Mock, mock_url_links: Mock
    ) -> None:
        """Test that multiple extraction strategies are used."""
        # Arrange
        soup = BeautifulSoup("<html></html>", "html.parser")
        base_url = "https://example.com"
        max_recipes = 10

        mock_url_links.return_value = [("url1", "Recipe 1")]
        mock_structured_links.return_value = [("url2", "Recipe 2")]
        mock_card_links.return_value = [("url3", "Recipe 3")]

        # Act
        result = _extract_recipe_links(soup, base_url, max_recipes)

        # Assert
        assert len(result) == 3
        mock_url_links.assert_called_once_with(soup, base_url, max_recipes)
        mock_structured_links.assert_called_once()
        mock_card_links.assert_called_once()

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper._extract_recipe_url_links")
    @patch("app.utils.popular_recipe_web_scraper._extract_structured_recipe_links")
    @patch("app.utils.popular_recipe_web_scraper._extract_recipe_card_links")
    def test_extract_recipe_links_max_limit(
        self, mock_card_links: Mock, mock_structured_links: Mock, mock_url_links: Mock
    ) -> None:
        """Test that results are limited by max_recipes."""
        # Arrange
        soup = BeautifulSoup("<html></html>", "html.parser")
        base_url = "https://example.com"
        max_recipes = 2

        mock_url_links.return_value = [("url1", "Recipe 1"), ("url2", "Recipe 2")]
        mock_structured_links.return_value = [("url3", "Recipe 3")]
        mock_card_links.return_value = []

        # Act
        result = _extract_recipe_links(soup, base_url, max_recipes)

        # Assert
        assert len(result) == 2
        assert result == [("url1", "Recipe 1"), ("url2", "Recipe 2")]


class TestExtractRecipeUrlLinks:
    """Unit tests for the _extract_recipe_url_links function."""

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper._is_recipe_url")
    @patch("app.utils.popular_recipe_web_scraper._resolve_url")
    @patch("app.utils.popular_recipe_web_scraper._extract_recipe_name")
    @patch("app.utils.popular_recipe_web_scraper._is_valid_recipe_name")
    def test_extract_recipe_url_links_success(
        self,
        mock_valid_name: Mock,
        mock_extract_name: Mock,
        mock_resolve_url: Mock,
        mock_is_recipe_url: Mock,
    ) -> None:
        """Test successful URL link extraction."""
        # Arrange
        html = '<a href="/recipe/chocolate-cake">Chocolate Cake</a>'
        soup = BeautifulSoup(html, "html.parser")
        base_url = "https://example.com"
        max_recipes = 10

        mock_is_recipe_url.return_value = True
        mock_resolve_url.return_value = "https://example.com/recipe/chocolate-cake"
        mock_extract_name.return_value = "Chocolate Cake"
        mock_valid_name.return_value = True

        # Act
        result = _extract_recipe_url_links(soup, base_url, max_recipes)

        # Assert
        assert len(result) == 1
        assert result[0] == (
            "https://example.com/recipe/chocolate-cake",
            "Chocolate Cake",
        )

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper._is_recipe_url")
    def test_extract_recipe_url_links_not_recipe_url(
        self, mock_is_recipe_url: Mock
    ) -> None:
        """Test URL link extraction when URL is not a recipe URL."""
        # Arrange
        html = '<a href="/about">About Us</a>'
        soup = BeautifulSoup(html, "html.parser")
        base_url = "https://example.com"
        max_recipes = 10

        mock_is_recipe_url.return_value = False

        # Act
        result = _extract_recipe_url_links(soup, base_url, max_recipes)

        # Assert
        assert len(result) == 0

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper._is_recipe_url")
    @patch("app.utils.popular_recipe_web_scraper._resolve_url")
    def test_extract_recipe_url_links_invalid_url(
        self, mock_resolve_url: Mock, mock_is_recipe_url: Mock
    ) -> None:
        """Test URL link extraction with invalid URL."""
        # Arrange
        html = '<a href="/recipe/chocolate-cake">Chocolate Cake</a>'
        soup = BeautifulSoup(html, "html.parser")
        base_url = "https://example.com"
        max_recipes = 10

        mock_is_recipe_url.return_value = True
        mock_resolve_url.return_value = None

        # Act
        result = _extract_recipe_url_links(soup, base_url, max_recipes)

        # Assert
        assert len(result) == 0


class TestExtractRecipeCardLinks:
    """Unit tests for the _extract_recipe_card_links function."""

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper._resolve_url")
    @patch("app.utils.popular_recipe_web_scraper._extract_recipe_name")
    @patch("app.utils.popular_recipe_web_scraper._is_valid_recipe_name")
    def test_extract_recipe_card_links_success(
        self, mock_valid_name: Mock, mock_extract_name: Mock, mock_resolve_url: Mock
    ) -> None:
        """Test successful recipe card link extraction."""
        # Arrange
        html = '''
        <div class="recipe-card">
            <a href="/recipe/pasta">Pasta Recipe</a>
        </div>
        '''
        soup = BeautifulSoup(html, "html.parser")
        base_url = "https://example.com"
        max_recipes = 10

        mock_resolve_url.return_value = "https://example.com/recipe/pasta"
        mock_extract_name.return_value = "Pasta Recipe"
        mock_valid_name.return_value = True

        # Act
        result = _extract_recipe_card_links(soup, base_url, max_recipes)

        # Assert
        assert len(result) == 1
        assert result[0] == ("https://example.com/recipe/pasta", "Pasta Recipe")

    @pytest.mark.unit
    def test_extract_recipe_card_links_no_cards(self) -> None:
        """Test recipe card extraction when no cards exist."""
        # Arrange
        html = '<div class="content">No recipe cards</div>'
        soup = BeautifulSoup(html, "html.parser")
        base_url = "https://example.com"
        max_recipes = 10

        # Act
        result = _extract_recipe_card_links(soup, base_url, max_recipes)

        # Assert
        assert len(result) == 0

    @pytest.mark.unit
    def test_extract_recipe_card_links_no_links_in_cards(self) -> None:
        """Test recipe card extraction when cards have no links."""
        # Arrange
        html = '<div class="recipe-card">Just text, no links</div>'
        soup = BeautifulSoup(html, "html.parser")
        base_url = "https://example.com"
        max_recipes = 10

        # Act
        result = _extract_recipe_card_links(soup, base_url, max_recipes)

        # Assert
        assert len(result) == 0


class TestExtractStructuredRecipeLinks:
    """Unit tests for the _extract_structured_recipe_links function."""

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper._extract_json_ld_recipes")
    @patch("app.utils.popular_recipe_web_scraper._extract_microdata_recipes")
    def test_extract_structured_recipe_links_json_ld_and_microdata(
        self, mock_microdata: Mock, mock_json_ld: Mock
    ) -> None:
        """Test structured data extraction with both JSON-LD and microdata."""
        # Arrange
        soup = BeautifulSoup("<html></html>", "html.parser")
        base_url = "https://example.com"
        max_recipes = 10

        mock_json_ld.return_value = [("url1", "Recipe 1")]
        mock_microdata.return_value = [("url2", "Recipe 2")]

        # Act
        result = _extract_structured_recipe_links(soup, base_url, max_recipes)

        # Assert
        assert len(result) == 2
        mock_json_ld.assert_called_once_with(soup, base_url, max_recipes)
        mock_microdata.assert_called_once()

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper._extract_json_ld_recipes")
    @patch("app.utils.popular_recipe_web_scraper._extract_microdata_recipes")
    def test_extract_structured_recipe_links_max_limit_reached(
        self, mock_microdata: Mock, mock_json_ld: Mock
    ) -> None:
        """Test that microdata is not called if JSON-LD reaches limit."""
        # Arrange
        soup = BeautifulSoup("<html></html>", "html.parser")
        base_url = "https://example.com"
        max_recipes = 2

        mock_json_ld.return_value = [("url1", "Recipe 1"), ("url2", "Recipe 2")]

        # Act
        result = _extract_structured_recipe_links(soup, base_url, max_recipes)

        # Assert
        assert len(result) == 2
        mock_json_ld.assert_called_once()
        mock_microdata.assert_not_called()


class TestExtractJsonLdRecipes:
    """Unit tests for the _extract_json_ld_recipes function."""

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper._resolve_url")
    @patch("app.utils.popular_recipe_web_scraper._is_valid_recipe_name")
    def test_extract_json_ld_recipes_success(
        self, mock_valid_name: Mock, mock_resolve_url: Mock
    ) -> None:
        """Test successful JSON-LD recipe extraction."""
        # Arrange
        json_data = {
            "@type": "Recipe",
            "name": "Chocolate Cake Recipe",
            "url": "https://example.com/recipe/chocolate-cake",
        }
        html = f'<script type="application/ld+json">{json.dumps(json_data)}</script>'
        soup = BeautifulSoup(html, "html.parser")
        base_url = "https://example.com"
        max_recipes = 10

        mock_resolve_url.return_value = "https://example.com/recipe/chocolate-cake"
        mock_valid_name.return_value = True

        # Act
        result = _extract_json_ld_recipes(soup, base_url, max_recipes)

        # Assert
        assert len(result) == 1
        assert result[0] == (
            "https://example.com/recipe/chocolate-cake",
            "Chocolate Cake Recipe",
        )

    @pytest.mark.unit
    def test_extract_json_ld_recipes_invalid_json(self) -> None:
        """Test JSON-LD extraction with invalid JSON."""
        # Arrange
        html = '<script type="application/ld+json">invalid json</script>'
        soup = BeautifulSoup(html, "html.parser")
        base_url = "https://example.com"
        max_recipes = 10

        # Act
        result = _extract_json_ld_recipes(soup, base_url, max_recipes)

        # Assert
        assert len(result) == 0

    @pytest.mark.unit
    def test_extract_json_ld_recipes_not_recipe_type(self) -> None:
        """Test JSON-LD extraction with non-recipe type."""
        # Arrange
        json_data = {
            "@type": "Article",
            "name": "Article Title",
            "url": "https://example.com/article",
        }
        html = f'<script type="application/ld+json">{json.dumps(json_data)}</script>'
        soup = BeautifulSoup(html, "html.parser")
        base_url = "https://example.com"
        max_recipes = 10

        # Act
        result = _extract_json_ld_recipes(soup, base_url, max_recipes)

        # Assert
        assert len(result) == 0

    @pytest.mark.unit
    def test_extract_json_ld_recipes_missing_data(self) -> None:
        """Test JSON-LD extraction with missing required data."""
        # Arrange
        json_data = {"@type": "Recipe"}  # Missing name and url
        html = f'<script type="application/ld+json">{json.dumps(json_data)}</script>'
        soup = BeautifulSoup(html, "html.parser")
        base_url = "https://example.com"
        max_recipes = 10

        # Act
        result = _extract_json_ld_recipes(soup, base_url, max_recipes)

        # Assert
        assert len(result) == 0


class TestExtractMicrodataRecipes:
    """Unit tests for the _extract_microdata_recipes function."""

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper._resolve_url")
    @patch("app.utils.popular_recipe_web_scraper._extract_recipe_name")
    @patch("app.utils.popular_recipe_web_scraper._is_valid_recipe_name")
    def test_extract_microdata_recipes_success(
        self, mock_valid_name: Mock, mock_extract_name: Mock, mock_resolve_url: Mock
    ) -> None:
        """Test successful microdata recipe extraction."""
        # Arrange
        html = '''
        <div itemtype="https://schema.org/Recipe">
            <a href="/recipe/pasta" itemprop="url">Pasta Recipe</a>
        </div>
        '''
        soup = BeautifulSoup(html, "html.parser")
        base_url = "https://example.com"
        max_recipes = 10

        mock_resolve_url.return_value = "https://example.com/recipe/pasta"
        mock_extract_name.return_value = "Pasta Recipe"
        mock_valid_name.return_value = True

        # Act
        result = _extract_microdata_recipes(soup, base_url, max_recipes)

        # Assert
        assert len(result) == 1
        assert result[0] == ("https://example.com/recipe/pasta", "Pasta Recipe")

    @pytest.mark.unit
    def test_extract_microdata_recipes_no_items(self) -> None:
        """Test microdata extraction when no recipe items exist."""
        # Arrange
        html = '<div>No microdata here</div>'
        soup = BeautifulSoup(html, "html.parser")
        base_url = "https://example.com"
        max_recipes = 10

        # Act
        result = _extract_microdata_recipes(soup, base_url, max_recipes)

        # Assert
        assert len(result) == 0

    @pytest.mark.unit
    def test_extract_microdata_recipes_no_links(self) -> None:
        """Test microdata extraction when recipe items have no links."""
        # Arrange
        html = '<div itemtype="https://schema.org/Recipe">No links</div>'
        soup = BeautifulSoup(html, "html.parser")
        base_url = "https://example.com"
        max_recipes = 10

        # Act
        result = _extract_microdata_recipes(soup, base_url, max_recipes)

        # Assert
        assert len(result) == 0


class TestIsRecipeUrl:
    """Unit tests for the _is_recipe_url function."""

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper.settings")
    def test_is_recipe_url_valid_recipe(self, mock_settings: Mock) -> None:
        """Test URL validation for valid recipe URLs."""
        # Arrange
        mock_settings.web_scraper_url_exclude_keywords = ["category", "tag", "about"]
        url = "https://example.com/recipe/chocolate-cake"

        # Act
        result = _is_recipe_url(url)

        # Assert
        assert result is True

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper.settings")
    def test_is_recipe_url_excluded_keyword(self, mock_settings: Mock) -> None:
        """Test URL validation with excluded keywords."""
        # Arrange
        mock_settings.web_scraper_url_exclude_keywords = ["category", "tag", "about"]
        url = "https://example.com/recipe/category/desserts"

        # Act
        result = _is_recipe_url(url)

        # Assert
        assert result is False

    @pytest.mark.unit
    def test_is_recipe_url_no_recipe_keyword(self) -> None:
        """Test URL validation without recipe keywords."""
        # Arrange
        url = "https://example.com/about/contact"

        # Act
        result = _is_recipe_url(url)

        # Assert
        assert result is False

    @pytest.mark.unit
    def test_is_recipe_url_empty_url(self) -> None:
        """Test URL validation with empty URL."""
        # Arrange
        url = ""

        # Act
        result = _is_recipe_url(url)

        # Assert
        assert result is False


class TestIsValidRecipeName:
    """Unit tests for the _is_valid_recipe_name function."""

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper.settings")
    def test_is_valid_recipe_name_valid(self, mock_settings: Mock) -> None:
        """Test recipe name validation for valid names."""
        # Arrange
        mock_settings.web_scraper_exclude_names = ["home", "about", "contact"]
        mock_settings.web_scraper_nav_prefixes = ["view", "see", "browse"]
        mock_settings.web_scraper_food_indicators = ["cake", "pasta", "chicken", "soup"]
        name = "Chocolate Cake Recipe"

        # Act
        result = _is_valid_recipe_name(name)

        # Assert
        assert result is True

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper.settings")
    def test_is_valid_recipe_name_too_short(self, mock_settings: Mock) -> None:
        """Test recipe name validation for names that are too short."""
        # Arrange
        mock_settings.web_scraper_exclude_names = []
        mock_settings.web_scraper_nav_prefixes = []
        mock_settings.web_scraper_food_indicators = ["cake"]
        name = "Hi"

        # Act
        result = _is_valid_recipe_name(name)

        # Assert
        assert result is False

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper.settings")
    def test_is_valid_recipe_name_excluded(self, mock_settings: Mock) -> None:
        """Test recipe name validation for excluded names."""
        # Arrange
        mock_settings.web_scraper_exclude_names = ["home", "about", "contact"]
        mock_settings.web_scraper_nav_prefixes = []
        mock_settings.web_scraper_food_indicators = []
        name = "home"

        # Act
        result = _is_valid_recipe_name(name)

        # Assert
        assert result is False

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper.settings")
    def test_is_valid_recipe_name_nav_prefix(self, mock_settings: Mock) -> None:
        """Test recipe name validation for navigation prefixes."""
        # Arrange
        mock_settings.web_scraper_exclude_names = []
        mock_settings.web_scraper_nav_prefixes = ["view", "see", "browse"]
        mock_settings.web_scraper_food_indicators = []
        name = "view all recipes"

        # Act
        result = _is_valid_recipe_name(name)

        # Assert
        assert result is False

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper.settings")
    @patch("app.utils.popular_recipe_web_scraper._is_category_name")
    def test_is_valid_recipe_name_category(
        self, mock_is_category: Mock, mock_settings: Mock
    ) -> None:
        """Test recipe name validation for category names."""
        # Arrange
        mock_settings.web_scraper_exclude_names = []
        mock_settings.web_scraper_nav_prefixes = []
        mock_settings.web_scraper_food_indicators = []
        mock_is_category.return_value = True
        name = "dessert recipes"

        # Act
        result = _is_valid_recipe_name(name)

        # Assert
        assert result is False

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper.settings")
    def test_is_valid_recipe_name_no_food_indicators(self, mock_settings: Mock) -> None:
        """Test recipe name validation without food indicators."""
        # Arrange
        mock_settings.web_scraper_exclude_names = []
        mock_settings.web_scraper_nav_prefixes = []
        mock_settings.web_scraper_food_indicators = ["cake", "pasta"]
        name = "some random text"

        # Act
        result = _is_valid_recipe_name(name)

        # Assert
        assert result is False

    @pytest.mark.unit
    def test_is_valid_recipe_name_empty(self) -> None:
        """Test recipe name validation for empty names."""
        # Arrange
        name = ""

        # Act
        result = _is_valid_recipe_name(name)

        # Assert
        assert result is False

    @pytest.mark.unit
    def test_is_valid_recipe_name_unknown_recipe(self) -> None:
        """Test recipe name validation for 'Unknown Recipe'."""
        # Arrange
        name = "Unknown Recipe"

        # Act
        result = _is_valid_recipe_name(name)

        # Assert
        assert result is False


class TestIsCategoryName:
    """Unit tests for the _is_category_name function."""

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper.settings")
    def test_is_category_name_pattern_match(self, mock_settings: Mock) -> None:
        """Test category name detection with pattern matching."""
        # Arrange
        mock_settings.web_scraper_category_patterns = [r".*recipes$", r".*cooking$"]
        mock_settings.web_scraper_single_word_categories = []
        name = "dessert recipes"

        # Act
        result = _is_category_name(name)

        # Assert
        assert result is True

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper.settings")
    def test_is_category_name_single_word(self, mock_settings: Mock) -> None:
        """Test category name detection for single words."""
        # Arrange
        mock_settings.web_scraper_category_patterns = []
        mock_settings.web_scraper_single_word_categories = ["desserts", "appetizers"]
        name = "desserts"

        # Act
        result = _is_category_name(name)

        # Assert
        assert result is True

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper.settings")
    def test_is_category_name_compound_category(self, mock_settings: Mock) -> None:
        """Test category name detection for compound categories."""
        # Arrange
        mock_settings.web_scraper_category_patterns = []
        mock_settings.web_scraper_single_word_categories = ["chicken", "recipes"]
        name = "chicken recipes"

        # Act
        result = _is_category_name(name)

        # Assert
        assert result is True

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper.settings")
    def test_is_category_name_not_category(self, mock_settings: Mock) -> None:
        """Test category name detection for non-categories."""
        # Arrange
        mock_settings.web_scraper_category_patterns = []
        mock_settings.web_scraper_single_word_categories = []
        name = "chocolate cake recipe"

        # Act
        result = _is_category_name(name)

        # Assert
        assert result is False


class TestResolveUrl:
    """Unit tests for the _resolve_url function."""

    @pytest.mark.unit
    def test_resolve_url_relative_path(self) -> None:
        """Test URL resolution for relative paths."""
        # Arrange
        href = "/recipe/chocolate-cake"
        base_url = "https://example.com"

        # Act
        result = _resolve_url(href, base_url)

        # Assert
        assert result == "https://example.com/recipe/chocolate-cake"

    @pytest.mark.unit
    def test_resolve_url_absolute_url(self) -> None:
        """Test URL resolution for absolute URLs."""
        # Arrange
        href = "https://other-site.com/recipe/pasta"
        base_url = "https://example.com"

        # Act
        result = _resolve_url(href, base_url)

        # Assert
        assert result == "https://other-site.com/recipe/pasta"

    @pytest.mark.unit
    def test_resolve_url_empty_href(self) -> None:
        """Test URL resolution for empty href."""
        # Arrange
        href = ""
        base_url = "https://example.com"

        # Act
        result = _resolve_url(href, base_url)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_resolve_url_unsupported_format(self) -> None:
        """Test URL resolution for unsupported formats."""
        # Arrange
        href = "javascript:void(0)"
        base_url = "https://example.com"

        # Act
        result = _resolve_url(href, base_url)

        # Assert
        assert result is None


class TestExtractRecipeName:
    """Unit tests for the _extract_recipe_name function."""

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper._clean_recipe_name")
    def test_extract_recipe_name_from_text(self, mock_clean_name: Mock) -> None:
        """Test recipe name extraction from link text."""
        # Arrange
        html = '<a href="/recipe">Chocolate Cake</a>'
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")
        mock_clean_name.return_value = "Chocolate Cake"

        # Act
        assert link is not None
        assert isinstance(link, Tag)
        result = _extract_recipe_name(link)

        # Assert
        assert result == "Chocolate Cake"
        mock_clean_name.assert_called_once_with("Chocolate Cake")

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper._clean_recipe_name")
    def test_extract_recipe_name_from_title(self, mock_clean_name: Mock) -> None:
        """Test recipe name extraction from title attribute."""
        # Arrange
        html = '<a href="/recipe" title="Pasta Bolognese"></a>'
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")
        mock_clean_name.return_value = "Pasta Bolognese"

        # Act
        assert link is not None
        assert isinstance(link, Tag)
        result = _extract_recipe_name(link)

        # Assert
        assert result == "Pasta Bolognese"

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper._clean_recipe_name")
    def test_extract_recipe_name_from_alt(self, mock_clean_name: Mock) -> None:
        """Test recipe name extraction from alt attribute."""
        # Arrange
        html = '<a href="/recipe" alt="Fish Soup"></a>'
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")
        mock_clean_name.return_value = "Fish Soup"

        # Act
        assert link is not None
        assert isinstance(link, Tag)
        result = _extract_recipe_name(link)

        # Assert
        assert result == "Fish Soup"

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper._clean_recipe_name")
    def test_extract_recipe_name_fallback_unknown(self, mock_clean_name: Mock) -> None:
        """Test recipe name extraction fallback to Unknown Recipe."""
        # Arrange
        html = '<a href="/recipe"></a>'
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")
        mock_clean_name.return_value = "Unknown Recipe"

        # Act
        assert link is not None
        assert isinstance(link, Tag)
        result = _extract_recipe_name(link)

        # Assert
        assert result == "Unknown Recipe"

    @pytest.mark.unit
    @patch("app.utils.popular_recipe_web_scraper._clean_recipe_name")
    def test_extract_recipe_name_truncated_long_name(
        self, mock_clean_name: Mock
    ) -> None:
        """Test recipe name extraction with truncation for long names."""
        # Arrange
        html = '<a href="/recipe">Very Long Recipe Name That Should Be Truncated</a>'
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")
        long_name = "A" * 150  # Longer than 100 characters
        mock_clean_name.return_value = long_name

        # Act
        assert link is not None
        assert isinstance(link, Tag)
        result = _extract_recipe_name(link)

        # Assert
        assert len(result) == 100
        assert result == "A" * 100


class TestCleanRecipeName:
    """Unit tests for the _clean_recipe_name function."""

    @pytest.mark.unit
    def test_clean_recipe_name_remove_timing(self) -> None:
        """Test cleaning recipe name by removing timing information."""
        # Arrange
        name = "Chocolate Cake 30 mins ratings"

        # Act
        result = _clean_recipe_name(name)

        # Assert
        assert result == "Chocolate Cake"

    @pytest.mark.unit
    def test_clean_recipe_name_remove_ratings(self) -> None:
        """Test cleaning recipe name by removing ratings."""
        # Arrange
        name = "Pasta Recipe 5 ratings"

        # Act
        result = _clean_recipe_name(name)

        # Assert
        assert result == "Pasta Recipe"

    @pytest.mark.unit
    def test_clean_recipe_name_remove_extra_whitespace(self) -> None:
        """Test cleaning recipe name by removing extra whitespace."""
        # Arrange
        name = "  Soup   Recipe   "

        # Act
        result = _clean_recipe_name(name)

        # Assert
        assert result == "Soup Recipe"

    @pytest.mark.unit
    def test_clean_recipe_name_empty_string(self) -> None:
        """Test cleaning empty recipe name."""
        # Arrange
        name = ""

        # Act
        result = _clean_recipe_name(name)

        # Assert
        assert result == ""

    @pytest.mark.unit
    def test_clean_recipe_name_no_changes_needed(self) -> None:
        """Test cleaning recipe name when no changes are needed."""
        # Arrange
        name = "Simple Cake Recipe"

        # Act
        result = _clean_recipe_name(name)

        # Assert
        assert result == "Simple Cake Recipe"


class TestConstants:
    """Unit tests for module constants."""

    @pytest.mark.unit
    def test_recipe_name_length_constants(self) -> None:
        """Test that recipe name length constants are properly defined."""
        # Assert
        assert MIN_RECIPE_NAME_LENGTH == 3
        assert MIN_VALID_RECIPE_NAME_LENGTH == 5
        assert MAX_RECIPE_NAME_LENGTH == 100
        assert (
            MIN_RECIPE_NAME_LENGTH
            < MIN_VALID_RECIPE_NAME_LENGTH
            < MAX_RECIPE_NAME_LENGTH
        )
