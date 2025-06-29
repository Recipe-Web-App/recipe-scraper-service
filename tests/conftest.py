"""Shared test fixtures and configuration for the Recipe Scraper service tests.

This module provides pytest fixtures that are used across multiple test modules,
including database setup, mock services, and test client configuration.
"""

from decimal import Decimal
from unittest.mock import Mock

import pytest

from app.api.v1.schemas.common.ingredient import Quantity
from app.api.v1.schemas.common.nutritional_info.fats import Fats
from app.api.v1.schemas.common.nutritional_info.fibers import Fibers
from app.api.v1.schemas.common.nutritional_info.ingredient_classification import (
    IngredientClassification,
)
from app.api.v1.schemas.common.nutritional_info.macro_nutrients import MacroNutrients
from app.api.v1.schemas.common.nutritional_info.minerals import Minerals
from app.api.v1.schemas.common.nutritional_info.sugars import Sugars
from app.api.v1.schemas.common.nutritional_info.vitams import Vitamins
from app.api.v1.schemas.response.ingredient_nutritional_info_response import (
    IngredientNutritionalInfoResponse,
)
from app.api.v1.schemas.response.recipe_nutritional_info_response import (
    RecipeNutritionalInfoResponse,
)
from app.enums.allergen_enum import AllergenEnum
from app.enums.food_group_enum import FoodGroupEnum
from app.enums.ingredient_unit_enum import IngredientUnitEnum
from app.services.admin_service import AdminService
from app.services.nutritional_info_service import NutritionalInfoService


@pytest.fixture
def mock_admin_service() -> Mock:
    """Create a mock AdminService for testing.

    Returns:
        Mock: Mocked AdminService instance
    """
    mock_service = Mock(spec=AdminService)
    mock_service.clear_cache.return_value = None
    return mock_service


@pytest.fixture
def mock_cache_manager() -> Mock:
    """Create a mock CacheManager for testing.

    Returns:
        Mock: Mocked CacheManager instance
    """
    mock_cache = Mock()
    mock_cache.clear_all.return_value = None
    return mock_cache


@pytest.fixture
def mock_ingredient_nutritional_info_responses() -> (
    list[IngredientNutritionalInfoResponse]
):
    """Fixture for a list of fully mocked IngredientNutritionalInfoResponse objects."""
    return [
        IngredientNutritionalInfoResponse(
            quantity=Quantity(amount=Decimal(100), measurement=IngredientUnitEnum.G),
            classification=IngredientClassification(
                allergies=[AllergenEnum.GLUTEN, AllergenEnum.PEANUTS],
                food_groups=[FoodGroupEnum.VEGETABLES, FoodGroupEnum.FRUITS],
                nutriscore_score=85,
                nutriscore_grade="A",
                product_name="Mock Ingredient 1",
                brands="Mock Brand",
                categories="Mock Category 1",
            ),
            macro_nutrients=MacroNutrients(
                calories=180,
                carbs_g=Decimal("397.7"),
                cholesterol_mg=Decimal(100),
                protein_g=Decimal("98.8"),
                sugars=Sugars(sugar_g=Decimal("264.4"), added_sugars_g=Decimal("52.2")),
                fats=Fats(
                    fat_g=Decimal("29.9"),
                    saturated_fat_g=Decimal("7.7"),
                    monounsaturated_fat_g=Decimal("9.9"),
                    polyunsaturated_fat_g=Decimal("18.8"),
                    omega_3_fat_g=Decimal("2.21"),
                    omega_6_fat_g=Decimal("7.77"),
                    omega_9_fat_g=Decimal("2.99"),
                    trans_fat_g=Decimal("0.33"),
                ),
                fibers=Fibers(
                    fiber_g=Decimal("122.2"),
                    soluble_fiber_g=Decimal("44.4"),
                    insoluble_fiber_g=Decimal("88.8"),
                ),
            ),
            vitamins=Vitamins(
                vitamin_a_mg=Decimal("9.93"),
                vitamin_b6_mg=Decimal("8.81"),
                vitamin_b12_mg=Decimal("11.1"),
                vitamin_c_mg=Decimal("1379.9"),
                vitamin_d_mg=Decimal("22.2"),
                vitamin_e_mg=Decimal("59.9"),
                vitamin_k_mg=Decimal("0.889"),
            ),
            minerals=Minerals(
                calcium_mg=Decimal(1000),
                iron_mg=Decimal("27.77"),
                magnesium_mg=Decimal(1100),
                potassium_mg=Decimal(23700),
                sodium_mg=Decimal(500),
                zinc_mg=Decimal("17.77"),
            ),
        ),
        IngredientNutritionalInfoResponse(
            quantity=Quantity(amount=Decimal(30), measurement=IngredientUnitEnum.LB),
            classification=IngredientClassification(
                allergies=[AllergenEnum.SHELLFISH],
                food_groups=[FoodGroupEnum.SEAFOOD],
                nutriscore_score=-1,
                nutriscore_grade="B",
                product_name="Mock Ingredient 2",
                brands="Mock Brand 2",
                categories="Mock Category 2",
            ),
            macro_nutrients=MacroNutrients(
                calories=420,
                carbs_g=Decimal("138.8"),
                cholesterol_mg=Decimal(1200),
                protein_g=Decimal("276.6"),
                sugars=Sugars(sugar_g=Decimal("57.7"), added_sugars_g=Decimal("23.3")),
                fats=Fats(
                    fat_g=Decimal("307.7"),
                    saturated_fat_g=Decimal("168.8"),
                    monounsaturated_fat_g=Decimal("129.9"),
                    polyunsaturated_fat_g=Decimal("39.9"),
                    omega_3_fat_g=Decimal("2.99"),
                    omega_6_fat_g=Decimal("11.19"),
                    omega_9_fat_g=Decimal("59.9"),
                    trans_fat_g=Decimal("5.99"),
                ),
                fibers=Fibers(
                    fiber_g=Decimal("22.2"),
                    soluble_fiber_g=Decimal("11.1"),
                    insoluble_fiber_g=Decimal("11.1"),
                ),
            ),
            vitamins=Vitamins(
                vitamin_a_mg=Decimal("27.55"),
                vitamin_b6_mg=Decimal("5.99"),
                vitamin_b12_mg=Decimal("29.99"),
                vitamin_c_mg=Decimal("12.2"),
                vitamin_d_mg=Decimal("17.7"),
                vitamin_e_mg=Decimal("23.3"),
                vitamin_k_mg=Decimal("0.119"),
            ),
            minerals=Minerals(
                calcium_mg=Decimal(8000),
                iron_mg=Decimal("12.99"),
                magnesium_mg=Decimal(800),
                potassium_mg=Decimal(2800),
                sodium_mg=Decimal(7400),
                zinc_mg=Decimal("41.99"),
            ),
        ),
        IngredientNutritionalInfoResponse(
            quantity=Quantity(amount=Decimal(5), measurement=IngredientUnitEnum.TBSP),
            classification=IngredientClassification(
                allergies=[],
                food_groups=[FoodGroupEnum.POULTRY],
                nutriscore_score=2,
                nutriscore_grade="A",
                product_name="Mock Ingredient 3",
                brands="Mock Brand 3",
                categories="Mock Category 3",
            ),
            macro_nutrients=MacroNutrients(
                calories=100,
                carbs_g=Decimal("29.9"),
                cholesterol_mg=Decimal(10),
                protein_g=Decimal("19.9"),
                sugars=Sugars(sugar_g=Decimal("7.7"), added_sugars_g=Decimal("2.2")),
                fats=Fats(
                    fat_g=Decimal("2.3"),
                    saturated_fat_g=Decimal("1.4"),
                    monounsaturated_fat_g=Decimal("1.4"),
                    polyunsaturated_fat_g=Decimal("1.4"),
                    omega_3_fat_g=Decimal("0.222"),
                    omega_6_fat_g=Decimal("0.233"),
                    omega_9_fat_g=Decimal("0.255"),
                    trans_fat_g=Decimal("0.11"),
                ),
                fibers=Fibers(
                    fiber_g=Decimal("7.7"),
                    soluble_fiber_g=Decimal("2.3"),
                    insoluble_fiber_g=Decimal("4.7"),
                ),
            ),
            vitamins=Vitamins(
                vitamin_a_mg=Decimal("2.33"),
                vitamin_b6_mg=Decimal("2.11"),
                vitamin_b12_mg=Decimal("1.1"),
                vitamin_c_mg=Decimal("28.8"),
                vitamin_d_mg=Decimal("2.2"),
                vitamin_e_mg=Decimal("2.11"),
                vitamin_k_mg=Decimal("0.114"),
            ),
            minerals=Minerals(
                calcium_mg=Decimal(200),
                iron_mg=Decimal("2.33"),
                magnesium_mg=Decimal(100),
                potassium_mg=Decimal(1500),
                sodium_mg=Decimal(20),
                zinc_mg=Decimal("2.11"),
            ),
        ),
    ]


