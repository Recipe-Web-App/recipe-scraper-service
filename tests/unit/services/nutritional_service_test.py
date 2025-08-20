"""Unit tests for NutritionalInfoService.

This module contains comprehensive unit tests for the NutritionalInfoService class,
testing nutritional information retrieval for both individual ingredients and recipes
with proper error handling and quantity adjustments.
"""

from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.schemas.common.ingredient import Quantity
from app.api.v1.schemas.response.ingredient_nutritional_info_response import (
    IngredientNutritionalInfoResponse,
)
from app.api.v1.schemas.response.recipe_nutritional_info_response import (
    RecipeNutritionalInfoResponse,
)
from app.db.models.ingredient_models.ingredient import Ingredient
from app.db.models.nutritional_info_models.nutritional_info import NutritionalInfo
from app.db.models.recipe_models.recipe import Recipe
from app.db.models.recipe_models.recipe_ingredient import RecipeIngredient
from app.enums.ingredient_unit_enum import IngredientUnitEnum
from app.exceptions.custom_exceptions import IncompatibleUnitsError
from app.services.nutritional_info_service import NutritionalInfoService


@pytest.mark.unit
class TestNutritionalInfoService:
    """Unit tests for NutritionalInfoService."""

    @pytest.fixture
    def nutritional_service(self) -> NutritionalInfoService:
        """Create a NutritionalInfoService instance for testing."""
        return NutritionalInfoService()

    @pytest.fixture
    def mock_ingredient(self) -> Mock:
        """Create a mock ingredient."""
        ingredient = Mock(spec=Ingredient)
        ingredient.ingredient_id = 1
        ingredient.name = "Tomato"
        return ingredient

    @pytest.fixture
    def mock_nutritional_info(self) -> Mock:
        """Create a mock nutritional info."""
        nutritional_info = Mock(spec=NutritionalInfo)
        nutritional_info.product_name = "Tomato, fresh"
        nutritional_info.generic_name = "Tomato"
        nutritional_info.calories = Decimal("18.0")
        nutritional_info.protein = Decimal("0.9")
        nutritional_info.carbohydrates = Decimal("3.9")
        nutritional_info.fat = Decimal("0.2")
        return nutritional_info

    @pytest.fixture
    def mock_recipe(self) -> Mock:
        """Create a mock recipe with ingredients."""
        recipe = Mock(spec=Recipe)
        recipe.recipe_id = 1
        recipe.recipe_name = "Test Recipe"

        # Create mock recipe ingredients
        recipe_ingredient = Mock(spec=RecipeIngredient)
        recipe_ingredient.ingredient_id = 1
        recipe_ingredient.quantity = Decimal("100")
        recipe_ingredient.unit = IngredientUnitEnum.G
        recipe_ingredient.ingredient = Mock(spec=Ingredient)
        recipe_ingredient.ingredient.name = "Tomato"

        recipe.ingredients = [recipe_ingredient]
        return recipe

    def test_nutritional_service_initialization(
        self, nutritional_service: NutritionalInfoService
    ) -> None:
        """Test NutritionalInfoService initialization."""
        assert nutritional_service is not None

    def test_get_ingredient_nutritional_info_success(
        self,
        nutritional_service: NutritionalInfoService,
        mock_db_session: Mock,
        mock_ingredient: Mock,
        mock_nutritional_info: Mock,
    ) -> None:
        """Test successful ingredient nutritional info retrieval."""
        # Arrange
        ingredient_id = 1
        quantity = Quantity(amount=Decimal("100"), measurement=IngredientUnitEnum.G)

        mock_db_session.query().filter().first.side_effect = [
            mock_ingredient,  # First call for ingredient
            mock_nutritional_info,  # Second call for nutritional info
        ]

        with patch(
            "app.services.nutritional_info_service."
            "IngredientNutritionalInfoResponse.from_db_model"
        ) as mock_from_db:
            mock_response = Mock(spec=IngredientNutritionalInfoResponse)
            mock_response.adjust_quantity = Mock()
            mock_from_db.return_value = mock_response

            # Act
            result = nutritional_service.get_ingredient_nutritional_info(
                ingredient_id, quantity, mock_db_session
            )

            # Assert
            assert result == mock_response
            mock_from_db.assert_called_once_with(mock_nutritional_info)
            mock_response.adjust_quantity.assert_called_once_with(quantity)

    def test_get_ingredient_nutritional_info_ingredient_not_found(
        self,
        nutritional_service: NutritionalInfoService,
        mock_db_session: Mock,
    ) -> None:
        """Test ingredient not found error."""
        # Arrange
        ingredient_id = 999
        quantity = None
        mock_db_session.query().filter().first.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            nutritional_service.get_ingredient_nutritional_info(
                ingredient_id, quantity, mock_db_session
            )

        assert exc_info.value.status_code == 404
        expected_detail = f"Ingredient with ID {ingredient_id} not found"
        assert expected_detail in str(exc_info.value.detail)

    def test_get_ingredient_nutritional_info_no_nutritional_data(
        self,
        nutritional_service: NutritionalInfoService,
        mock_db_session: Mock,
        mock_ingredient: Mock,
    ) -> None:
        """Test no nutritional data found for ingredient."""
        # Arrange
        ingredient_id = 1
        quantity = None

        # First call returns ingredient, subsequent calls return None
        mock_db_session.query().filter().first.side_effect = [
            mock_ingredient,  # Ingredient found
            None,  # No nutritional info by product name
            None,  # No nutritional info by generic name
        ]

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            nutritional_service.get_ingredient_nutritional_info(
                ingredient_id, quantity, mock_db_session
            )

        assert exc_info.value.status_code == 404
        assert "Nutritional information for ingredient" in str(exc_info.value.detail)
        assert "not found" in str(exc_info.value.detail)

    def test_get_ingredient_nutritional_info_fallback_to_generic_name(
        self,
        nutritional_service: NutritionalInfoService,
        mock_db_session: Mock,
        mock_ingredient: Mock,
        mock_nutritional_info: Mock,
    ) -> None:
        """Test fallback to generic name search."""
        # Arrange
        ingredient_id = 1
        quantity = None

        # First call returns ingredient, second returns None,
        # third returns nutritional info
        mock_db_session.query().filter().first.side_effect = [
            mock_ingredient,  # Ingredient found
            None,  # No nutritional info by product name
            mock_nutritional_info,  # Found by generic name
        ]

        with patch(
            "app.services.nutritional_info_service."
            "IngredientNutritionalInfoResponse.from_db_model"
        ) as mock_from_db:
            mock_response = Mock(spec=IngredientNutritionalInfoResponse)
            mock_from_db.return_value = mock_response

            # Act
            result = nutritional_service.get_ingredient_nutritional_info(
                ingredient_id, quantity, mock_db_session
            )

            # Assert
            assert result == mock_response
            mock_from_db.assert_called_once_with(mock_nutritional_info)

    def test_get_ingredient_nutritional_info_conversion_error(
        self,
        nutritional_service: NutritionalInfoService,
        mock_db_session: Mock,
        mock_ingredient: Mock,
        mock_nutritional_info: Mock,
    ) -> None:
        """Test database model conversion error."""
        # Arrange
        ingredient_id = 1
        quantity = None

        mock_db_session.query().filter().first.side_effect = [
            mock_ingredient,
            mock_nutritional_info,
        ]

        with patch(
            "app.services.nutritional_info_service."
            "IngredientNutritionalInfoResponse.from_db_model"
        ) as mock_from_db:
            mock_from_db.side_effect = ValueError("Conversion error")

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                nutritional_service.get_ingredient_nutritional_info(
                    ingredient_id, quantity, mock_db_session
                )

            assert exc_info.value.status_code == 500
            assert "Error converting nutritional info" in str(exc_info.value.detail)

    def test_get_ingredient_nutritional_info_incompatible_units_error(
        self,
        nutritional_service: NutritionalInfoService,
        mock_db_session: Mock,
        mock_ingredient: Mock,
        mock_nutritional_info: Mock,
    ) -> None:
        """Test incompatible units error during quantity adjustment."""
        # Arrange
        ingredient_id = 1
        quantity = Quantity(amount=Decimal("1"), measurement=IngredientUnitEnum.CUP)

        mock_db_session.query().filter().first.side_effect = [
            mock_ingredient,
            mock_nutritional_info,
        ]

        with patch(
            "app.services.nutritional_info_service."
            "IngredientNutritionalInfoResponse.from_db_model"
        ) as mock_from_db:
            mock_response = Mock(spec=IngredientNutritionalInfoResponse)
            mock_response.adjust_quantity.side_effect = IncompatibleUnitsError(
                IngredientUnitEnum.G, IngredientUnitEnum.CUP
            )
            mock_from_db.return_value = mock_response

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                nutritional_service.get_ingredient_nutritional_info(
                    ingredient_id, quantity, mock_db_session
                )

            assert exc_info.value.status_code == 400
            assert "Cannot convert nutritional info" in str(exc_info.value.detail)
            assert "incompatible units" in str(exc_info.value.detail)

    def test_get_ingredient_nutritional_info_quantity_adjustment_error(
        self,
        nutritional_service: NutritionalInfoService,
        mock_db_session: Mock,
        mock_ingredient: Mock,
        mock_nutritional_info: Mock,
    ) -> None:
        """Test quantity adjustment error."""
        # Arrange
        ingredient_id = 1
        quantity = Quantity(amount=Decimal("100"), measurement=IngredientUnitEnum.G)

        mock_db_session.query().filter().first.side_effect = [
            mock_ingredient,
            mock_nutritional_info,
        ]

        with patch(
            "app.services.nutritional_info_service."
            "IngredientNutritionalInfoResponse.from_db_model"
        ) as mock_from_db:
            mock_response = Mock(spec=IngredientNutritionalInfoResponse)
            mock_response.adjust_quantity.side_effect = ValueError("Adjustment error")
            mock_from_db.return_value = mock_response

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                nutritional_service.get_ingredient_nutritional_info(
                    ingredient_id, quantity, mock_db_session
                )

            assert exc_info.value.status_code == 500
            assert "Error adjusting nutritional info" in str(exc_info.value.detail)

    def test_get_ingredient_nutritional_info_without_quantity(
        self,
        nutritional_service: NutritionalInfoService,
        mock_db_session: Mock,
        mock_ingredient: Mock,
        mock_nutritional_info: Mock,
    ) -> None:
        """Test ingredient nutritional info retrieval without quantity."""
        # Arrange
        ingredient_id = 1
        quantity = None

        mock_db_session.query().filter().first.side_effect = [
            mock_ingredient,
            mock_nutritional_info,
        ]

        with patch(
            "app.services.nutritional_info_service."
            "IngredientNutritionalInfoResponse.from_db_model"
        ) as mock_from_db:
            mock_response = Mock(spec=IngredientNutritionalInfoResponse)
            mock_from_db.return_value = mock_response

            # Act
            result = nutritional_service.get_ingredient_nutritional_info(
                ingredient_id, quantity, mock_db_session
            )

            # Assert
            assert result == mock_response
            mock_from_db.assert_called_once_with(mock_nutritional_info)
            # Should not call adjust_quantity when quantity is None
            assert (
                not hasattr(mock_response, 'adjust_quantity')
                or not mock_response.adjust_quantity.called
            )

    def test_get_recipe_nutritional_info_success_with_total_and_ingredients(
        self,
        nutritional_service: NutritionalInfoService,
        mock_db_session: Mock,
        mock_recipe: Mock,
    ) -> None:
        """Test successful recipe nutritional info retrieval with total and
        ingredients."""
        # Arrange
        recipe_id = 1
        include_total = True
        include_ingredients = True

        mock_db_session.query().filter().first.return_value = mock_recipe

        with patch.object(
            nutritional_service, 'get_ingredient_nutritional_info'
        ) as mock_get_ingredient:
            mock_ingredient_response = Mock(spec=IngredientNutritionalInfoResponse)
            mock_get_ingredient.return_value = mock_ingredient_response

            with patch(
                "app.services.nutritional_info_service."
                "IngredientNutritionalInfoResponse.calculate_total_nutritional_info"
            ) as mock_calculate_total:
                mock_total = Mock(spec=IngredientNutritionalInfoResponse)
                mock_calculate_total.return_value = mock_total

                # Act
                result = nutritional_service.get_recipe_nutritional_info(
                    recipe_id, include_total, include_ingredients, mock_db_session
                )

                # Assert
                assert isinstance(result, RecipeNutritionalInfoResponse)
                assert result.ingredients == {1: mock_ingredient_response}
                assert result.total == mock_total
                assert result.missing_ingredients is None  # No missing ingredients
                mock_calculate_total.assert_called_once_with([mock_ingredient_response])

    def test_get_recipe_nutritional_info_recipe_not_found(
        self,
        nutritional_service: NutritionalInfoService,
        mock_db_session: Mock,
    ) -> None:
        """Test recipe not found error."""
        # Arrange
        recipe_id = 999
        include_total = True
        include_ingredients = True

        mock_db_session.query().filter().first.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            nutritional_service.get_recipe_nutritional_info(
                recipe_id, include_total, include_ingredients, mock_db_session
            )

        assert exc_info.value.status_code == 404
        assert f"Recipe with ID {recipe_id} not found" in str(exc_info.value.detail)

    def test_get_recipe_nutritional_info_with_missing_ingredients(
        self,
        nutritional_service: NutritionalInfoService,
        mock_db_session: Mock,
        mock_recipe: Mock,
    ) -> None:
        """Test recipe nutritional info with missing ingredient data."""
        # Arrange
        recipe_id = 1
        include_total = False
        include_ingredients = True

        mock_db_session.query().filter().first.return_value = mock_recipe

        with patch.object(
            nutritional_service, 'get_ingredient_nutritional_info'
        ) as mock_get_ingredient:
            mock_get_ingredient.side_effect = HTTPException(
                status_code=404, detail="Nutritional info not found"
            )

            # Act
            result = nutritional_service.get_recipe_nutritional_info(
                recipe_id, include_total, include_ingredients, mock_db_session
            )

            # Assert
            assert isinstance(result, RecipeNutritionalInfoResponse)
            assert result.ingredients == {}
            assert result.total is None
            assert result.missing_ingredients == [1]

    def test_get_recipe_nutritional_info_ingredient_without_quantity(
        self,
        nutritional_service: NutritionalInfoService,
        mock_db_session: Mock,
    ) -> None:
        """Test recipe with ingredient that has no quantity/unit."""
        # Arrange
        recipe_id = 1
        include_total = True
        include_ingredients = True

        # Create recipe with ingredient without quantity/unit
        recipe = Mock(spec=Recipe)
        recipe.recipe_id = 1
        recipe_ingredient = Mock(spec=RecipeIngredient)
        recipe_ingredient.ingredient_id = 1
        recipe_ingredient.quantity = None  # No quantity
        recipe_ingredient.unit = None  # No unit
        recipe_ingredient.ingredient = Mock(spec=Ingredient)
        recipe_ingredient.ingredient.name = "Salt"
        recipe.ingredients = [recipe_ingredient]

        mock_db_session.query().filter().first.return_value = recipe

        with patch.object(
            nutritional_service, 'get_ingredient_nutritional_info'
        ) as mock_get_ingredient:
            mock_ingredient_response = Mock(spec=IngredientNutritionalInfoResponse)
            # Add classification attribute for calculate_total_nutritional_info
            mock_classification = Mock()
            mock_classification.nutriscore_score = None
            mock_ingredient_response.classification = mock_classification
            mock_get_ingredient.return_value = mock_ingredient_response

            # Mock the calculate_total_nutritional_info to avoid complex mocking
            with patch(
                "app.services.nutritional_info_service."
                "IngredientNutritionalInfoResponse.calculate_total_nutritional_info"
            ) as mock_calculate_total:
                mock_total = Mock(spec=IngredientNutritionalInfoResponse)
                mock_calculate_total.return_value = mock_total

                # Act
                result = nutritional_service.get_recipe_nutritional_info(
                    recipe_id, include_total, include_ingredients, mock_db_session
                )

                # Assert
                mock_get_ingredient.assert_called_once_with(1, None, mock_db_session)
                assert result.ingredients == {1: mock_ingredient_response}
                assert result.total == mock_total

    def test_get_recipe_nutritional_info_unexpected_error_handling(
        self,
        nutritional_service: NutritionalInfoService,
        mock_db_session: Mock,
        mock_recipe: Mock,
    ) -> None:
        """Test handling of unexpected errors during ingredient processing."""
        # Arrange
        recipe_id = 1
        include_total = False
        include_ingredients = True

        mock_db_session.query().filter().first.return_value = mock_recipe

        with patch.object(
            nutritional_service, 'get_ingredient_nutritional_info'
        ) as mock_get_ingredient:
            mock_get_ingredient.side_effect = ValueError("Unexpected error")

            # Act
            result = nutritional_service.get_recipe_nutritional_info(
                recipe_id, include_total, include_ingredients, mock_db_session
            )

            # Assert
            assert isinstance(result, RecipeNutritionalInfoResponse)
            assert result.ingredients == {}
            assert result.missing_ingredients == [1]

    def test_get_recipe_nutritional_info_exclude_ingredients_include_total(
        self,
        nutritional_service: NutritionalInfoService,
        mock_db_session: Mock,
        mock_recipe: Mock,
    ) -> None:
        """Test recipe nutritional info excluding ingredients but including total."""
        # Arrange
        recipe_id = 1
        include_total = True
        include_ingredients = False

        mock_db_session.query().filter().first.return_value = mock_recipe

        with patch.object(
            nutritional_service, 'get_ingredient_nutritional_info'
        ) as mock_get_ingredient:
            mock_ingredient_response = Mock(spec=IngredientNutritionalInfoResponse)
            mock_get_ingredient.return_value = mock_ingredient_response

            with patch(
                "app.services.nutritional_info_service."
                "IngredientNutritionalInfoResponse.calculate_total_nutritional_info"
            ) as mock_calculate_total:
                mock_total = Mock(spec=IngredientNutritionalInfoResponse)
                mock_calculate_total.return_value = mock_total

                # Act
                result = nutritional_service.get_recipe_nutritional_info(
                    recipe_id, include_total, include_ingredients, mock_db_session
                )

            # Assert
            assert result.ingredients is None  # Should not include ingredients
            assert result.total == mock_total
            assert result.missing_ingredients is None  # No missing ingredients

    def test_get_recipe_nutritional_info_minimal_response(
        self,
        nutritional_service: NutritionalInfoService,
        mock_db_session: Mock,
        mock_recipe: Mock,
    ) -> None:
        """Test recipe nutritional info with minimal response (no total/ingredients)."""
        # Arrange
        recipe_id = 1
        include_total = False
        include_ingredients = False

        mock_db_session.query().filter().first.return_value = mock_recipe

        with patch.object(
            nutritional_service, 'get_ingredient_nutritional_info'
        ) as mock_get_ingredient:
            mock_ingredient_response = Mock(spec=IngredientNutritionalInfoResponse)
            mock_get_ingredient.return_value = mock_ingredient_response

            # Act
            result = nutritional_service.get_recipe_nutritional_info(
                recipe_id, include_total, include_ingredients, mock_db_session
            )

        # Assert
        assert result.ingredients is None
        assert result.total is None
        assert result.missing_ingredients is None  # Still processed but not included
