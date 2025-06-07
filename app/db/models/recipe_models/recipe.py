"""Recipe model definition.

Defines the data model for a recipe entity, capturing the necessary fields and
relationships for storing recipes.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base_database_model import BaseDatabaseModel
from app.enums.difficulty_level_enum import DifficultyLevelEnum

if TYPE_CHECKING:
    from app.db.models.recipe_models.recipe_ingredient import RecipeIngredient
    from app.db.models.recipe_models.recipe_review import RecipeReview
    from app.db.models.recipe_models.recipe_step import RecipeStep
    from app.db.models.recipe_models.recipe_tag_junction import RecipeTagJunction


class Recipe(BaseDatabaseModel):
    """SQLAlchemy ORM model for the 'recipes' table.

    Represents a recipe entity with attributes corresponding to the database schema.
    """

    __tablename__ = "recipes"
    __table_args__ = ({"schema": "recipe_manager"},)

    recipe_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipe_manager.users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    origin_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    servings: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    preparation_time: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    cooking_time: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    difficulty: Mapped[DifficultyLevelEnum | None] = mapped_column(
        SAEnum(
            DifficultyLevelEnum,
            name="difficulty_level_enum",
            schema="recipe_manager",
            native_enum=False,
            create_constraint=False,
        ),
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
    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        "RecipeIngredient",
        back_populates="recipe",
        cascade="all, delete-orphan",
        lazy="joined",
    )
    steps: Mapped[list["RecipeStep"]] = relationship(
        "RecipeStep",
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="RecipeStep.step_number",
        lazy="joined",
    )
    tags: Mapped[list["RecipeTagJunction"]] = relationship(
        "RecipeTagJunction",
        back_populates="recipe",
        cascade="all, delete-orphan",
        lazy="joined",
    )
    reviews: Mapped[list["RecipeReview"]] = relationship(
        "RecipeReview",
        back_populates="recipe",
        cascade="all, delete-orphan",
        lazy="joined",
    )
