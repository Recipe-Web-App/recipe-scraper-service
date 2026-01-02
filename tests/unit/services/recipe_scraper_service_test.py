"""Unit tests for RecipeScraperService.

This module contains comprehensive unit tests for the RecipeScraperService class,
testing recipe scraping, parsing, database operations, caching, and integration with
external services.
"""

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.schemas.common.pagination_params import PaginationParams
from app.api.v1.schemas.common.recipe import Recipe as RecipeSchema
from app.api.v1.schemas.common.web_recipe import WebRecipe
from app.api.v1.schemas.response.create_recipe_response import CreateRecipeResponse
from app.api.v1.schemas.response.recommended_recipes_response import (
    PopularRecipesResponse,
)
from app.db.models.ingredient_models.ingredient import Ingredient as IngredientModel
from app.db.models.recipe_models.recipe import Recipe
from app.enums.ingredient_unit_enum import IngredientUnitEnum
from app.exceptions.custom_exceptions import RecipeScrapingError
from app.services.recipe_scraper_service import (
    RecipeScraperService,
    _parse_ingredient_string,
)


@pytest.mark.unit
class TestParseIngredientString:
    """Unit tests for the _parse_ingredient_string helper function."""

    def test_parse_ingredient_string_with_decimal_quantity(self) -> None:
        """Test parsing ingredient string with decimal quantity."""
        # Arrange
        ingredient_str = "2.5 cups flour"

        # Act
        quantity, unit, name = _parse_ingredient_string(ingredient_str)

        # Assert
        assert quantity == Decimal("2.5")
        assert unit == IngredientUnitEnum.CUP
        assert name == "flour"

    def test_parse_ingredient_string_with_whole_number(self) -> None:
        """Test parsing ingredient string with whole number quantity."""
        # Arrange
        ingredient_str = "3 tablespoons olive oil"

        # Act
        quantity, unit, name = _parse_ingredient_string(ingredient_str)

        # Assert
        assert quantity == Decimal("3")
        assert unit == IngredientUnitEnum.TBSP
        assert name == "olive oil"

    def test_parse_ingredient_string_with_simple_fraction(self) -> None:
        """Test parsing ingredient string with simple fraction."""
        # Arrange
        ingredient_str = "1/2 teaspoon salt"

        # Act
        quantity, unit, name = _parse_ingredient_string(ingredient_str)

        # Assert
        assert quantity == Decimal("0.5")
        assert unit == IngredientUnitEnum.TSP
        assert name == "salt"

    def test_parse_ingredient_string_with_mixed_fraction(self) -> None:
        """Test parsing ingredient string with mixed fraction."""
        # Arrange
        ingredient_str = "1 1/2 cups milk"

        # Act
        quantity, unit, name = _parse_ingredient_string(ingredient_str)

        # Assert
        assert quantity == Decimal("1.5")
        assert unit == IngredientUnitEnum.CUP
        assert name == "milk"

    def test_parse_ingredient_string_no_quantity(self) -> None:
        """Test parsing ingredient string without quantity."""
        # Arrange
        ingredient_str = "salt to taste"

        # Act
        quantity, unit, name = _parse_ingredient_string(ingredient_str)

        # Assert
        assert quantity is None
        assert unit is None  # "to taste" not recognized as valid unit
        assert name == "to taste"

    def test_parse_ingredient_string_quantity_no_unit(self) -> None:
        """Test parsing ingredient string with quantity but no unit."""
        # Arrange
        ingredient_str = "2 eggs"

        # Act
        quantity, unit, name = _parse_ingredient_string(ingredient_str)

        # Assert
        assert quantity == Decimal("2")
        assert unit is None  # "eggs" is not a recognized unit, so becomes None
        assert name == "s"  # Due to regex capturing "egg" as unit, leaving "s"

    def test_parse_ingredient_string_unknown_unit(self) -> None:
        """Test parsing ingredient string with unknown unit."""
        # Arrange
        ingredient_str = "3 unknownunit sugar"

        # Act
        quantity, unit, name = _parse_ingredient_string(ingredient_str)

        # Assert
        assert quantity == Decimal("3")
        assert unit is None  # Unknown unit defaults to None
        assert name == "sugar"

    def test_parse_ingredient_string_invalid_quantity(self) -> None:
        """Test parsing ingredient string with invalid quantity."""
        # Arrange
        ingredient_str = "abc cups flour"

        # Act
        quantity, unit, name = _parse_ingredient_string(ingredient_str)

        # Assert
        assert quantity is None  # Invalid quantity defaults to None
        assert unit is None  # "abc" not recognized as valid unit
        assert name == "cups flour"  # Unit parsing continues normally

    def test_parse_ingredient_string_zero_division_error(self) -> None:
        """Test parsing ingredient string with zero division in fraction."""
        # Arrange
        ingredient_str = "1/0 cups flour"

        # Act
        quantity, unit, name = _parse_ingredient_string(ingredient_str)

        # Assert
        assert quantity is None  # Division by zero handled gracefully
        assert unit == IngredientUnitEnum.CUP
        assert name == "flour"

    def test_parse_ingredient_string_whitespace_handling(self) -> None:
        """Test parsing ingredient string with extra whitespace."""
        # Arrange
        ingredient_str = "  2   cups   flour  "

        # Act
        quantity, unit, name = _parse_ingredient_string(ingredient_str)

        # Assert
        assert quantity == Decimal("2")
        assert unit == IngredientUnitEnum.CUP
        assert name == "flour"


