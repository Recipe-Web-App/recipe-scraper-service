"""Recipe Review model definition.

Defines the data model for a recipe review entity, including its attributes and any
associated ORM configurations.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base_database_model import BaseDatabaseModel


class RecipeReview(BaseDatabaseModel):
    """SQLAlchemy ORM model for the 'reviews' table.

    Represents a recipe review entity with attributes corresponding to the database
    schema.
    """

    __tablename__ = "reviews"
    __table_args__ = ({"schema": "recipe_manager"},)

    review_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    recipe_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("recipe_manager.recipes.recipe_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipe_manager.users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    rating: Mapped[Decimal] = mapped_column(
        Numeric(2, 1),
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
