"""Unit tests for the SpoonacularService class."""

from typing import Any
from unittest.mock import Mock, patch

import httpx
import pytest
from fastapi import HTTPException

from app.api.v1.schemas.common.web_recipe import WebRecipe
from app.api.v1.schemas.response.recommended_substitutions_response import (
    ConversionRatio,
    IngredientSubstitution,
)
from app.enums.ingredient_unit_enum import IngredientUnitEnum
from app.exceptions.custom_exceptions import SubstitutionNotFoundError
from app.services.downstream.spoonacular_service import SpoonacularService


@pytest.mark.unit
class TestSpoonacularService:
    @pytest.fixture
    def spoonacular_service(self) -> SpoonacularService:
        """Create SpoonacularService instance for testing."""
        return SpoonacularService()

    def test_init_sets_correct_attributes(self) -> None:
        """Test that SpoonacularService initializes with correct attributes."""
        # Act
        service = SpoonacularService()

        # Assert
        assert service.api_key is not None
        assert service.base_url == "https://api.spoonacular.com"
        assert hasattr(service, "client")
        assert isinstance(service.client, httpx.Client)

    @patch("httpx.Client.get")
    def test_get_ingredient_substitutes_success(
        self,
        mock_get: Mock,
        spoonacular_service: SpoonacularService,
        mock_spoonacular_substitutes_response: dict[str, Any],
    ) -> None:
        """Test successful ingredient substitutes retrieval."""
        # Arrange
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_spoonacular_substitutes_response
        mock_get.return_value = mock_response

        # Act
        result = spoonacular_service.get_ingredient_substitutes("cheddar cheese")

        # Assert
        assert len(result) == 3
        assert result[0]["substitute_ingredient"] == "American Cheese"
        assert result[0]["conversion_ratio"]["ratio"] == 1.0
        assert result[0]["confidence_score"] == 0.8

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "food/ingredients/substitutes" in call_args[0][0]
        assert call_args[1]["params"]["ingredientName"] == "cheddar cheese"

    @patch("httpx.Client.get")
    def test_get_ingredient_substitutes_failure_response(
        self,
        mock_get: Mock,
        spoonacular_service: SpoonacularService,
        mock_spoonacular_substitutes_response_failure: dict[str, Any],
    ) -> None:
        """Test handling of failure response from Spoonacular."""
        # Arrange
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_spoonacular_substitutes_response_failure
        mock_get.return_value = mock_response

        # Act & Assert
        with pytest.raises(SubstitutionNotFoundError) as exc_info:
            spoonacular_service.get_ingredient_substitutes("unknown ingredient")

        assert "No substitutes found for this ingredient" in str(exc_info.value)

    @patch("httpx.Client.get")
    def test_get_ingredient_substitutes_http_402_error(
        self,
        mock_get: Mock,
        spoonacular_service: SpoonacularService,
    ) -> None:
        """Test handling of 402 Payment Required error."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 402
        http_error = httpx.HTTPStatusError(
            "402 Payment Required",
            request=Mock(),
            response=mock_response,
        )
        mock_get.side_effect = http_error

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            spoonacular_service.get_ingredient_substitutes("cheese")

        assert exc_info.value.status_code == 503
        assert "quota limits" in exc_info.value.detail

    @patch("httpx.Client.get")
    def test_get_ingredient_substitutes_http_404_error(
        self,
        mock_get: Mock,
        spoonacular_service: SpoonacularService,
    ) -> None:
        """Test handling of 404 Not Found error."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 404
        http_error = httpx.HTTPStatusError(
            "404 Not Found",
            request=Mock(),
            response=mock_response,
        )
        mock_get.side_effect = http_error

        # Act & Assert
        with pytest.raises(SubstitutionNotFoundError) as exc_info:
            spoonacular_service.get_ingredient_substitutes("nonexistent")

        assert "Spoonacular API returned no results" in str(exc_info.value)

    @patch("httpx.Client.get")
    def test_get_ingredient_substitutes_http_500_error(
        self,
        mock_get: Mock,
        spoonacular_service: SpoonacularService,
    ) -> None:
        """Test handling of 500 Internal Server Error."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 500
        http_error = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=Mock(),
            response=mock_response,
        )
        mock_get.side_effect = http_error

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            spoonacular_service.get_ingredient_substitutes("cheese")

        assert exc_info.value.status_code == 503
        assert "temporarily unavailable" in exc_info.value.detail

    @patch("httpx.Client.get")
    def test_get_ingredient_substitutes_request_error(
        self,
        mock_get: Mock,
        spoonacular_service: SpoonacularService,
    ) -> None:
        """Test handling of request errors."""
        # Arrange
        mock_get.side_effect = httpx.RequestError("Connection timeout")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            spoonacular_service.get_ingredient_substitutes("cheese")

        assert exc_info.value.status_code == 500

    def test_extract_clean_ingredient_name_with_equals_format(
        self, spoonacular_service: SpoonacularService
    ) -> None:
        """Test ingredient name extraction from equals format."""
        # Test cases with different formats
        test_cases = [
            ("1 cup = 1 cup American cheese", "American Cheese"),
            ("2 tablespoons = 1 ounce cream cheese", "Cream Cheese"),
            ("1/2 cup = 1/2 cup sharp cheddar", "Sharp Cheddar"),
        ]

        for input_text, expected in test_cases:
            result = spoonacular_service._extract_clean_ingredient_name(input_text)
            assert result == expected

    def test_extract_clean_ingredient_name_without_equals(
        self, spoonacular_service: SpoonacularService
    ) -> None:
        """Test ingredient name extraction without equals format."""
        # Test cases without equals sign
        test_cases = [
            ("mozzarella cheese (softer texture)", "Mozzarella Cheese"),
            ("swiss cheese - similar flavor", "Swiss Cheese"),
            ("plain yogurt", "Plain Yogurt"),
        ]

        for input_text, expected in test_cases:
            result = spoonacular_service._extract_clean_ingredient_name(input_text)
            assert result == expected

    def test_extract_ratio_from_description(
        self, spoonacular_service: SpoonacularService
    ) -> None:
        """Test ratio extraction from description text."""
        # Test cases with different ratio patterns
        test_cases = [
            ("Use 2:1 ratio for best results", 2.0),
            ("Use 1.5 times the amount", 1.5),
            ("Use 2x the original amount", 2.0),
            ("Use 0.5 times the amount", 0.5),
            ("No ratio mentioned here", 1.0),  # Default
        ]

        for description, expected_ratio in test_cases:
            result = spoonacular_service._extract_ratio_from_description(description)
            assert result == expected_ratio

    @patch("httpx.Client.get")
    def test_get_similar_recipes_success(
        self,
        mock_get: Mock,
        spoonacular_service: SpoonacularService,
        mock_spoonacular_similar_recipes_response: list[dict[str, Any]],
    ) -> None:
        """Test successful similar recipes retrieval."""
        # Arrange
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_spoonacular_similar_recipes_response
        mock_get.return_value = mock_response

        # Act
        result = spoonacular_service.get_similar_recipes(716429, limit=50)

        # Assert
        assert len(result) == 2
        expected_name = "Pasta with Garlic, Scallions, Cauliflower & Breadcrumbs"
        assert result[0]["recipe_name"] == expected_name
        assert result[0]["source"] == "spoonacular"
        assert result[0]["confidence_score"] == 0.7

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "recipes/716429/similar" in call_args[0][0]
        assert call_args[1]["params"]["limit"] == 50

    @patch("httpx.Client.get")
    def test_get_similar_recipes_limit_capping(
        self,
        mock_get: Mock,
        spoonacular_service: SpoonacularService,
        mock_spoonacular_empty_response: list[Any],
    ) -> None:
        """Test that similar recipes limit is capped at 100."""
        # Arrange
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_spoonacular_empty_response
        mock_get.return_value = mock_response

        # Act
        spoonacular_service.get_similar_recipes(123456, limit=150)

        # Assert
        call_args = mock_get.call_args
        assert call_args[1]["params"]["limit"] == 100  # Should be capped

    @patch("httpx.Client.get")
    def test_get_similar_recipes_404_returns_empty_list(
        self,
        mock_get: Mock,
        spoonacular_service: SpoonacularService,
    ) -> None:
        """Test that 404 errors return empty list instead of raising exception."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 404
        http_error = httpx.HTTPStatusError(
            "404 Not Found",
            request=Mock(),
            response=mock_response,
        )
        mock_get.side_effect = http_error

        # Act
        result = spoonacular_service.get_similar_recipes(999999)

        # Assert
        assert result == []

    @patch("httpx.Client.get")
    def test_search_recipes_by_ingredients_success(
        self,
        mock_get: Mock,
        spoonacular_service: SpoonacularService,
        mock_spoonacular_ingredient_search_response: list[dict[str, Any]],
    ) -> None:
        """Test successful recipe search by ingredients."""
        # Arrange
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_spoonacular_ingredient_search_response
        mock_get.return_value = mock_response

        # Act
        result = spoonacular_service.search_recipes_by_ingredients(
            ["asparagus", "beans"], limit=10, ranking=1
        )

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], WebRecipe)
        expected_name = "Cannellini Bean and Asparagus Salad with Mushrooms"
        assert result[0].recipe_name == expected_name

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "recipes/findByIngredients" in call_args[0][0]
        params = call_args[1]["params"]
        assert params["ingredients"] == "asparagus,beans"
        assert params["limit"] == 10
        assert params["ranking"] == 1
        assert params["ignorePantry"] is True

    @patch("httpx.Client.get")
    def test_search_recipes_by_ingredients_no_ranking(
        self,
        mock_get: Mock,
        spoonacular_service: SpoonacularService,
        mock_spoonacular_empty_response: list[Any],
    ) -> None:
        """Test recipe search without ranking parameter."""
        # Arrange
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_spoonacular_empty_response
        mock_get.return_value = mock_response

        # Act
        spoonacular_service.search_recipes_by_ingredients(["tomato"], ranking=None)

        # Assert
        call_args = mock_get.call_args
        params = call_args[1]["params"]
        assert "ranking" not in params

    def test_get_ingredient_substitutions_domain_objects(
        self, spoonacular_service: SpoonacularService
    ) -> None:
        """Test conversion to domain objects."""
        # Arrange - Mock the get_ingredient_substitutes method
        raw_substitutes = [
            {
                "substitute_ingredient": "American Cheese",
                "conversion_ratio": {
                    "ratio": 1.0,
                    "measurement": IngredientUnitEnum.CUP,
                },
                "notes": "1 cup = 1 cup American cheese",
                "confidence_score": 0.8,
            },
            {
                "substitute_ingredient": "Cream Cheese",
                "conversion_ratio": {
                    "ratio": 2.0,
                    "measurement": IngredientUnitEnum.TBSP,
                },
                "notes": "2 tablespoons = 1 ounce cream cheese",
                "confidence_score": 0.8,
            },
        ]

        with patch.object(
            spoonacular_service,
            "get_ingredient_substitutes",
            return_value=raw_substitutes,
        ):
            # Act
            result = spoonacular_service.get_ingredient_substitutions("cheddar cheese")

            # Assert
            assert len(result) == 2
            assert all(isinstance(sub, IngredientSubstitution) for sub in result)

            # Check first substitution
            first_sub = result[0]
            assert first_sub.ingredient == "American Cheese"
            assert isinstance(first_sub.conversion_ratio, ConversionRatio)
            assert first_sub.conversion_ratio.ratio == 1.0
            assert first_sub.conversion_ratio.measurement == IngredientUnitEnum.CUP

            # Check second substitution
            second_sub = result[1]
            assert second_sub.ingredient == "Cream Cheese"
            assert second_sub.conversion_ratio.ratio == 2.0
            assert second_sub.conversion_ratio.measurement == IngredientUnitEnum.TBSP

    def test_convert_recipes_to_standard_format(
        self, spoonacular_service: SpoonacularService
    ) -> None:
        """Test conversion of recipe objects to standard format."""
        # Arrange
        mock_recipe = Mock()
        mock_recipe.title = "Test Recipe"
        mock_recipe.id = 12345
        mock_recipe.source_url = "https://example.com/recipe"
        mock_recipe.image = "https://example.com/image.jpg"
        mock_recipe.summary = "Test summary"
        mock_recipe.ready_in_minutes = 30
        mock_recipe.servings = 4

        # Act
        result = spoonacular_service._convert_recipes_to_standard_format([mock_recipe])

        # Assert
        assert len(result) == 1
        recipe = result[0]
        assert recipe["recipe_name"] == "Test Recipe"
        assert recipe["url"] == "https://example.com/recipe"
        assert recipe["image_url"] == "https://example.com/image.jpg"
        assert recipe["summary"] == "Test summary"
        assert recipe["ready_in_minutes"] == 30
        assert recipe["servings"] == 4
        assert recipe["source"] == "spoonacular"
        assert recipe["confidence_score"] == 0.7

    def test_convert_recipes_to_standard_format_fallback_url(
        self, spoonacular_service: SpoonacularService
    ) -> None:
        """Test URL fallback when source_url is not available."""
        # Arrange
        mock_recipe = Mock()
        mock_recipe.title = "Test Recipe"
        mock_recipe.id = 12345
        mock_recipe.source_url = None
        mock_recipe.spoonacular_source_url = None

        # Act
        result = spoonacular_service._convert_recipes_to_standard_format([mock_recipe])

        # Assert
        recipe = result[0]
        expected_url = "https://spoonacular.com/recipes/Test-Recipe-12345"
        assert recipe["url"] == expected_url

    def test_convert_ingredient_search_to_standard_format(
        self, spoonacular_service: SpoonacularService
    ) -> None:
        """Test conversion of ingredient search results."""
        # Arrange
        raw_recipes = [
            {
                "id": 782585,
                "title": "Test Recipe",
                "image": "https://example.com/image.jpg",
            }
        ]

        # Act
        result = spoonacular_service._convert_ingredient_search_to_standard_format(
            raw_recipes
        )

        # Assert
        assert len(result) == 1
        recipe = result[0]
        assert recipe["recipe_name"] == "Test Recipe"
        assert recipe["url"] == "https://spoonacular.com/recipes/Test-Recipe-782585"
        assert recipe["image_url"] == "https://example.com/image.jpg"
        assert recipe["source"] == "spoonacular"
        assert recipe["confidence_score"] == 0.8  # Higher for ingredient matches

    def test_parse_spoonacular_response_invalid_format(
        self, spoonacular_service: SpoonacularService
    ) -> None:
        """Test handling of invalid response format."""
        # Arrange
        invalid_data = {"invalid": "format"}

        # Act & Assert
        with pytest.raises(SubstitutionNotFoundError) as exc_info:
            spoonacular_service._parse_spoonacular_response(
                invalid_data,
                "test ingredient",
            )

        assert "No valid substitutes found in Spoonacular response" in str(
            exc_info.value
        )

    def test_parse_spoonacular_response_no_substitutes(
        self, spoonacular_service: SpoonacularService
    ) -> None:
        """Test handling when no substitutes are found."""
        # Arrange
        data = {"status": "success", "substitutes": [], "message": ""}

        # Act & Assert
        with pytest.raises(SubstitutionNotFoundError) as exc_info:
            spoonacular_service._parse_spoonacular_response(data, "test ingredient")

        assert "No valid substitutes found" in str(exc_info.value)

    def test_destructor_closes_client(self) -> None:
        """Test that destructor properly closes HTTP client."""
        # Arrange
        service = SpoonacularService()
        mock_client = Mock()
        service.client = mock_client

        # Act
        service.__del__()

        # Assert
        mock_client.close.assert_called_once()

    def test_destructor_handles_missing_client(self) -> None:
        """Test that destructor handles case where client doesn't exist."""
        # Arrange
        service = SpoonacularService()
        delattr(service, "client")

        # Act & Assert - Should not raise exception
        service.__del__()

    @patch("httpx.Client.get")
    def test_search_recipes_by_ingredients_invalid_webrecipe_conversion(
        self,
        mock_get: Mock,
        spoonacular_service: SpoonacularService,
    ) -> None:
        """Test handling of invalid WebRecipe conversion."""
        # Arrange
        invalid_recipe_data = [{"id": 123, "title": "", "image": None}]  # Invalid data
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = invalid_recipe_data
        mock_get.return_value = mock_response

        # Act
        result = spoonacular_service.search_recipes_by_ingredients(["tomato"])

        # Assert - Should handle invalid recipes gracefully but still create objects
        assert len(result) == 1  # Invalid recipes still get converted
        assert result[0].recipe_name == ""  # Empty title becomes empty string

    def test_extract_ratio_edge_cases(
        self, spoonacular_service: SpoonacularService
    ) -> None:
        """Test ratio extraction with edge cases."""
        # Test cases with edge cases
        test_cases = [
            ("", 1.0),  # Empty string
            ("No numbers here", 1.0),  # No numbers
            ("Use 0:1 ratio", 0.0),  # Zero ratio returns 0.0
            ("Multiple 2:1 and 3:1 ratios", 2.0),  # Should pick first match
        ]

        for description, expected_ratio in test_cases:
            result = spoonacular_service._extract_ratio_from_description(description)
            assert result == expected_ratio

    def test_parse_spoonacular_response_invalid_data(
        self, spoonacular_service: SpoonacularService
    ) -> None:
        """Test parsing response with invalid data."""
        # Arrange
        invalid_data = {"invalid": "structure"}

        # Act & Assert
        with pytest.raises(SubstitutionNotFoundError) as exc_info:
            spoonacular_service._parse_spoonacular_response(
                invalid_data, "test ingredient"
            )
        assert "test ingredient" in str(exc_info.value)

    def test_parse_spoonacular_response_empty_data(
        self, spoonacular_service: SpoonacularService
    ) -> None:
        """Test parsing response with empty data."""
        # Arrange

        empty_data: dict[str, Any] = {}

        # Act & Assert
        with pytest.raises(SubstitutionNotFoundError) as exc_info:
            spoonacular_service._parse_spoonacular_response(
                empty_data, "test ingredient"
            )
        assert "test ingredient" in str(exc_info.value)