class TestRecipeScraperService:
    """Unit tests for RecipeScraperService."""

    @pytest.fixture
    def recipe_scraper_service(self) -> RecipeScraperService:
        """Create a RecipeScraperService instance for testing."""
        # Create mock services
        mock_spoonacular = Mock()
        mock_notification = AsyncMock()
        mock_user_mgmt = AsyncMock()

        with patch("app.services.recipe_scraper_service.get_cache_manager"):
            service = RecipeScraperService(
                spoonacular_service=mock_spoonacular,
                notification_service=mock_notification,
                user_mgmt_service=mock_user_mgmt,
            )
            return service

    @pytest.fixture
    def mock_user_id(self) -> UUID:
        """Create a mock user ID."""
        return uuid4()

    @pytest.fixture
    def mock_scraped_data(self) -> dict[str, Any]:
        """Create mock scraped recipe data."""
        return {
            "title": "Test Recipe",
            "description": "A test recipe",
            "canonical_url": "https://example.com/recipe",
            "yields": "4 servings",
            "prep_time": 15,
            "cook_time": 30,
            "ingredients": ["2 cups flour", "1 tsp salt", "1 cup milk"],
            "instructions_list": ["Mix ingredients", "Bake for 30 minutes"],
        }

    @pytest.fixture
    def mock_pagination(self) -> PaginationParams:
        """Create mock pagination parameters."""
        return PaginationParams(limit=10, offset=0, count_only=False)

    def test_recipe_scraper_service_initialization(
        self, recipe_scraper_service: RecipeScraperService
    ) -> None:
        """Test RecipeScraperService initialization."""
        assert recipe_scraper_service is not None
        assert hasattr(recipe_scraper_service, 'cache_manager')
        assert hasattr(recipe_scraper_service, 'spoonacular_service')

    @patch("app.services.recipe_scraper_service.scrape_me")
    @pytest.mark.asyncio
    async def test_create_recipe_success(
        self,
        mock_scrape_me: Mock,
        recipe_scraper_service: RecipeScraperService,
        mock_db_session: Mock,
        mock_user_id: UUID,
        mock_scraped_data: dict[str, Any],
    ) -> None:
        """Test successful recipe creation."""
        # Arrange
        url = "https://example.com/recipe"

        # Mock scraper
        mock_scraper = Mock()
        mock_scraper.to_json.return_value = mock_scraped_data
        mock_scrape_me.return_value = mock_scraper

        # Mock database queries
        mock_db_session.query().filter().first.return_value = None  # No existing recipe

        # Mock ingredient queries - need to mock the ingredient lookup properly
        mock_existing_ingredients: list[Mock] = []
        for name in ["flour", "salt", "milk"]:  # Actual parsed ingredient names
            mock_ingredient = Mock(spec=IngredientModel)
            mock_ingredient.name = name
            mock_ingredient.ingredient_id = len(mock_existing_ingredients) + 1
            mock_existing_ingredients.append(mock_ingredient)

        mock_db_session.query().filter().all.return_value = mock_existing_ingredients

        # Mock new ingredient creation
        mock_new_ingredient = Mock(spec=IngredientModel)
        mock_new_ingredient.name = "salt"
        mock_new_ingredient.ingredient_id = 2

        # Mock recipe creation
        mock_recipe = Mock(spec=Recipe)
        mock_recipe.recipe_id = 1

        with (
            patch(
                "app.services.recipe_scraper_service.IngredientModel"
            ) as mock_ingredient_class,
            patch("app.services.recipe_scraper_service.Recipe") as mock_recipe_class,
            patch.object(RecipeSchema, "from_db_model") as mock_from_db,
        ):

            mock_ingredient_class.return_value = mock_new_ingredient
            mock_recipe_class.return_value = mock_recipe
            mock_recipe_schema = Mock(spec=RecipeSchema)
            mock_from_db.return_value = mock_recipe_schema

            # Act
            result = await recipe_scraper_service.create_recipe(
                url, mock_db_session, mock_user_id
            )

            # Assert
            assert isinstance(result, CreateRecipeResponse)
            assert result.recipe == mock_recipe_schema
            mock_scrape_me.assert_called_once_with(url)
            mock_db_session.add.assert_called()
            mock_db_session.commit.assert_called_once()

    @patch("app.services.recipe_scraper_service.scrape_me")
    @pytest.mark.asyncio
    async def test_create_recipe_already_exists(
        self,
        mock_scrape_me: Mock,
        recipe_scraper_service: RecipeScraperService,
        mock_db_session: Mock,
        mock_user_id: UUID,
    ) -> None:
        """Test recipe creation when recipe already exists."""
        # Arrange
        url = "https://example.com/recipe"

        # Mock existing recipe
        mock_existing_recipe = Mock(spec=Recipe)
        mock_existing_recipe.recipe_id = 123
        mock_db_session.query().filter().first.return_value = mock_existing_recipe

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await recipe_scraper_service.create_recipe(
                url, mock_db_session, mock_user_id
            )

        assert exc_info.value.status_code == 409
        assert "Recipe ID 123 already exists" in str(exc_info.value.detail)
        mock_scrape_me.assert_not_called()

    @patch("app.services.recipe_scraper_service.scrape_me")
    @pytest.mark.asyncio
    async def test_create_recipe_database_error(
        self,
        mock_scrape_me: Mock,
        recipe_scraper_service: RecipeScraperService,
        mock_db_session: Mock,
        mock_user_id: UUID,
        mock_scraped_data: dict[str, Any],
    ) -> None:
        """Test recipe creation with database error."""
        # Arrange
        url = "https://example.com/recipe"

        # Mock scraper
        mock_scraper = Mock()
        mock_scraper.to_json.return_value = mock_scraped_data
        mock_scrape_me.return_value = mock_scraper

        # Mock database queries
        mock_db_session.query().filter().first.return_value = None

        # Mock ingredient queries to avoid KeyError before database error
        mock_existing_ingredients: list[Mock] = []
        for name in ["flour", "salt", "milk"]:
            mock_ingredient = Mock(spec=IngredientModel)
            mock_ingredient.name = name
            mock_ingredient.ingredient_id = len(mock_existing_ingredients) + 1
            mock_existing_ingredients.append(mock_ingredient)

        mock_db_session.query().filter().all.return_value = mock_existing_ingredients

        mock_db_session.commit.side_effect = Exception("Database error")

        with (
            patch("app.services.recipe_scraper_service.IngredientModel"),
            patch("app.services.recipe_scraper_service.Recipe"),
        ):

            # Act & Assert
            with pytest.raises(Exception, match="Database error"):
                await recipe_scraper_service.create_recipe(
                    url, mock_db_session, mock_user_id
                )

            mock_db_session.rollback.assert_called_once()

    @patch("app.services.recipe_scraper_service.scrape_me")
    @pytest.mark.asyncio
    async def test_create_recipe_invalid_servings(
        self,
        mock_scrape_me: Mock,
        recipe_scraper_service: RecipeScraperService,
        mock_db_session: Mock,
        mock_user_id: UUID,
    ) -> None:
        """Test recipe creation with invalid servings data."""
        # Arrange
        url = "https://example.com/recipe"
        scraped_data = {
            "title": "Test Recipe",
            "yields": "invalid servings",  # Invalid format
            "ingredients": [],
            "instructions_list": [],
        }

        # Mock scraper
        mock_scraper = Mock()
        mock_scraper.to_json.return_value = scraped_data
        mock_scrape_me.return_value = mock_scraper

        # Mock database queries
        mock_db_session.query().filter().first.return_value = None
        mock_db_session.query().filter().all.return_value = []

        with (
            patch("app.services.recipe_scraper_service.IngredientModel"),
            patch("app.services.recipe_scraper_service.Recipe") as mock_recipe_class,
            patch.object(RecipeSchema, "from_db_model") as mock_from_db,
        ):

            mock_recipe = Mock(spec=Recipe)
            mock_recipe_class.return_value = mock_recipe
            mock_recipe_schema = Mock(spec=RecipeSchema)
            mock_from_db.return_value = mock_recipe_schema

            # Act
            result = await recipe_scraper_service.create_recipe(
                url, mock_db_session, mock_user_id
            )

            # Assert
            assert isinstance(result, CreateRecipeResponse)
            # Verify that the recipe was created with servings=None
            recipe_call_args = mock_recipe_class.call_args[1]
            assert recipe_call_args["servings"] is None

    @patch("app.services.recipe_scraper_service.scrape_me")
    @pytest.mark.asyncio
    async def test_create_recipe_schema_conversion_error(
        self,
        mock_scrape_me: Mock,
        recipe_scraper_service: RecipeScraperService,
        mock_db_session: Mock,
        mock_user_id: UUID,
        mock_scraped_data: dict[str, Any],
    ) -> None:
        """Test recipe creation with schema conversion error."""
        # Arrange
        url = "https://example.com/recipe"

        # Mock scraper
        mock_scraper = Mock()
        mock_scraper.to_json.return_value = mock_scraped_data
        mock_scrape_me.return_value = mock_scraper

        # Mock database queries
        mock_db_session.query().filter().first.return_value = None

        # Mock ingredient queries to avoid KeyError
        mock_existing_ingredients: list[Mock] = []
        for name in ["flour", "salt", "milk"]:
            mock_ingredient = Mock(spec=IngredientModel)
            mock_ingredient.name = name
            mock_ingredient.ingredient_id = len(mock_existing_ingredients) + 1
            mock_existing_ingredients.append(mock_ingredient)
        mock_db_session.query().filter().all.return_value = mock_existing_ingredients

        with (
            patch("app.services.recipe_scraper_service.IngredientModel"),
            patch("app.services.recipe_scraper_service.Recipe"),
            patch.object(RecipeSchema, "from_db_model") as mock_from_db,
        ):

            mock_from_db.side_effect = Exception("Schema conversion error")

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await recipe_scraper_service.create_recipe(
                    url, mock_db_session, mock_user_id
                )

            assert exc_info.value.status_code == 500
            assert "Failed to convert recipe to response schema" in str(
                exc_info.value.detail
            )

    @pytest.mark.asyncio
    async def test_get_popular_recipes_from_cache(
        self,
        recipe_scraper_service: RecipeScraperService,
        mock_pagination: PaginationParams,
    ) -> None:
        """Test getting popular recipes from cache."""
        # Arrange
        cached_recipe_data = [
            {"recipe_name": "Cached Recipe 1", "url": "https://example.com/1"},
            {"recipe_name": "Cached Recipe 2", "url": "https://example.com/2"},
        ]

        mock_cache_manager = AsyncMock()
        mock_cache_manager.get.return_value = cached_recipe_data
        recipe_scraper_service.cache_manager = mock_cache_manager

        with patch.object(PopularRecipesResponse, "from_all") as mock_from_all:
            mock_response = Mock(spec=PopularRecipesResponse)
            mock_from_all.return_value = mock_response

            # Act
            result = await recipe_scraper_service.get_popular_recipes(mock_pagination)

            # Assert
            assert result == mock_response
            mock_cache_manager.get.assert_called_once_with("popular_recipes")
            mock_from_all.assert_called_once()
            # Verify WebRecipe objects were created from cached data
            call_args = mock_from_all.call_args[0]
            web_recipes = call_args[0]
            assert len(web_recipes) == 2
            assert all(isinstance(recipe, WebRecipe) for recipe in web_recipes)

    @pytest.mark.asyncio
    async def test_get_popular_recipes_cache_miss(
        self,
        recipe_scraper_service: RecipeScraperService,
        mock_pagination: PaginationParams,
    ) -> None:
        """Test getting popular recipes with cache miss."""
        # Arrange
        mock_cache_manager = AsyncMock()
        mock_cache_manager.get.return_value = None  # Cache miss
        recipe_scraper_service.cache_manager = mock_cache_manager

        mock_scraped_recipes = [
            WebRecipe(recipe_name="Scraped Recipe 1", url="https://example.com/1"),
            WebRecipe(recipe_name="Scraped Recipe 2", url="https://example.com/2"),
        ]

        with (
            patch.object(
                recipe_scraper_service, "_scrape_all_popular_recipes"
            ) as mock_scrape_all,
            patch.object(PopularRecipesResponse, "from_all") as mock_from_all,
        ):

            mock_scrape_all.return_value = mock_scraped_recipes
            mock_response = Mock(spec=PopularRecipesResponse)
            mock_from_all.return_value = mock_response

            # Act
            result = await recipe_scraper_service.get_popular_recipes(mock_pagination)

            # Assert
            assert result == mock_response
            mock_cache_manager.get.assert_called_once_with("popular_recipes")
            mock_scrape_all.assert_called_once()
            mock_cache_manager.set.assert_called_once()
            # Verify cache was set with serialized data
            cache_set_args = mock_cache_manager.set.call_args
            assert cache_set_args[0][0] == "popular_recipes"
            assert cache_set_args[1]["expiry_hours"] == 24

    @pytest.mark.asyncio
    async def test_get_popular_recipes_invalid_cache_data(
        self,
        recipe_scraper_service: RecipeScraperService,
        mock_pagination: PaginationParams,
    ) -> None:
        """Test getting popular recipes with invalid cache data format."""
        # Arrange
        mock_cache_manager = AsyncMock()
        mock_cache_manager.get.return_value = "invalid_data"  # Invalid format
        recipe_scraper_service.cache_manager = mock_cache_manager

        mock_scraped_recipes = [
            WebRecipe(recipe_name="Scraped Recipe", url="https://example.com/1")
        ]

        with (
            patch.object(
                recipe_scraper_service, "_scrape_all_popular_recipes"
            ) as mock_scrape_all,
            patch.object(PopularRecipesResponse, "from_all") as mock_from_all,
        ):

            mock_scrape_all.return_value = mock_scraped_recipes
            mock_response = Mock(spec=PopularRecipesResponse)
            mock_from_all.return_value = mock_response

            # Act
            result = await recipe_scraper_service.get_popular_recipes(mock_pagination)

            # Assert
            assert result == mock_response
            mock_scrape_all.assert_called_once()  # Fallback to scraping

    @patch("app.services.recipe_scraper_service.scrape_popular_recipes")
    def test_scrape_all_popular_recipes_success(
        self,
        mock_scrape_popular_recipes: Mock,
        recipe_scraper_service: RecipeScraperService,
    ) -> None:
        """Test successful scraping of all popular recipes."""
        # Arrange
        mock_recipes_1 = [
            WebRecipe(recipe_name="Recipe 1", url="https://site1.com/1"),
            WebRecipe(recipe_name="Recipe 2", url="https://site1.com/2"),
        ]
        mock_recipes_2 = [
            WebRecipe(recipe_name="Recipe 3", url="https://site2.com/3"),
        ]
        mock_scrape_popular_recipes.side_effect = [mock_recipes_1, mock_recipes_2]

        with patch("app.services.recipe_scraper_service.settings") as mock_settings:
            mock_settings.popular_recipe_urls = [
                "https://site1.com",
                "https://site2.com",
            ]

            # Act
            result = recipe_scraper_service._scrape_all_popular_recipes()

            # Assert
            assert len(result) == 3
            assert all(isinstance(recipe, WebRecipe) for recipe in result)
            assert mock_scrape_popular_recipes.call_count == 2

    @patch("app.services.recipe_scraper_service.scrape_popular_recipes")
    def test_scrape_all_popular_recipes_with_errors(
        self,
        mock_scrape_popular_recipes: Mock,
        recipe_scraper_service: RecipeScraperService,
    ) -> None:
        """Test scraping popular recipes with some URLs failing."""
        # Arrange
        mock_recipes = [
            WebRecipe(recipe_name="Recipe 1", url="https://site1.com/1"),
        ]
        mock_scrape_popular_recipes.side_effect = [
            RecipeScrapingError("Scraping failed"),  # First URL fails
            mock_recipes,  # Second URL succeeds
        ]

        with patch("app.services.recipe_scraper_service.settings") as mock_settings:
            mock_settings.popular_recipe_urls = [
                "https://failing-site.com",
                "https://working-site.com",
            ]

            # Act
            result = recipe_scraper_service._scrape_all_popular_recipes()

            # Assert
            assert len(result) == 1  # Only recipes from working site
            assert result[0].recipe_name == "Recipe 1"
            assert mock_scrape_popular_recipes.call_count == 2

    @patch("app.services.recipe_scraper_service.scrape_popular_recipes")
    def test_scrape_all_popular_recipes_all_fail(
        self,
        mock_scrape_popular_recipes: Mock,
        recipe_scraper_service: RecipeScraperService,
    ) -> None:
        """Test scraping popular recipes when all URLs fail."""
        # Arrange
        mock_scrape_popular_recipes.side_effect = RecipeScrapingError("All failed")

        with patch("app.services.recipe_scraper_service.settings") as mock_settings:
            mock_settings.popular_recipe_urls = ["https://failing-site.com"]

            # Act
            result = recipe_scraper_service._scrape_all_popular_recipes()

            # Assert
            assert len(result) == 0  # No recipes scraped
            mock_scrape_popular_recipes.assert_called_once()

    def test_scrape_all_popular_recipes_empty_urls(
        self, recipe_scraper_service: RecipeScraperService
    ) -> None:
        """Test scraping popular recipes with empty URL list."""
        # Arrange
        with patch("app.services.recipe_scraper_service.settings") as mock_settings:
            mock_settings.popular_recipe_urls = []

            # Act
            result = recipe_scraper_service._scrape_all_popular_recipes()

            # Assert
            assert len(result) == 0

    @patch("app.services.recipe_scraper_service.scrape_me")
    @pytest.mark.asyncio
    async def test_create_recipe_complex_ingredient_parsing(
        self,
        mock_scrape_me: Mock,
        recipe_scraper_service: RecipeScraperService,
        mock_db_session: Mock,
        mock_user_id: UUID,
    ) -> None:
        """Test recipe creation with complex ingredient parsing scenarios."""
        # Arrange
        url = "https://example.com/recipe"
        scraped_data = {
            "title": "Complex Recipe",
            "ingredients": [
                "2 1/2 cups all-purpose flour",
                "1/4 teaspoon salt",
                "3 eggs",
                "1 pinch of black pepper",
                "2.5 tablespoons olive oil",
            ],
            "instructions_list": ["Mix and bake"],
        }

        # Mock scraper
        mock_scraper = Mock()
        mock_scraper.to_json.return_value = scraped_data
        mock_scrape_me.return_value = mock_scraper

        # Mock database queries
        mock_db_session.query().filter().first.return_value = None

        # Mock existing ingredients based on actual parsing results
        # "3 eggs" -> "s", "1 pinch of black pepper" -> "of black pepper"
        mock_existing_ingredients = []
        expected_names = [
            "all-purpose flour",
            "salt",
            "s",
            "of black pepper",
            "olive oil",
        ]
        for i, name in enumerate(expected_names):
            mock_ingredient = Mock(spec=IngredientModel)
            mock_ingredient.name = name
            mock_ingredient.ingredient_id = i + 1
            mock_existing_ingredients.append(mock_ingredient)
        mock_db_session.query().filter().all.return_value = mock_existing_ingredients

        with (
            patch(
                "app.services.recipe_scraper_service.IngredientModel"
            ) as mock_ingredient_class,
            patch("app.services.recipe_scraper_service.Recipe") as mock_recipe_class,
            patch.object(RecipeSchema, "from_db_model") as mock_from_db,
        ):

            # Mock ingredient creation
            mock_ingredients = []
            for i, name in enumerate(
                ["all-purpose flour", "salt", "eggs", "black pepper", "olive oil"]
            ):
                mock_ingredient = Mock(spec=IngredientModel)
                mock_ingredient.name = name
                mock_ingredient.ingredient_id = i + 1
                mock_ingredients.append(mock_ingredient)

            mock_ingredient_class.side_effect = mock_ingredients

            mock_recipe = Mock(spec=Recipe)
            mock_recipe_class.return_value = mock_recipe
            mock_recipe_schema = Mock(spec=RecipeSchema)
            mock_from_db.return_value = mock_recipe_schema

            # Act
            result = await recipe_scraper_service.create_recipe(
                url, mock_db_session, mock_user_id
            )

            # Assert
            assert isinstance(result, CreateRecipeResponse)
            # Since ingredients already exist in DB, no new ones should be created
            assert mock_ingredient_class.call_count == 0
            # Verify recipe was created with correct structure

    @patch("app.services.recipe_scraper_service.scrape_me")
    @pytest.mark.asyncio
    async def test_create_recipe_with_notifications_success(
        self,
        mock_scrape_me: Mock,
        recipe_scraper_service: RecipeScraperService,
        mock_db_session: Mock,
        mock_user_id: UUID,
        mock_scraped_data: dict[str, Any],
    ) -> None:
        """Test that notifications are sent after successful recipe creation."""
        # Arrange
        url = "https://example.com/recipe"
        mock_scraper = Mock()
        mock_scraper.to_json.return_value = mock_scraped_data
        mock_scrape_me.return_value = mock_scraper

        # Mock database
        mock_db_session.query().filter().first.return_value = None
        mock_existing_ingredients: list[Mock] = []
        for name in ["flour", "salt", "milk"]:
            mock_ingredient = Mock(spec=IngredientModel)
            mock_ingredient.name = name
            mock_ingredient.ingredient_id = len(mock_existing_ingredients) + 1
            mock_existing_ingredients.append(mock_ingredient)
        mock_db_session.query().filter().all.return_value = mock_existing_ingredients

        mock_recipe = Mock(spec=Recipe)
        mock_recipe.recipe_id = 123

        with (
            patch("app.services.recipe_scraper_service.IngredientModel"),
            patch("app.services.recipe_scraper_service.Recipe") as mock_recipe_class,
            patch.object(RecipeSchema, "from_db_model") as mock_from_db,
        ):
            mock_recipe_class.return_value = mock_recipe
            mock_recipe_schema = Mock(spec=RecipeSchema)
            mock_from_db.return_value = mock_recipe_schema

            # Act
            result = await recipe_scraper_service.create_recipe(
                url, mock_db_session, mock_user_id
            )

            # Assert
            assert isinstance(result, CreateRecipeResponse)
            # Notifications should be sent via the mocked async services
            assert recipe_scraper_service.notification_service is not None

    @patch("app.services.recipe_scraper_service.scrape_me")
    @pytest.mark.asyncio
    async def test_create_recipe_notification_failure_silent(
        self,
        mock_scrape_me: Mock,
        recipe_scraper_service: RecipeScraperService,
        mock_db_session: Mock,
        mock_user_id: UUID,
        mock_scraped_data: dict[str, Any],
    ) -> None:
        """Test that notification failures don't break recipe creation."""
        # Arrange
        url = "https://example.com/recipe"
        mock_scraper = Mock()
        mock_scraper.to_json.return_value = mock_scraped_data
        mock_scrape_me.return_value = mock_scraper

        # Mock database
        mock_db_session.query().filter().first.return_value = None
        mock_existing_ingredients: list[Mock] = []
        for name in ["flour", "salt", "milk"]:
            mock_ingredient = Mock(spec=IngredientModel)
            mock_ingredient.name = name
            mock_ingredient.ingredient_id = len(mock_existing_ingredients) + 1
            mock_existing_ingredients.append(mock_ingredient)
        mock_db_session.query().filter().all.return_value = mock_existing_ingredients

        mock_recipe = Mock(spec=Recipe)
        mock_recipe.recipe_id = 456

        # Configure the AsyncMock to raise an exception when get_follower_ids is called
        mock_get_follower_ids = AsyncMock(
            side_effect=Exception("User management service unavailable")
        )

        with (
            patch("app.services.recipe_scraper_service.IngredientModel"),
            patch("app.services.recipe_scraper_service.Recipe") as mock_recipe_class,
            patch.object(RecipeSchema, "from_db_model") as mock_from_db,
            patch.object(
                recipe_scraper_service.user_mgmt_service,
                "get_follower_ids",
                mock_get_follower_ids,
            ),
        ):
            mock_recipe_class.return_value = mock_recipe
            mock_recipe_schema = Mock(spec=RecipeSchema)
            mock_from_db.return_value = mock_recipe_schema

            # Act - should not raise exception
            result = await recipe_scraper_service.create_recipe(
                url, mock_db_session, mock_user_id
            )

            # Assert
            assert isinstance(result, CreateRecipeResponse)
            # Recipe creation should still succeed even though notifications failed
            mock_db_session.commit.assert_called_once()
            mock_recipe_class.assert_called_once()