@pytest.fixture
def mock_ingredient_nutritional_info_response(
    mock_ingredient_nutritional_info_responses: list[IngredientNutritionalInfoResponse],
) -> IngredientNutritionalInfoResponse:
    """Fixture for a mocked IngredientNutritionalInfoResponse."""
    return mock_ingredient_nutritional_info_responses[0]


@pytest.fixture
def mock_recipe_nutritional_info_response(
    mock_ingredient_nutritional_info_responses: list[IngredientNutritionalInfoResponse],
) -> RecipeNutritionalInfoResponse:
    """Fixture for a mocked RecipeNutritionalInfoResponse including all ingredients."""
    mock_ingredient_nutritional_info_dict = {}
    for i in range(len(mock_ingredient_nutritional_info_responses)):
        mock_ingredient_nutritional_info_dict[i] = (
            mock_ingredient_nutritional_info_responses[i]
        )
    return RecipeNutritionalInfoResponse(
        ingredients=mock_ingredient_nutritional_info_dict,
    )


@pytest.fixture
def mock_recipe_nutritional_info_response_with_missing_ingredients(
    mock_recipe_nutritional_info_response: RecipeNutritionalInfoResponse,
) -> RecipeNutritionalInfoResponse:
    """Fixture for a mocked RecipeNutritionalInfoResponse with missing ingredients."""
    ingredients = mock_recipe_nutritional_info_response.ingredients
    ingredients_len = 0 if ingredients is None else len(ingredients)
    return RecipeNutritionalInfoResponse(
        missing_ingredients=[
            ingredients_len,
            ingredients_len + 1,
        ],
        ingredients=ingredients,
    )


@pytest.fixture
def mock_quantity() -> Quantity:
    """Fixture for a mocked Quantity object."""
    return Quantity(amount=Decimal(100), measurement=IngredientUnitEnum.G)


@pytest.fixture
def mock_nutritional_info_service(
    mock_recipe_nutritional_info_response: RecipeNutritionalInfoResponse,
    mock_ingredient_nutritional_info_response: IngredientNutritionalInfoResponse,
) -> Mock:
    """Fixture for a mocked NutritionalInfoService with a preset return value."""
    mock = Mock(spec=NutritionalInfoService)
    mock.get_recipe_nutritional_info.return_value = (
        mock_recipe_nutritional_info_response
    )
    mock.get_ingredient_nutritional_info.return_value = (
        mock_ingredient_nutritional_info_response
    )
    return mock
