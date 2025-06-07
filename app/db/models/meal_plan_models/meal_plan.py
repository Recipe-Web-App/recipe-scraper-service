"""Meal Plan model definition.

Defines the data model for a meal plan entity, including its attributes and any
associated ORM configurations.
"""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base_database_model import BaseDatabaseModel

if TYPE_CHECKING:
    from app.db.models.meal_plan_models.meal_plan_recipe import MealPlanRecipe
    from app.db.models.user_models.user import User


class MealPlan(BaseDatabaseModel):
    """SQLAlchemy ORM model for the 'meal_plans' table.

    Represents a meal plan entity with attributes corresponding to the database schema.
    """

    __tablename__ = "meal_plans"
    __table_args__ = ({"schema": "recipe_manager"},)

    meal_plan_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipe_manager.users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    start_date: Mapped[str | None] = mapped_column(
        Date,
        nullable=True,
    )
    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    user: Mapped["User"] = relationship(
        "User",
        lazy="joined",
    )
    meal_plan_recipes: Mapped[list["MealPlanRecipe"]] = relationship(
        "MealPlanRecipe",
        back_populates="meal_plan",
        cascade="all, delete-orphan",
        lazy="joined",
    )