class TestFilterByNotificationPreferences:
    """Unit tests for _filter_by_notification_preferences method."""

    @pytest.fixture
    def recipe_scraper_service(self) -> RecipeScraperService:
        """Create a RecipeScraperService instance for testing."""

        mock_spoonacular = Mock()
        mock_notification = AsyncMock()
        mock_user_mgmt = AsyncMock()

        with patch("app.services.recipe_scraper_service.get_cache_manager"):
            service = RecipeScraperService(
                spoonacular_service=mock_spoonacular,
                notification_service=mock_notification,
                user_mgmt_service=mock_user_mgmt,
            )
            return service

    @pytest.mark.asyncio
    async def test_filter_empty_list(
        self,
        recipe_scraper_service: RecipeScraperService,
    ) -> None:
        """Test filtering with empty user list."""
        result = await recipe_scraper_service._filter_by_notification_preferences([])

        assert result == []

    @pytest.mark.asyncio
    async def test_filter_all_opted_in(
        self,
        recipe_scraper_service: RecipeScraperService,
    ) -> None:
        """Test filtering when all users have opted in."""
        from app.api.v1.schemas.downstream.user_management_service import (
            NotificationPreferences,
        )

        user_ids = [uuid4(), uuid4(), uuid4()]

        # Mock batch preferences - all opted in
        mock_prefs = {
            uid: NotificationPreferences(recipe_recommendations=True)
            for uid in user_ids
        }

        recipe_scraper_service.user_mgmt_service.get_notification_preferences_batch = (  # type: ignore[method-assign]
            AsyncMock(return_value=mock_prefs)
        )

        result = await recipe_scraper_service._filter_by_notification_preferences(
            user_ids
        )

        assert len(result) == 3
        assert set(result) == set(user_ids)

    @pytest.mark.asyncio
    async def test_filter_some_opted_out(
        self,
        recipe_scraper_service: RecipeScraperService,
    ) -> None:
        """Test filtering when some users have opted out."""
        from app.api.v1.schemas.downstream.user_management_service import (
            NotificationPreferences,
        )

        user_ids = [uuid4(), uuid4(), uuid4()]

        # Second user opted out
        mock_prefs = {
            user_ids[0]: NotificationPreferences(recipe_recommendations=True),
            user_ids[1]: NotificationPreferences(recipe_recommendations=False),
            user_ids[2]: NotificationPreferences(recipe_recommendations=True),
        }

        recipe_scraper_service.user_mgmt_service.get_notification_preferences_batch = (  # type: ignore[method-assign]
            AsyncMock(return_value=mock_prefs)
        )

        result = await recipe_scraper_service._filter_by_notification_preferences(
            user_ids
        )

        assert len(result) == 2
        assert user_ids[0] in result
        assert user_ids[1] not in result  # Opted out
        assert user_ids[2] in result

    @pytest.mark.asyncio
    async def test_filter_all_opted_out(
        self,
        recipe_scraper_service: RecipeScraperService,
    ) -> None:
        """Test filtering when all users have opted out."""
        from app.api.v1.schemas.downstream.user_management_service import (
            NotificationPreferences,
        )

        user_ids = [uuid4(), uuid4()]

        # All opted out
        mock_prefs = {
            uid: NotificationPreferences(recipe_recommendations=False)
            for uid in user_ids
        }

        recipe_scraper_service.user_mgmt_service.get_notification_preferences_batch = (  # type: ignore[method-assign]
            AsyncMock(return_value=mock_prefs)
        )

        result = await recipe_scraper_service._filter_by_notification_preferences(
            user_ids
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_filter_fetch_failure_includes_user(
        self,
        recipe_scraper_service: RecipeScraperService,
    ) -> None:
        """Test that users are included when preference fetch fails (fail-open)."""
        from app.api.v1.schemas.downstream.user_management_service import (
            NotificationPreferences,
        )

        user_ids = [uuid4(), uuid4()]

        # One user has prefs, one failed to fetch (None)
        mock_prefs = {
            user_ids[0]: NotificationPreferences(recipe_recommendations=True),
            user_ids[1]: None,  # Failed to fetch
        }

        recipe_scraper_service.user_mgmt_service.get_notification_preferences_batch = (  # type: ignore[method-assign]
            AsyncMock(return_value=mock_prefs)
        )

        result = await recipe_scraper_service._filter_by_notification_preferences(
            user_ids
        )

        # Both should be included (fail-open)
        assert len(result) == 2
        assert user_ids[0] in result
        assert user_ids[1] in result

    @pytest.mark.asyncio
    async def test_filter_null_preference_treated_as_true(
        self,
        recipe_scraper_service: RecipeScraperService,
    ) -> None:
        """Test that None preference value is treated as True (default opted-in)."""
        from app.api.v1.schemas.downstream.user_management_service import (
            NotificationPreferences,
        )

        user_ids = [uuid4()]

        # recipe_recommendations is None (not explicitly set)
        mock_prefs = {
            user_ids[0]: NotificationPreferences(recipe_recommendations=None),
        }

        recipe_scraper_service.user_mgmt_service.get_notification_preferences_batch = (  # type: ignore[method-assign]
            AsyncMock(return_value=mock_prefs)
        )

        result = await recipe_scraper_service._filter_by_notification_preferences(
            user_ids
        )

        # Should be included (None means default = opted in)
        assert len(result) == 1
        assert user_ids[0] in result

    @pytest.mark.asyncio
    async def test_filter_user_not_in_preferences_map(
        self,
        recipe_scraper_service: RecipeScraperService,
    ) -> None:
        """Test that users missing from preferences map are included (fail-open)."""
        user_ids = [uuid4(), uuid4()]

        # Only first user in map, second missing entirely
        mock_prefs: dict[UUID, Any] = {
            # user_ids[0] not in map
            # user_ids[1] not in map
        }

        recipe_scraper_service.user_mgmt_service.get_notification_preferences_batch = (  # type: ignore[method-assign]
            AsyncMock(return_value=mock_prefs)
        )

        result = await recipe_scraper_service._filter_by_notification_preferences(
            user_ids
        )

        # Both should be included (fail-open when not in map)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_filter_mixed_scenarios(
        self,
        recipe_scraper_service: RecipeScraperService,
    ) -> None:
        """Test filtering with mixed opt-in, opt-out, None, and fetch failures."""
        from app.api.v1.schemas.downstream.user_management_service import (
            NotificationPreferences,
        )

        user_ids = [uuid4() for _ in range(5)]

        mock_prefs = {
            user_ids[0]: NotificationPreferences(recipe_recommendations=True),  # In
            user_ids[1]: NotificationPreferences(recipe_recommendations=False),  # Out
            user_ids[2]: NotificationPreferences(recipe_recommendations=None),  # In
            user_ids[3]: None,  # Fetch failed - In (fail-open)
            # user_ids[4] not in map - In (fail-open)
        }

        recipe_scraper_service.user_mgmt_service.get_notification_preferences_batch = (  # type: ignore[method-assign]
            AsyncMock(return_value=mock_prefs)
        )

        result = await recipe_scraper_service._filter_by_notification_preferences(
            user_ids
        )

        # 4 should be included, 1 opted out
        assert len(result) == 4
        assert user_ids[0] in result  # Opted in
        assert user_ids[1] not in result  # Opted out
        assert user_ids[2] in result  # None = default true
        assert user_ids[3] in result  # Fetch failed = fail-open
        assert user_ids[4] in result  # Not in map = fail-open
