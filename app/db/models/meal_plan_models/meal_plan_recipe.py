"""Meal Plan Recipe model definition.

Defines the data model for a meal plan recipe entity, including its attributes and any
associated ORM configurations.
"""

from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base_database_model import BaseDatabaseModel


class MealPlanRecipe(BaseDatabaseModel):
    """SQLAlchemy ORM model for the 'meal_plan_recipes' table.

    Represents the association between a meal plan and a recipe for a specific date and
    meal type.
    """

    __tablename__ = "meal_plan_recipes"
    __table_args__ = ({"schema": "recipe_manager"},)

    meal_plan_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("recipe_manager.meal_plans.meal_plan_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    recipe_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("recipe_manager.recipes.recipe_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    meal_date: Mapped[date] = mapped_column(
        Date,
        primary_key=True,
        nullable=False,
    )
    meal_type: Mapped[str] = mapped_column(
        # This assumes the ENUM is already created in the DB.
        "MEAL_TYPE_ENUM",
        nullable=False,
    )
