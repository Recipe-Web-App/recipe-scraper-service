"""Unit tests for the MealPlan model."""

import uuid
from datetime import date, datetime

import pytest

from app.db.models.meal_plan_models.meal_plan import MealPlan


class TestMealPlan:
    """Test cases for MealPlan model."""

    @pytest.mark.unit
    def test_meal_plan_model_creation(
        self, mock_user_id: uuid.UUID, mock_datetime: datetime
    ) -> None:
        """Test creating a MealPlan instance with all fields."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 7)

        meal_plan = MealPlan(
            meal_plan_id=1,
            user_id=mock_user_id,
            name="Weekly Meal Plan",
            description="A weekly meal plan for testing",
            start_date=start_date,
            end_date=end_date,
            created_at=mock_datetime,
            updated_at=mock_datetime,
        )

        assert meal_plan.meal_plan_id == 1
        assert meal_plan.user_id == mock_user_id
        assert meal_plan.name == "Weekly Meal Plan"
        assert meal_plan.description == "A weekly meal plan for testing"
        assert meal_plan.start_date == start_date
        assert meal_plan.end_date == end_date
        assert meal_plan.created_at == mock_datetime
        assert meal_plan.updated_at == mock_datetime

    @pytest.mark.unit
    def test_meal_plan_model_creation_minimal(self, mock_user_id: uuid.UUID) -> None:
        """Test creating a MealPlan instance with minimal required fields."""
        meal_plan = MealPlan(
            user_id=mock_user_id,
            name="Minimal Meal Plan",
        )

        assert meal_plan.user_id == mock_user_id
        assert meal_plan.name == "Minimal Meal Plan"
        assert meal_plan.description is None
        assert meal_plan.start_date is None
        assert meal_plan.end_date is None

    @pytest.mark.unit
    def test_meal_plan_model_with_none_description(
        self, mock_user_id: uuid.UUID
    ) -> None:
        """Test creating a MealPlan instance with None description."""
        meal_plan = MealPlan(
            user_id=mock_user_id,
            name="No Description Plan",
            description=None,
        )

        assert meal_plan.name == "No Description Plan"
        assert meal_plan.description is None

    @pytest.mark.unit
    def test_meal_plan_model_with_date_range(self, mock_user_id: uuid.UUID) -> None:
        """Test creating MealPlan instances with various date ranges."""
        date_ranges = [
            (date(2024, 1, 1), date(2024, 1, 7)),  # 1 week
            (date(2024, 2, 1), date(2024, 2, 29)),  # 1 month (leap year)
            (date(2024, 1, 1), date(2024, 12, 31)),  # 1 year
            (date(2024, 6, 15), date(2024, 6, 15)),  # single day
        ]

        for start_date, end_date in date_ranges:
            meal_plan = MealPlan(
                user_id=mock_user_id,
                name=f"Plan {start_date} to {end_date}",
                start_date=start_date,
                end_date=end_date,
            )
            assert meal_plan.start_date == start_date
            assert meal_plan.end_date == end_date

    @pytest.mark.unit
    def test_meal_plan_model_with_only_start_date(
        self, mock_user_id: uuid.UUID
    ) -> None:
        """Test creating MealPlan with only start date."""
        start_date = date(2024, 1, 1)
        meal_plan = MealPlan(
            user_id=mock_user_id,
            name="Start Date Only Plan",
            start_date=start_date,
            end_date=None,
        )

        assert meal_plan.start_date == start_date
        assert meal_plan.end_date is None

    @pytest.mark.unit
    def test_meal_plan_model_with_only_end_date(self, mock_user_id: uuid.UUID) -> None:
        """Test creating MealPlan with only end date."""
        end_date = date(2024, 1, 7)
        meal_plan = MealPlan(
            user_id=mock_user_id,
            name="End Date Only Plan",
            start_date=None,
            end_date=end_date,
        )

        assert meal_plan.start_date is None
        assert meal_plan.end_date == end_date

    @pytest.mark.unit
    def test_meal_plan_model_tablename(self, mock_user_id: uuid.UUID) -> None:
        """Test that the table name is correctly set."""
        meal_plan = MealPlan(user_id=mock_user_id, name="Test")
        assert meal_plan.__tablename__ == "meal_plans"

    @pytest.mark.unit
    def test_meal_plan_model_table_args(self, mock_user_id: uuid.UUID) -> None:
        """Test that the table args schema is correctly set."""
        meal_plan = MealPlan(user_id=mock_user_id, name="Test")
        assert meal_plan.__table_args__ == ({"schema": "recipe_manager"},)

    @pytest.mark.unit
    def test_meal_plan_model_inheritance(self, mock_user_id: uuid.UUID) -> None:
        """Test that MealPlan inherits from BaseDatabaseModel."""
        from app.db.models.base_database_model import BaseDatabaseModel

        meal_plan = MealPlan(user_id=mock_user_id, name="Test")
        assert isinstance(meal_plan, BaseDatabaseModel)

    @pytest.mark.unit
    def test_meal_plan_model_serialization(
        self, mock_user_id: uuid.UUID, mock_datetime: datetime
    ) -> None:
        """Test that MealPlan can be serialized to JSON."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 7)

        meal_plan = MealPlan(
            meal_plan_id=1,
            user_id=mock_user_id,
            name="Serialization Test Plan",
            description="Test meal plan for serialization",
            start_date=start_date,
            end_date=end_date,
            created_at=mock_datetime,
            updated_at=mock_datetime,
        )

        json_str = meal_plan._to_json()

        # Should contain all the expected fields
        assert '"meal_plan_id": 1' in json_str
        assert '"name": "Serialization Test Plan"' in json_str
        assert '"description": "Test meal plan for serialization"' in json_str
        assert '"start_date":' in json_str
        assert '"end_date":' in json_str

    @pytest.mark.unit
    def test_meal_plan_model_string_representation(
        self, mock_user_id: uuid.UUID
    ) -> None:
        """Test string representation of MealPlan model."""
        meal_plan = MealPlan(
            meal_plan_id=1,
            user_id=mock_user_id,
            name="String Test Plan",
        )

        str_repr = str(meal_plan)

        # Should be a JSON string representation
        assert '"meal_plan_id": 1' in str_repr
        assert '"name": "String Test Plan"' in str_repr

    @pytest.mark.unit
    def test_meal_plan_model_repr(self, mock_user_id: uuid.UUID) -> None:
        """Test repr representation of MealPlan model."""
        meal_plan = MealPlan(
            meal_plan_id=1,
            user_id=mock_user_id,
            name="Repr Test Plan",
        )

        repr_str = repr(meal_plan)

        # Should be a JSON string representation
        assert '"meal_plan_id": 1' in repr_str
        assert '"name": "Repr Test Plan"' in repr_str

    @pytest.mark.unit
    def test_meal_plan_model_relationships(self, mock_user_id: uuid.UUID) -> None:
        """Test that the relationships are properly configured."""
        meal_plan = MealPlan(user_id=mock_user_id, name="Relationship Test")

        # Relationships should be configured but initially None/empty
        assert hasattr(meal_plan, 'user')
        assert hasattr(meal_plan, 'meal_plan_recipes')
        assert meal_plan.meal_plan_recipes == []

    @pytest.mark.unit
    def test_meal_plan_model_with_long_name(self, mock_user_id: uuid.UUID) -> None:
        """Test creating a MealPlan with a long name (up to 255 chars)."""
        long_name = "A" * 255
        meal_plan = MealPlan(user_id=mock_user_id, name=long_name)

        assert meal_plan.name == long_name
        assert len(meal_plan.name) == 255

    @pytest.mark.unit
    def test_meal_plan_model_with_long_description(
        self, mock_user_id: uuid.UUID
    ) -> None:
        """Test creating a MealPlan with a long description."""
        long_description = "This is a very long description. " * 100
        meal_plan = MealPlan(
            user_id=mock_user_id,
            name="Long Description Plan",
            description=long_description,
        )

        assert meal_plan.name == "Long Description Plan"
        assert meal_plan.description == long_description

    @pytest.mark.unit
    def test_meal_plan_model_with_future_dates(self, mock_user_id: uuid.UUID) -> None:
        """Test creating MealPlan with future dates."""
        start_date = date(2025, 12, 1)
        end_date = date(2025, 12, 31)

        meal_plan = MealPlan(
            user_id=mock_user_id,
            name="Future Plan",
            start_date=start_date,
            end_date=end_date,
        )

        assert meal_plan.start_date == start_date
        assert meal_plan.end_date == end_date

    @pytest.mark.unit
    def test_meal_plan_model_with_past_dates(self, mock_user_id: uuid.UUID) -> None:
        """Test creating MealPlan with past dates."""
        start_date = date(2020, 1, 1)
        end_date = date(2020, 1, 7)

        meal_plan = MealPlan(
            user_id=mock_user_id,
            name="Past Plan",
            start_date=start_date,
            end_date=end_date,
        )

        assert meal_plan.start_date == start_date
        assert meal_plan.end_date == end_date
