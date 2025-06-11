"""Meal Plan Recipe model definition.

Defines the data model for a meal plan recipe entity, including its attributes and any
associated ORM configurations.
"""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base_database_model import BaseDatabaseModel
from app.enums.meal_type_enum import MealTypeEnum

if TYPE_CHECKING:
    from app.db.models.meal_plan_models.meal_plan import MealPlan


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
    meal_type: Mapped[MealTypeEnum] = mapped_column(
        SAEnum(
            MealTypeEnum,
            name="meal_type_enum",
            schema="recipe_manager",
            native_enum=False,
            create_constraint=False,
        ),
        nullable=False,
    )
    meal_plan: Mapped["MealPlan"] = relationship(
        "MealPlan",
        back_populates="meal_plan_recipes",
        lazy="joined",
    )
