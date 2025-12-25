"""Unit tests for RecommendationsService."""

from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.schemas.common.web_recipe import WebRecipe
from app.api.v1.schemas.response.pairing_suggestions_response import (
    PairingSuggestionsResponse,
)
from app.api.v1.schemas.response.recommended_substitutions_response import (
    RecommendedSubstitutionsResponse,
)
from app.db.models.ingredient_models.ingredient import Ingredient as IngredientModel
from app.db.models.recipe_models.recipe import Recipe as RecipeModel
from app.db.models.recipe_models.recipe_ingredient import RecipeIngredient


@pytest.mark.unit
class TestRecommendationsService:
    """Unit tests for RecommendationsService class."""

    def test_init(
        self,
        recommendations_service: Mock,
        mock_cache_manager: Mock,
        mock_spoonacular_service: Mock,
    ) -> None:
        """Test RecommendationsService initialization."""
        assert recommendations_service._cache_manager == mock_cache_manager
        assert recommendations_service._spoonacular_service == mock_spoonacular_service
        assert recommendations_service._MIN_SHARED_INGREDIENTS == 2

    def test_get_recommended_substitutions_success(
        self,
        recommendations_service: Mock,
        mock_db_session: Mock,
        sample_ingredient: Mock,
        sample_quantity: Mock,
        sample_pagination: Mock,
        mock_spoonacular_service: Mock,
    ) -> None:
        """Test successful ingredient substitution retrieval."""
        # Arrange
        ingredient_id = 1
        mock_substitutions = [
            WebRecipe(recipe_name="Alternative 1", url="https://example.com/alt1"),
            WebRecipe(recipe_name="Alternative 2", url="https://example.com/alt2"),
        ]

        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            sample_ingredient
        )
        mock_spoonacular_service.get_ingredient_substitutions.return_value = (
            mock_substitutions
        )

        with patch.object(
            RecommendedSubstitutionsResponse, "from_all"
        ) as mock_from_all:
            expected_response = Mock(spec=RecommendedSubstitutionsResponse)
            mock_from_all.return_value = expected_response

            # Act
            result = recommendations_service.get_recommended_substitutions(
                ingredient_id, sample_quantity, sample_pagination, mock_db_session
            )

            # Assert
            assert result == expected_response
            mock_db_session.query.assert_called_once_with(IngredientModel)
            mock_spoonacular_service.get_ingredient_substitutions.assert_called_once_with(
                ingredient_name=sample_ingredient.name
            )
            mock_from_all.assert_called_once()

    def test_get_recommended_substitutions_ingredient_not_found(
        self,
        recommendations_service: Mock,
        mock_db_session: Mock,
        sample_quantity: Mock,
        sample_pagination: Mock,
    ) -> None:
        """Test ingredient substitution when ingredient is not found."""
        # Arrange
        ingredient_id = 999
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            recommendations_service.get_recommended_substitutions(
                ingredient_id, sample_quantity, sample_pagination, mock_db_session
            )

        assert exc_info.value.status_code == 404
        expected_detail = f"Ingredient with ID {ingredient_id} not found"
        assert expected_detail in str(exc_info.value.detail)

    def test_get_recommended_substitutions_without_quantity(
        self,
        recommendations_service: Mock,
        mock_db_session: Mock,
        sample_ingredient: Mock,
        sample_pagination: Mock,
        mock_spoonacular_service: Mock,
    ) -> None:
        """Test ingredient substitution without quantity."""
        # Arrange
        ingredient_id = 1
        mock_substitutions: list[str] = []

        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            sample_ingredient
        )
        mock_spoonacular_service.get_ingredient_substitutions.return_value = (
            mock_substitutions
        )

        with patch.object(
            RecommendedSubstitutionsResponse, "from_all"
        ) as mock_from_all:
            expected_response = Mock(spec=RecommendedSubstitutionsResponse)
            mock_from_all.return_value = expected_response

            # Act
            result = recommendations_service.get_recommended_substitutions(
                ingredient_id, None, sample_pagination, mock_db_session
            )

            # Assert
            assert result == expected_response
            mock_spoonacular_service.get_ingredient_substitutions.assert_called_once_with(
                ingredient_name=sample_ingredient.name
            )

    @pytest.mark.asyncio
    async def test_get_pairing_suggestions_success(
        self,
        recommendations_service: Mock,
        mock_db_session: Mock,
        sample_recipe: Mock,
        sample_pagination: Mock,
    ) -> None:
        """Test successful pairing suggestions retrieval."""
        # Arrange
        recipe_id = 1
        db_suggestions = [
            WebRecipe(recipe_name="DB Recipe 1", url="https://example.com/db1"),
        ]
        spoonacular_suggestions = [
            WebRecipe(recipe_name="API Recipe 1", url="https://example.com/api1"),
        ]

        with (
            patch.object(
                recommendations_service, "_get_recipe_by_id"
            ) as mock_get_recipe,
            patch.object(
                recommendations_service, "_get_database_pairing_suggestions"
            ) as mock_db_suggestions,
            patch.object(
                recommendations_service, "_get_spoonacular_pairing_suggestions"
            ) as mock_spoon_suggestions,
            patch.object(
                recommendations_service, "_deduplicate_suggestions"
            ) as mock_dedupe,
            patch.object(PairingSuggestionsResponse, "from_all") as mock_from_all,
        ):
            mock_get_recipe.return_value = sample_recipe
            mock_db_suggestions.return_value = db_suggestions
            mock_spoon_suggestions.return_value = spoonacular_suggestions
            mock_dedupe.return_value = db_suggestions + spoonacular_suggestions

            expected_response = Mock(spec=PairingSuggestionsResponse)
            mock_from_all.return_value = expected_response

            # Act
            result = await recommendations_service.get_pairing_suggestions(
                recipe_id, sample_pagination, mock_db_session
            )

            # Assert
            assert result == expected_response
            mock_get_recipe.assert_called_once_with(recipe_id, mock_db_session)
            mock_db_suggestions.assert_called_once_with(sample_recipe, mock_db_session)
            mock_spoon_suggestions.assert_called_once_with(
                sample_recipe, mock_db_session
            )
            mock_dedupe.assert_called_once()
            mock_from_all.assert_called_once_with(
                recipe_id, db_suggestions + spoonacular_suggestions, sample_pagination
            )

    @pytest.mark.asyncio
    async def test_get_pairing_suggestions_recipe_not_found(
        self,
        recommendations_service: Mock,
        mock_db_session: Mock,
        sample_pagination: Mock,
    ) -> None:
        """Test pairing suggestions when recipe is not found."""
        # Arrange
        recipe_id = 999

        with patch.object(
            recommendations_service, "_get_recipe_by_id"
        ) as mock_get_recipe:
            mock_get_recipe.side_effect = HTTPException(
                status_code=404, detail="Recipe not found"
            )

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await recommendations_service.get_pairing_suggestions(
                    recipe_id, sample_pagination, mock_db_session
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_pairing_suggestions_database_error(
        self,
        recommendations_service: Mock,
        mock_db_session: Mock,
        sample_recipe: Mock,
        sample_pagination: Mock,
    ) -> None:
        """Test pairing suggestions with database error."""
        # Arrange
        recipe_id = 1

        with (
            patch.object(
                recommendations_service, "_get_recipe_by_id"
            ) as mock_get_recipe,
            patch.object(
                recommendations_service, "_get_database_pairing_suggestions"
            ) as mock_db_suggestions,
            patch.object(PairingSuggestionsResponse, "from_all") as mock_from_all,
        ):
            mock_get_recipe.return_value = sample_recipe
            mock_db_suggestions.side_effect = SQLAlchemyError("Database error")

            expected_response = Mock(spec=PairingSuggestionsResponse)
            mock_from_all.return_value = expected_response

            # Act
            result = await recommendations_service.get_pairing_suggestions(
                recipe_id, sample_pagination, mock_db_session
            )

            # Assert
            assert result == expected_response
            mock_from_all.assert_called_once_with(recipe_id, [], sample_pagination)

    @pytest.mark.asyncio
    async def test_get_pairing_suggestions_unexpected_error(
        self,
        recommendations_service: Mock,
        mock_db_session: Mock,
        sample_recipe: Mock,
        sample_pagination: Mock,
    ) -> None:
        """Test pairing suggestions with unexpected error."""
        # Arrange
        recipe_id = 1

        with (
            patch.object(
                recommendations_service, "_get_recipe_by_id"
            ) as mock_get_recipe,
            patch.object(
                recommendations_service, "_get_database_pairing_suggestions"
            ) as mock_db_suggestions,
            patch.object(PairingSuggestionsResponse, "from_all") as mock_from_all,
        ):
            mock_get_recipe.return_value = sample_recipe
            mock_db_suggestions.side_effect = ValueError("Unexpected error")

            expected_response = Mock(spec=PairingSuggestionsResponse)
            mock_from_all.return_value = expected_response

            # Act
            result = await recommendations_service.get_pairing_suggestions(
                recipe_id, sample_pagination, mock_db_session
            )

            # Assert
            assert result == expected_response
            mock_from_all.assert_called_once_with(recipe_id, [], sample_pagination)

    def test_get_database_pairing_suggestions_success(
        self,
        recommendations_service: Mock,
        sample_recipe: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test database pairing suggestions retrieval."""
        # Arrange
        ingredient_suggestions = [
            WebRecipe(
                recipe_name="Similar Ingredient Recipe", url="https://example.com/ing1"
            ),
        ]
        tag_suggestions = [
            WebRecipe(recipe_name="Similar Tag Recipe", url="https://example.com/tag1"),
        ]

        with (
            patch.object(
                recommendations_service, "_find_recipes_with_similar_ingredients"
            ) as mock_similar_ingredients,
            patch.object(
                recommendations_service, "_find_recipes_with_similar_tags"
            ) as mock_similar_tags,
        ):
            mock_similar_ingredients.return_value = ingredient_suggestions
            mock_similar_tags.return_value = tag_suggestions

            # Act
            result = recommendations_service._get_database_pairing_suggestions(
                sample_recipe, mock_db_session
            )

            # Assert
            assert result == ingredient_suggestions + tag_suggestions
            mock_similar_ingredients.assert_called_once_with(
                sample_recipe, mock_db_session, limit=5
            )
            mock_similar_tags.assert_called_once_with(
                sample_recipe, mock_db_session, limit=5
            )

    def test_get_database_pairing_suggestions_with_errors(
        self,
        recommendations_service: Mock,
        sample_recipe: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test database pairing suggestions with errors."""
        # Arrange
        with (
            patch.object(
                recommendations_service, "_find_recipes_with_similar_ingredients"
            ) as mock_similar_ingredients,
            patch.object(
                recommendations_service, "_find_recipes_with_similar_tags"
            ) as mock_similar_tags,
        ):
            mock_similar_ingredients.side_effect = SQLAlchemyError("Ingredient error")
            mock_similar_tags.side_effect = SQLAlchemyError("Tag error")

            # Act
            result = recommendations_service._get_database_pairing_suggestions(
                sample_recipe, mock_db_session
            )

            # Assert
            assert result == []

    @pytest.mark.asyncio
    async def test_get_spoonacular_pairing_suggestions_cache_hit(
        self,
        recommendations_service: Mock,
        sample_recipe: Mock,
        mock_db_session: Mock,
        mock_cache_manager: Mock,
    ) -> None:
        """Test Spoonacular pairing suggestions with cache hit."""
        # Arrange
        cached_data = [
            {"recipe_name": "Cached Recipe 1", "url": "https://example.com/cached1"},
            {"recipe_name": "Cached Recipe 2", "url": "https://example.com/cached2"},
        ]

        with patch.object(
            recommendations_service, "_get_recipe_ingredients"
        ) as mock_get_ingredients:
            mock_get_ingredients.return_value = ["flour", "sugar"]
            mock_cache_manager.get.return_value = cached_data

            # Act
            result = await recommendations_service._get_spoonacular_pairing_suggestions(
                sample_recipe, mock_db_session
            )

            # Assert
            assert len(result) == 2
            assert all(isinstance(recipe, WebRecipe) for recipe in result)
            assert result[0].recipe_name == "Cached Recipe 1"
            assert result[1].recipe_name == "Cached Recipe 2"

    @pytest.mark.asyncio
    async def test_get_spoonacular_pairing_suggestions_cache_miss(
        self,
        recommendations_service: Mock,
        sample_recipe: Mock,
        mock_db_session: Mock,
        mock_cache_manager: Mock,
        mock_spoonacular_service: Mock,
    ) -> None:
        """Test Spoonacular pairing suggestions with cache miss."""
        # Arrange
        api_suggestions = [
            WebRecipe(recipe_name="API Recipe 1", url="https://example.com/api1"),
            WebRecipe(recipe_name="API Recipe 2", url="https://example.com/api2"),
        ]

        with patch.object(
            recommendations_service, "_get_recipe_ingredients"
        ) as mock_get_ingredients:
            mock_get_ingredients.return_value = ["flour", "sugar"]
            mock_cache_manager.get.return_value = None
            mock_spoonacular_service.search_recipes_by_ingredients.return_value = (
                api_suggestions
            )

            # Act
            result = await recommendations_service._get_spoonacular_pairing_suggestions(
                sample_recipe, mock_db_session
            )

            # Assert
            assert result == api_suggestions
            mock_spoonacular_service.search_recipes_by_ingredients.assert_called_once_with(
                ingredients=["flour", "sugar"], limit=100
            )
            mock_cache_manager.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_spoonacular_pairing_suggestions_no_ingredients(
        self,
        recommendations_service: Mock,
        sample_recipe: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test Spoonacular pairing suggestions with no ingredients."""
        # Arrange
        with patch.object(
            recommendations_service, "_get_recipe_ingredients"
        ) as mock_get_ingredients:
            mock_get_ingredients.return_value = []

            # Act
            result = await recommendations_service._get_spoonacular_pairing_suggestions(
                sample_recipe, mock_db_session
            )

            # Assert
            assert result == []

    @pytest.mark.asyncio
    async def test_get_spoonacular_pairing_suggestions_api_error(
        self,
        recommendations_service: Mock,
        sample_recipe: Mock,
        mock_db_session: Mock,
        mock_cache_manager: Mock,
        mock_spoonacular_service: Mock,
    ) -> None:
        """Test Spoonacular pairing suggestions with API error."""
        # Arrange
        with patch.object(
            recommendations_service, "_get_recipe_ingredients"
        ) as mock_get_ingredients:
            mock_get_ingredients.return_value = ["flour", "sugar"]
            mock_cache_manager.get.return_value = None
            mock_spoonacular_service.search_recipes_by_ingredients.side_effect = (
                HTTPException(status_code=500, detail="API Error")
            )

            # Act
            result = await recommendations_service._get_spoonacular_pairing_suggestions(
                sample_recipe, mock_db_session
            )

            # Assert
            assert result == []

    @pytest.mark.asyncio
    async def test_get_spoonacular_pairing_suggestions_cache_error(
        self,
        recommendations_service: Mock,
        sample_recipe: Mock,
        mock_db_session: Mock,
        mock_cache_manager: Mock,
        mock_spoonacular_service: Mock,
    ) -> None:
        """Test Spoonacular pairing suggestions with cache error."""
        # Arrange
        api_suggestions = [
            WebRecipe(recipe_name="API Recipe", url="https://example.com/api"),
        ]

        with patch.object(
            recommendations_service, "_get_recipe_ingredients"
        ) as mock_get_ingredients:
            mock_get_ingredients.return_value = ["flour"]
            mock_cache_manager.get.return_value = None
            mock_cache_manager.set.side_effect = OSError("Cache error")
            mock_spoonacular_service.search_recipes_by_ingredients.return_value = (
                api_suggestions
            )

            # Act
            result = await recommendations_service._get_spoonacular_pairing_suggestions(
                sample_recipe, mock_db_session
            )

            # Assert
            assert result == api_suggestions

    def test_get_recipe_ingredients_success(
        self,
        recommendations_service: Mock,
        sample_recipe: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test successful recipe ingredients retrieval."""
        # Arrange
        mock_recipe_ingredients = []
        for name in ["flour", "sugar", "eggs"]:
            mock_ingredient = Mock()
            mock_ingredient.name = name
            mock_recipe_ingredient = Mock(spec=RecipeIngredient)
            mock_recipe_ingredient.ingredient = mock_ingredient
            mock_recipe_ingredients.append(mock_recipe_ingredient)

        mock_db_session.query.return_value.filter.return_value.all.return_value = (
            mock_recipe_ingredients
        )

        # Act
        result = recommendations_service._get_recipe_ingredients(
            sample_recipe, mock_db_session
        )

        # Assert
        assert result == ["flour", "sugar", "eggs"]
        mock_db_session.query.assert_called_once_with(RecipeIngredient)

    def test_get_recipe_ingredients_with_none_ingredient(
        self,
        recommendations_service: Mock,
        sample_recipe: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test recipe ingredients retrieval with None ingredient."""
        # Arrange
        mock_ingredient = Mock()
        mock_ingredient.name = "flour"  # Set string value, not Mock
        mock_recipe_ingredients = [
            Mock(spec=RecipeIngredient, ingredient=None),  # No ingredient
            # Valid ingredient
            Mock(spec=RecipeIngredient, ingredient=mock_ingredient),
        ]

        mock_db_session.query.return_value.filter.return_value.all.return_value = (
            mock_recipe_ingredients
        )

        # Act
        result = recommendations_service._get_recipe_ingredients(
            sample_recipe, mock_db_session
        )

        # Assert
        assert result == ["flour"]

    def test_get_recipe_ingredients_database_error(
        self,
        recommendations_service: Mock,
        sample_recipe: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test recipe ingredients retrieval with database error."""
        # Arrange
        mock_db_session.query.return_value.filter.return_value.all.side_effect = (
            SQLAlchemyError("Database error")
        )

        # Act
        result = recommendations_service._get_recipe_ingredients(
            sample_recipe, mock_db_session
        )

        # Assert
        assert result == []

    def test_get_recipe_by_id_success(
        self,
        recommendations_service: Mock,
        sample_recipe: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test successful recipe retrieval by ID."""
        # Arrange
        recipe_id = 1
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            sample_recipe
        )

        # Act
        result = recommendations_service._get_recipe_by_id(recipe_id, mock_db_session)

        # Assert
        assert result == sample_recipe
        mock_db_session.query.assert_called_once_with(RecipeModel)

    def test_get_recipe_by_id_not_found(
        self,
        recommendations_service: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test recipe retrieval when recipe is not found."""
        # Arrange
        recipe_id = 999
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            recommendations_service._get_recipe_by_id(recipe_id, mock_db_session)

        assert exc_info.value.status_code == 404
        assert f"Recipe {recipe_id} not found" in str(exc_info.value.detail)

    def test_find_recipes_with_similar_ingredients_success(
        self,
        recommendations_service: Mock,
        sample_recipe: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test finding recipes with similar ingredients."""
        # Mock the result data
        mock_recipe_1 = Mock()
        mock_recipe_1.title = "Similar Recipe 1"
        mock_recipe_1.origin_url = "https://example.com/1"

        mock_recipe_2 = Mock()
        mock_recipe_2.title = "Similar Recipe 2"
        mock_recipe_2.origin_url = None
        mock_recipe_2.recipe_id = 2

        mock_similar_recipes = [(mock_recipe_1, 3), (mock_recipe_2, 2)]

        # Set up the complex mock chain properly
        query_mock = Mock()
        mock_db_session.query.return_value = query_mock

        # Mock the ingredient_id attribute and in_ method to avoid SQLAlchemy errors
        with patch(
            'app.services.recommendations_service.RecipeIngredient'
        ) as mock_recipe_ingredient:
            mock_ingredient_id = Mock()
            mock_recipe_ingredient.ingredient_id = mock_ingredient_id
            mock_ingredient_id.in_.return_value = "mocked_filter"

            # Set up the rest of the query chain
            query_mock.join.return_value = query_mock
            query_mock.filter.return_value = query_mock
            query_mock.group_by.return_value = query_mock
            query_mock.having.return_value = query_mock
            query_mock.order_by.return_value = query_mock
            query_mock.limit.return_value = query_mock
            query_mock.all.return_value = mock_similar_recipes

            # Act
            result = recommendations_service._find_recipes_with_similar_ingredients(
                sample_recipe, mock_db_session, limit=5
            )

            # Assert
            assert len(result) == 2
            assert all(isinstance(recipe, WebRecipe) for recipe in result)
            assert result[0].recipe_name == "Similar Recipe 1"
            assert result[0].url == "https://example.com/1"
            assert result[1].recipe_name == "Similar Recipe 2"
            assert result[1].url == "https://sous-chef-proxy.local/recipes/2"

    def test_find_recipes_with_similar_tags_success(
        self,
        recommendations_service: Mock,
        sample_recipe: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test finding recipes with similar tags."""
        # Mock the result data
        mock_recipe_1 = Mock()
        mock_recipe_1.title = "Tagged Recipe 1"
        mock_recipe_1.origin_url = "https://example.com/tag1"

        mock_recipe_2 = Mock()
        mock_recipe_2.title = "Tagged Recipe 2"
        mock_recipe_2.origin_url = "https://example.com/tag2"

        mock_similar_recipes = [(mock_recipe_1, 2), (mock_recipe_2, 1)]

        # Set up the complex mock chain properly
        query_mock = Mock()
        mock_db_session.query.return_value = query_mock

        # Mock the tag_id attribute and in_ method to avoid SQLAlchemy errors
        with patch(
            'app.services.recommendations_service.RecipeTagJunction'
        ) as mock_recipe_tag_junction:
            mock_tag_id = Mock()
            mock_recipe_tag_junction.tag_id = mock_tag_id
            mock_tag_id.in_.return_value = "mocked_filter"

            # Set up the rest of the query chain
            query_mock.join.return_value = query_mock
            query_mock.filter.return_value = query_mock
            query_mock.group_by.return_value = query_mock
            query_mock.having.return_value = query_mock
            query_mock.order_by.return_value = query_mock
            query_mock.limit.return_value = query_mock
            query_mock.all.return_value = mock_similar_recipes

            # Act
            result = recommendations_service._find_recipes_with_similar_tags(
                sample_recipe, mock_db_session, limit=5
            )

            # Assert
            assert len(result) == 2
            assert all(isinstance(recipe, WebRecipe) for recipe in result)
            assert result[0].recipe_name == "Tagged Recipe 1"
            assert result[1].recipe_name == "Tagged Recipe 2"

    def test_deduplicate_suggestions_success(
        self,
        recommendations_service: Mock,
    ) -> None:
        """Test deduplication of recipe suggestions."""
        # Arrange
        suggestions = [
            WebRecipe(recipe_name="Recipe One", url="https://example.com/1"),
            WebRecipe(recipe_name="Recipe Two", url="https://example.com/2"),
            # Duplicate
            WebRecipe(recipe_name="RECIPE ONE", url="https://example.com/1"),
            # Duplicate with spaces
            WebRecipe(recipe_name=" Recipe Two ", url="https://example.com/2"),
            WebRecipe(recipe_name="Recipe Three", url="https://example.com/3"),
        ]

        # Act
        result = recommendations_service._deduplicate_suggestions(suggestions)

        # Assert
        assert len(result) == 3
        assert result[0].recipe_name == "Recipe One"
        assert result[1].recipe_name == "Recipe Two"
        assert result[2].recipe_name == "Recipe Three"

    def test_deduplicate_suggestions_empty_list(
        self,
        recommendations_service: Mock,
    ) -> None:
        """Test deduplication with empty list."""
        # Act
        result = recommendations_service._deduplicate_suggestions([])

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_get_spoonacular_pairing_suggestions_invalid_cache_data(
        self,
        recommendations_service: Mock,
        sample_recipe: Mock,
        mock_db_session: Mock,
        mock_cache_manager: Mock,
        mock_spoonacular_service: Mock,
    ) -> None:
        """Test Spoonacular pairing suggestions with invalid cache data format."""
        # Arrange
        invalid_cache_data = "invalid_format"  # Not a list

        with patch.object(
            recommendations_service, "_get_recipe_ingredients"
        ) as mock_get_ingredients:
            mock_get_ingredients.return_value = ["flour"]
            mock_cache_manager.get.return_value = invalid_cache_data
            mock_spoonacular_service.search_recipes_by_ingredients.return_value = []

            # Act
            result = await recommendations_service._get_spoonacular_pairing_suggestions(
                sample_recipe, mock_db_session
            )

            # Assert - should return empty list when cache data is invalid
            # and no API results
            assert result == []
