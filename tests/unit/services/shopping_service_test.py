"""Unit tests for ShoppingService."""

from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.schemas.common.ingredient import Quantity
from app.api.v1.schemas.response.ingredient_shopping_info_response import (
    IngredientShoppingInfoResponse,
)
from app.api.v1.schemas.response.recipe_shopping_info_response import (
    RecipeShoppingInfoResponse,
)
from app.db.models.ingredient_models.ingredient import Ingredient
from app.db.models.recipe_models.recipe import Recipe
from app.db.models.recipe_models.recipe_ingredient import RecipeIngredient
from app.enums.ingredient_unit_enum import IngredientUnitEnum
from app.exceptions.custom_exceptions import (
    DownstreamAuthenticationError,
    DownstreamDataNotFoundError,
    DownstreamServiceUnavailableError,
    IncompatibleUnitsError,
)


@pytest.mark.unit
class TestShoppingService:
    """Unit tests for ShoppingService class."""

    def test_init(self, shopping_service: Mock, mock_kroger_service: Mock) -> None:
        """Test ShoppingService initialization."""
        assert shopping_service.kroger_service == mock_kroger_service

    def test_get_ingredient_shopping_info_success_with_quantity(
        self,
        shopping_service: Mock,
        mock_db_session: Mock,
        sample_ingredient: Mock,
        sample_quantity: Quantity,
        mock_kroger_ingredient_price: Mock,
    ) -> None:
        """Test successful ingredient shopping info retrieval with quantity."""
        # Setup database query
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            sample_ingredient
        )

        # Setup kroger service success
        shopping_service.kroger_service.get_ingredient_price.return_value = (
            mock_kroger_ingredient_price
        )

        # Act
        result = shopping_service.get_ingredient_shopping_info(
            ingredient_id=1,
            quantity=sample_quantity,
            db=mock_db_session,
        )

        # Assert
        assert isinstance(result, IngredientShoppingInfoResponse)
        assert result.ingredient_name == sample_ingredient.name
        assert result.quantity == sample_quantity
        assert result.estimated_price is not None

        # Verify database query
        mock_db_session.query.assert_called_once_with(Ingredient)
        mock_db_session.query.return_value.filter.assert_called_once()

    def test_get_ingredient_shopping_info_success_without_quantity(
        self,
        shopping_service: Mock,
        mock_db_session: Mock,
        sample_ingredient: Mock,
        mock_kroger_ingredient_price: Mock,
    ) -> None:
        """Test successful ingredient shopping info retrieval without quantity."""
        # Setup database query
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            sample_ingredient
        )

        # Setup kroger service success
        shopping_service.kroger_service.get_ingredient_price.return_value = (
            mock_kroger_ingredient_price
        )

        # Act
        result = shopping_service.get_ingredient_shopping_info(
            ingredient_id=1,
            quantity=None,
            db=mock_db_session,
        )

        # Assert
        assert isinstance(result, IngredientShoppingInfoResponse)
        assert result.ingredient_name == sample_ingredient.name
        assert result.quantity.amount == 1.0
        assert result.quantity.measurement == IngredientUnitEnum.UNIT

    def test_get_ingredient_shopping_info_ingredient_not_found(
        self,
        shopping_service: Mock,
        mock_db_session: Mock,
        sample_quantity: Quantity,
    ) -> None:
        """Test ingredient shopping info when ingredient not found."""
        # Setup database query to return None
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            shopping_service.get_ingredient_shopping_info(
                ingredient_id=999,
                quantity=sample_quantity,
                db=mock_db_session,
            )

        assert exc_info.value.status_code == 404
        assert "Ingredient with ID 999 not found" in str(exc_info.value.detail)

    def test_get_ingredient_shopping_info_incompatible_units_error(
        self,
        shopping_service: Mock,
        mock_db_session: Mock,
        sample_ingredient: Mock,
        sample_quantity: Quantity,
    ) -> None:
        """Test ingredient shopping info with incompatible units error."""
        # Setup database query
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            sample_ingredient
        )

        # Mock the internal method to raise IncompatibleUnitsError
        with patch.object(
            shopping_service, '_get_ingredient_shopping_info'
        ) as mock_method:
            mock_method.side_effect = IncompatibleUnitsError(
                from_unit=IngredientUnitEnum.CUP, to_unit=IngredientUnitEnum.G
            )

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                shopping_service.get_ingredient_shopping_info(
                    ingredient_id=1,
                    quantity=sample_quantity,
                    db=mock_db_session,
                )

            assert exc_info.value.status_code == 400
            assert "Cannot convert quantity" in str(exc_info.value.detail)

    def test_get_ingredient_shopping_info_value_error(
        self,
        shopping_service: Mock,
        mock_db_session: Mock,
        sample_ingredient: Mock,
        sample_quantity: Quantity,
    ) -> None:
        """Test ingredient shopping info with value error."""
        # Setup database query
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            sample_ingredient
        )

        # Mock the internal method to raise ValueError
        with patch.object(
            shopping_service, '_get_ingredient_shopping_info'
        ) as mock_method:
            mock_method.side_effect = ValueError("Test error")

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                shopping_service.get_ingredient_shopping_info(
                    ingredient_id=1,
                    quantity=sample_quantity,
                    db=mock_db_session,
                )

            assert exc_info.value.status_code == 500
            assert "Error calculating shopping info" in str(exc_info.value.detail)

    def test_get_recipe_shopping_info_success(
        self,
        shopping_service: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test successful recipe shopping info retrieval."""
        # Create mock recipe with ingredients
        mock_recipe = Mock(spec=Recipe)
        mock_recipe.recipe_id = 1

        # Create mock recipe ingredient
        mock_recipe_ingredient = Mock(spec=RecipeIngredient)
        mock_recipe_ingredient.quantity = Decimal("2.0")
        mock_recipe_ingredient.unit = IngredientUnitEnum.CUP

        # Create mock ingredient
        mock_ingredient = Mock(spec=Ingredient)
        mock_ingredient.ingredient_id = 1
        mock_ingredient.name = "flour"
        mock_recipe_ingredient.ingredient = mock_ingredient

        mock_recipe.ingredients = [mock_recipe_ingredient]

        # Setup database query chain
        query_mock = Mock()
        mock_db_session.query.return_value = query_mock
        query_mock.outerjoin.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.first.return_value = mock_recipe

        # Mock the internal shopping info method
        mock_shopping_info = IngredientShoppingInfoResponse(
            ingredient_name="flour",
            quantity=Quantity(amount=2.0, measurement=IngredientUnitEnum.CUP),
            estimated_price=5.99,
        )

        with patch.object(
            shopping_service, '_get_ingredient_shopping_info'
        ) as mock_method:
            mock_method.return_value = mock_shopping_info

            # Act
            result = shopping_service.get_recipe_shopping_info(
                recipe_id=1,
                db=mock_db_session,
            )

            # Assert
            assert isinstance(result, RecipeShoppingInfoResponse)
            assert result.recipe_id == 1
            assert len(result.ingredients) == 1
            assert 1 in result.ingredients
            assert result.ingredients[1] == mock_shopping_info
            assert result.total_estimated_cost == Decimal('5.99')

    def test_get_recipe_shopping_info_recipe_not_found(
        self,
        shopping_service: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test recipe shopping info when recipe not found."""
        # Setup database query to return None
        query_mock = Mock()
        mock_db_session.query.return_value = query_mock
        query_mock.outerjoin.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.first.return_value = None

        # Also mock the raw recipe query to return None
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            shopping_service.get_recipe_shopping_info(
                recipe_id=999,
                db=mock_db_session,
            )

        assert exc_info.value.status_code == 404
        assert "Recipe with ID 999 not found" in str(exc_info.value.detail)

    def test_get_recipe_shopping_info_with_ingredient_error(
        self,
        shopping_service: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test recipe shopping info when ingredient processing fails."""
        # Create mock recipe with ingredients
        mock_recipe = Mock(spec=Recipe)
        mock_recipe.recipe_id = 1

        # Create mock recipe ingredient that will cause an error
        mock_recipe_ingredient = Mock(spec=RecipeIngredient)
        mock_recipe_ingredient.quantity = None  # This will cause an error
        mock_recipe_ingredient.unit = None

        mock_ingredient = Mock(spec=Ingredient)
        mock_ingredient.ingredient_id = 1
        mock_ingredient.name = "flour"
        mock_recipe_ingredient.ingredient = mock_ingredient

        mock_recipe.ingredients = [mock_recipe_ingredient]

        # Setup database query
        query_mock = Mock()
        mock_db_session.query.return_value = query_mock
        query_mock.outerjoin.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.first.return_value = mock_recipe

        # Mock the internal method to raise an error
        with patch.object(
            shopping_service, '_get_ingredient_shopping_info'
        ) as mock_method:
            mock_method.side_effect = ValueError("Test error")

            # Act
            result = shopping_service.get_recipe_shopping_info(
                recipe_id=1,
                db=mock_db_session,
            )

            # Assert - should continue with empty ingredients
            assert isinstance(result, RecipeShoppingInfoResponse)
            assert result.recipe_id == 1
            assert len(result.ingredients) == 0
            assert result.total_estimated_cost == 0.0

    def test_get_ingredient_shopping_info_internal_with_kroger_data(
        self,
        shopping_service: Mock,
        sample_ingredient: Mock,
        sample_quantity: Quantity,
        mock_kroger_ingredient_price: Mock,
    ) -> None:
        """Test internal ingredient shopping info with Kroger data."""
        # Setup kroger service success
        shopping_service.kroger_service.get_ingredient_price.return_value = (
            mock_kroger_ingredient_price
        )

        # Act
        result = shopping_service._get_ingredient_shopping_info(
            sample_ingredient, sample_quantity
        )

        # Assert
        assert isinstance(result, IngredientShoppingInfoResponse)
        assert result.ingredient_name == sample_ingredient.name
        assert result.quantity == sample_quantity
        assert result.estimated_price is not None

    def test_get_ingredient_shopping_info_internal_auth_error(
        self,
        shopping_service: Mock,
        sample_ingredient: Mock,
        sample_quantity: Quantity,
    ) -> None:
        """Test internal ingredient shopping info with authentication error."""
        # Setup kroger service to raise auth error
        shopping_service.kroger_service.get_ingredient_price.side_effect = (
            DownstreamAuthenticationError("Auth failed")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            shopping_service._get_ingredient_shopping_info(
                sample_ingredient, sample_quantity
            )

        assert exc_info.value.status_code == 503
        assert "authentication failed" in str(exc_info.value.detail)

    def test_get_ingredient_shopping_info_internal_service_unavailable(
        self,
        shopping_service: Mock,
        sample_ingredient: Mock,
        sample_quantity: Quantity,
    ) -> None:
        """Test internal ingredient shopping info with service unavailable."""
        # Setup kroger service to raise service unavailable error
        shopping_service.kroger_service.get_ingredient_price.side_effect = (
            DownstreamServiceUnavailableError("Service down")
        )

        # Act
        result = shopping_service._get_ingredient_shopping_info(
            sample_ingredient, sample_quantity
        )

        # Assert - should return response with no pricing
        assert isinstance(result, IngredientShoppingInfoResponse)
        assert result.ingredient_name == sample_ingredient.name
        assert result.quantity == sample_quantity
        assert result.estimated_price is None

    def test_get_ingredient_shopping_info_internal_data_not_found(
        self,
        shopping_service: Mock,
        sample_ingredient: Mock,
        sample_quantity: Quantity,
    ) -> None:
        """Test internal ingredient shopping info with data not found."""
        # Setup kroger service to raise data not found error
        shopping_service.kroger_service.get_ingredient_price.side_effect = (
            DownstreamDataNotFoundError("kroger", "ingredient_price")
        )

        # Act
        result = shopping_service._get_ingredient_shopping_info(
            sample_ingredient, sample_quantity
        )

        # Assert - should return response with no pricing
        assert isinstance(result, IngredientShoppingInfoResponse)
        assert result.ingredient_name == sample_ingredient.name
        assert result.quantity == sample_quantity
        assert result.estimated_price is None

    def test_get_ingredient_shopping_info_internal_no_quantity(
        self,
        shopping_service: Mock,
        sample_ingredient: Mock,
        mock_kroger_ingredient_price: Mock,
    ) -> None:
        """Test internal ingredient shopping info without quantity."""
        # Setup kroger service success
        shopping_service.kroger_service.get_ingredient_price.return_value = (
            mock_kroger_ingredient_price
        )

        # Act
        result = shopping_service._get_ingredient_shopping_info(sample_ingredient, None)

        # Assert
        assert isinstance(result, IngredientShoppingInfoResponse)
        assert result.ingredient_name == sample_ingredient.name
        assert result.quantity.amount == 1.0
        assert result.quantity.measurement == IngredientUnitEnum.UNIT

    def test_calculate_price_with_kroger_data(
        self,
        shopping_service: Mock,
        mock_kroger_ingredient_price: Mock,
        sample_quantity: Quantity,
    ) -> None:
        """Test price calculation with Kroger data."""
        # Act
        result = shopping_service._calculate_price_with_kroger_data(
            mock_kroger_ingredient_price, sample_quantity
        )

        # Assert
        expected_price = Decimal(str(mock_kroger_ingredient_price.price)) * Decimal(
            sample_quantity.amount
        )
        assert result == expected_price
        assert isinstance(result, Decimal)
