"""Recipe Step model definition.

Defines the data model for a recipe step entity, including its attributes and any
associated ORM configurations.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base_database_model import BaseDatabaseModel


class RecipeStep(BaseDatabaseModel):
    """SQLAlchemy ORM model for the 'recipe_steps' table.

    Represents a step in a recipe, with attributes corresponding to the database schema.
    """

    __tablename__ = "recipe_steps"
    __table_args__ = ({"schema": "recipe_manager"},)

    step_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    recipe_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("recipe_manager.recipes.recipe_id", ondelete="CASCADE"),
        nullable=False,
    )
    step_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    instruction: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    optional: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    timer_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
