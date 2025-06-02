"""Ingredient model definition.

Defines the data model for an ingredient entity, including its attributes and any
associated ORM configurations.
"""

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base_database_model import BaseDatabaseModel


class Ingredient(BaseDatabaseModel):
    """SQLAlchemy ORM model for the 'ingredients' table.

    Represents an ingredient entity with attributes corresponding to the database
    schema.
    """

    __tablename__ = "ingredients"
    __table_args__ = ({"schema": "recipe_manager"},)

    ingredient_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    is_optional: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
