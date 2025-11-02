"""Recipe Comment model definition.

Defines the data model for a recipe comment entity, including its attributes and any
associated ORM configurations.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base_database_model import BaseDatabaseModel

if TYPE_CHECKING:
    from app.db.models.recipe_models.recipe import Recipe


class RecipeComment(BaseDatabaseModel):
    """SQLAlchemy ORM model for the 'recipe_comments' table.

    Represents a recipe comment entity with attributes corresponding to the database
    schema.
    """

    __tablename__ = "recipe_comments"
    __table_args__ = ({"schema": "recipe_manager"},)

    comment_id: Mapped[int] = mapped_column(
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
    comment_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
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
    recipe: Mapped["Recipe"] = relationship(
        "Recipe",
        back_populates="comments",
        lazy="joined",
    )
