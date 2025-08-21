"""Unit tests for the NutritionalInfo model."""

from datetime import datetime
from decimal import Decimal

import pytest

from app.db.models.nutritional_info_models.nutritional_info import NutritionalInfo
from app.enums.allergen_enum import AllergenEnum
from app.enums.food_group_enum import FoodGroupEnum
from app.enums.ingredient_unit_enum import IngredientUnitEnum


class TestNutritionalInfo:
    """Test cases for NutritionalInfo model."""

    @pytest.mark.unit
    def test_nutritional_info_model_creation_minimal(self) -> None:
        """Test creating a NutritionalInfo instance with minimal required fields."""
        nutritional_info = NutritionalInfo(
            code="1234567890123",
        )

        assert nutritional_info.code == "1234567890123"
        assert nutritional_info.product_name is None
        assert nutritional_info.brands is None

    @pytest.mark.unit
    def test_nutritional_info_model_creation_full(
        self, mock_datetime: datetime
    ) -> None:
        """Test creating a NutritionalInfo instance with all fields."""
        nutritional_info = NutritionalInfo(
            nutritional_info_id=1,
            code="1234567890123",
            product_name="Test Product",
            generic_name="Generic Test Product",
            brands="Test Brand",
            categories="Category 1, Category 2",
            serving_quantity=Decimal("100.0"),
            serving_measurement=IngredientUnitEnum.G,
            allergens=[AllergenEnum.GLUTEN, AllergenEnum.TREE_NUTS],
            food_groups=FoodGroupEnum.GRAINS,
            nutriscore_score=85,
            nutriscore_grade="A",
            energy_kcal_100g=Decimal("250.5"),
            carbohydrates_100g=Decimal("45.2"),
            proteins_100g=Decimal("12.8"),
            fat_100g=Decimal("8.5"),
            fiber_100g=Decimal("3.2"),
            created_at=mock_datetime,
            updated_at=mock_datetime,
        )

        assert nutritional_info.nutritional_info_id == 1
        assert nutritional_info.code == "1234567890123"
        assert nutritional_info.product_name == "Test Product"
        assert nutritional_info.generic_name == "Generic Test Product"
        assert nutritional_info.brands == "Test Brand"
        assert nutritional_info.categories == "Category 1, Category 2"
        assert nutritional_info.serving_quantity == Decimal("100.0")
        assert nutritional_info.serving_measurement == IngredientUnitEnum.G
        assert nutritional_info.allergens == [
            AllergenEnum.GLUTEN,
            AllergenEnum.TREE_NUTS,
        ]
        assert nutritional_info.food_groups == FoodGroupEnum.GRAINS
        assert nutritional_info.nutriscore_score == 85
        assert nutritional_info.nutriscore_grade == "A"
        assert nutritional_info.energy_kcal_100g == Decimal("250.5")
        assert nutritional_info.carbohydrates_100g == Decimal("45.2")
        assert nutritional_info.proteins_100g == Decimal("12.8")
        assert nutritional_info.fat_100g == Decimal("8.5")
        assert nutritional_info.fiber_100g == Decimal("3.2")

    @pytest.mark.unit
    def test_nutritional_info_model_with_allergens(self) -> None:
        """Test creating NutritionalInfo with various allergens."""
        allergen_combinations = [
            [AllergenEnum.GLUTEN],
            [AllergenEnum.TREE_NUTS, AllergenEnum.PEANUTS],
            [AllergenEnum.MILK, AllergenEnum.EGGS, AllergenEnum.SOYBEANS],
            [],  # No allergens
        ]

        for allergens in allergen_combinations:
            nutritional_info = NutritionalInfo(
                code=f"code_{len(allergens)}",
                allergens=allergens,
            )
            assert nutritional_info.allergens == allergens

    @pytest.mark.unit
    def test_nutritional_info_model_with_food_groups(self) -> None:
        """Test creating NutritionalInfo with different food groups."""
        food_groups_to_test = [
            FoodGroupEnum.GRAINS,
            FoodGroupEnum.VEGETABLES,
            FoodGroupEnum.FRUITS,
            FoodGroupEnum.DAIRY,
            FoodGroupEnum.MEAT,
            FoodGroupEnum.SEAFOOD,
            FoodGroupEnum.POULTRY,
        ]

        for food_group in food_groups_to_test:
            nutritional_info = NutritionalInfo(
                code=f"code_{food_group.value}",
                food_groups=food_group,
            )
            assert nutritional_info.food_groups == food_group

    @pytest.mark.unit
    def test_nutritional_info_model_with_serving_measurements(self) -> None:
        """Test creating NutritionalInfo with different serving measurements."""
        measurements_to_test = [
            IngredientUnitEnum.G,
            IngredientUnitEnum.KG,
            IngredientUnitEnum.ML,
            IngredientUnitEnum.L,
            IngredientUnitEnum.CUP,
            IngredientUnitEnum.TBSP,
            IngredientUnitEnum.TSP,
        ]

        for measurement in measurements_to_test:
            nutritional_info = NutritionalInfo(
                code=f"code_{measurement.value}",
                serving_measurement=measurement,
            )
            assert nutritional_info.serving_measurement == measurement

    @pytest.mark.unit
    def test_nutritional_info_model_with_macro_nutrients(self) -> None:
        """Test creating NutritionalInfo with various macro nutrient values."""
        nutritional_info = NutritionalInfo(
            code="macro_test",
            energy_kcal_100g=Decimal("300.25"),
            carbohydrates_100g=Decimal("50.75"),
            cholesterol_100g=Decimal("15.5"),
            proteins_100g=Decimal("20.0"),
            sugars_100g=Decimal("12.5"),
            added_sugars_100g=Decimal("5.0"),
            fat_100g=Decimal("10.25"),
            saturated_fat_100g=Decimal("3.5"),
            fiber_100g=Decimal("8.0"),
        )

        assert nutritional_info.energy_kcal_100g == Decimal("300.25")
        assert nutritional_info.carbohydrates_100g == Decimal("50.75")
        assert nutritional_info.cholesterol_100g == Decimal("15.5")
        assert nutritional_info.proteins_100g == Decimal("20.0")
        assert nutritional_info.sugars_100g == Decimal("12.5")
        assert nutritional_info.added_sugars_100g == Decimal("5.0")
        assert nutritional_info.fat_100g == Decimal("10.25")
        assert nutritional_info.saturated_fat_100g == Decimal("3.5")
        assert nutritional_info.fiber_100g == Decimal("8.0")

    @pytest.mark.unit
    def test_nutritional_info_model_with_fat_types(self) -> None:
        """Test creating NutritionalInfo with various fat types."""
        nutritional_info = NutritionalInfo(
            code="fat_test",
            fat_100g=Decimal("15.0"),
            saturated_fat_100g=Decimal("5.0"),
            monounsaturated_fat_100g=Decimal("6.0"),
            polyunsaturated_fat_100g=Decimal("4.0"),
            omega_3_fat_100g=Decimal("1.5"),
            omega_6_fat_100g=Decimal("2.0"),
            omega_9_fat_100g=Decimal("0.5"),
            trans_fat_100g=Decimal("0.1"),
        )

        assert nutritional_info.fat_100g == Decimal("15.0")
        assert nutritional_info.saturated_fat_100g == Decimal("5.0")
        assert nutritional_info.monounsaturated_fat_100g == Decimal("6.0")
        assert nutritional_info.polyunsaturated_fat_100g == Decimal("4.0")
        assert nutritional_info.omega_3_fat_100g == Decimal("1.5")
        assert nutritional_info.omega_6_fat_100g == Decimal("2.0")
        assert nutritional_info.omega_9_fat_100g == Decimal("0.5")
        assert nutritional_info.trans_fat_100g == Decimal("0.1")

    @pytest.mark.unit
    def test_nutritional_info_model_with_fiber_types(self) -> None:
        """Test creating NutritionalInfo with various fiber types."""
        nutritional_info = NutritionalInfo(
            code="fiber_test",
            fiber_100g=Decimal("8.0"),
            soluble_fiber_100g=Decimal("3.0"),
            insoluble_fiber_100g=Decimal("5.0"),
        )

        assert nutritional_info.fiber_100g == Decimal("8.0")
        assert nutritional_info.soluble_fiber_100g == Decimal("3.0")
        assert nutritional_info.insoluble_fiber_100g == Decimal("5.0")

    @pytest.mark.unit
    def test_nutritional_info_model_with_vitamins(self) -> None:
        """Test creating NutritionalInfo with various vitamins."""
        nutritional_info = NutritionalInfo(
            code="vitamin_test",
            vitamin_a_100g=Decimal("0.001234"),
            vitamin_b6_100g=Decimal("0.002345"),
            vitamin_b12_100g=Decimal("0.000123"),
            vitamin_c_100g=Decimal("0.050000"),
            vitamin_d_100g=Decimal("0.000010"),
            vitamin_e_100g=Decimal("0.015000"),
            vitamin_k_100g=Decimal("0.000080"),
        )

        assert nutritional_info.vitamin_a_100g == Decimal("0.001234")
        assert nutritional_info.vitamin_b6_100g == Decimal("0.002345")
        assert nutritional_info.vitamin_b12_100g == Decimal("0.000123")
        assert nutritional_info.vitamin_c_100g == Decimal("0.050000")
        assert nutritional_info.vitamin_d_100g == Decimal("0.000010")
        assert nutritional_info.vitamin_e_100g == Decimal("0.015000")
        assert nutritional_info.vitamin_k_100g == Decimal("0.000080")

    @pytest.mark.unit
    def test_nutritional_info_model_with_minerals(self) -> None:
        """Test creating NutritionalInfo with various minerals."""
        nutritional_info = NutritionalInfo(
            code="mineral_test",
            calcium_100g=Decimal("120.500000"),
            iron_100g=Decimal("2.500000"),
            magnesium_100g=Decimal("50.000000"),
            potassium_100g=Decimal("300.000000"),
            sodium_100g=Decimal("150.000000"),
            zinc_100g=Decimal("1.200000"),
        )

        assert nutritional_info.calcium_100g == Decimal("120.500000")
        assert nutritional_info.iron_100g == Decimal("2.500000")
        assert nutritional_info.magnesium_100g == Decimal("50.000000")
        assert nutritional_info.potassium_100g == Decimal("300.000000")
        assert nutritional_info.sodium_100g == Decimal("150.000000")
        assert nutritional_info.zinc_100g == Decimal("1.200000")

    @pytest.mark.unit
    def test_nutritional_info_model_with_nutriscore(self) -> None:
        """Test creating NutritionalInfo with various nutriscore values."""
        nutriscore_combinations = [
            (100, "A"),
            (85, "A"),
            (75, "B"),
            (50, "C"),
            (25, "D"),
            (0, "E"),
            (-15, "E"),
        ]

        for score, grade in nutriscore_combinations:
            nutritional_info = NutritionalInfo(
                code=f"nutriscore_{score}",
                nutriscore_score=score,
                nutriscore_grade=grade,
            )
            assert nutritional_info.nutriscore_score == score
            assert nutritional_info.nutriscore_grade == grade

    @pytest.mark.unit
    def test_nutritional_info_model_tablename(self) -> None:
        """Test that the table name is correctly set."""
        nutritional_info = NutritionalInfo(code="test")
        assert nutritional_info.__tablename__ == "nutritional_info"

    @pytest.mark.unit
    def test_nutritional_info_model_table_args(self) -> None:
        """Test that the table args schema is correctly set."""
        nutritional_info = NutritionalInfo(code="test")
        assert nutritional_info.__table_args__ == ({"schema": "recipe_manager"},)

    @pytest.mark.unit
    def test_nutritional_info_model_inheritance(self) -> None:
        """Test that NutritionalInfo inherits from BaseDatabaseModel."""
        from app.db.models.base_database_model import BaseDatabaseModel

        nutritional_info = NutritionalInfo(code="test")
        assert isinstance(nutritional_info, BaseDatabaseModel)

    @pytest.mark.unit
    def test_nutritional_info_model_serialization(
        self, mock_datetime: datetime
    ) -> None:
        """Test that NutritionalInfo can be serialized to JSON."""
        nutritional_info = NutritionalInfo(
            nutritional_info_id=1,
            code="serialization_test",
            product_name="Serialization Test Product",
            allergens=[AllergenEnum.GLUTEN],
            food_groups=FoodGroupEnum.GRAINS,
            energy_kcal_100g=Decimal("250.0"),
            created_at=mock_datetime,
            updated_at=mock_datetime,
        )

        json_str = nutritional_info._to_json()

        # Should contain all the expected fields
        assert '"nutritional_info_id": 1' in json_str
        assert '"code": "serialization_test"' in json_str
        assert '"product_name": "Serialization Test Product"' in json_str
        assert '"allergens": ["GLUTEN"]' in json_str
        assert '"food_groups": "GRAINS"' in json_str

    @pytest.mark.unit
    def test_nutritional_info_model_with_none_values(self) -> None:
        """Test creating NutritionalInfo with None values for optional fields."""
        nutritional_info = NutritionalInfo(
            code="none_test",
            product_name=None,
            brands=None,
            allergens=None,
            food_groups=None,
            nutriscore_score=None,
            energy_kcal_100g=None,
        )

        assert nutritional_info.code == "none_test"
        assert nutritional_info.product_name is None
        assert nutritional_info.brands is None
        assert nutritional_info.allergens is None
        assert nutritional_info.food_groups is None
        assert nutritional_info.nutriscore_score is None
        assert nutritional_info.energy_kcal_100g is None

    @pytest.mark.unit
    def test_nutritional_info_model_with_long_code(self) -> None:
        """Test creating NutritionalInfo with a long code (up to 255 chars)."""
        long_code = "A" * 255
        nutritional_info = NutritionalInfo(code=long_code)

        assert nutritional_info.code == long_code
        assert len(nutritional_info.code) == 255

    @pytest.mark.unit
    def test_nutritional_info_model_with_empty_allergens(self) -> None:
        """Test creating NutritionalInfo with empty allergens list."""
        nutritional_info = NutritionalInfo(
            code="empty_allergens",
            allergens=[],
        )

        assert nutritional_info.allergens == []
