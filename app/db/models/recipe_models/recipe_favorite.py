"""Recipe Favorite model definition.

Defines the data model for a recipe favorite entity, including its attributes and any
associated ORM configurations.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base_database_model import BaseDatabaseModel


class RecipeFavorite(BaseDatabaseModel):
    """SQLAlchemy ORM model for the 'recipe_favorites' table.

    Represents a user's favorite recipe, linking users and recipes.
    """

    __tablename__ = "recipe_favorites"
    __table_args__ = ({"schema": "recipe_manager"},)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipe_manager.users.user_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    recipe_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("recipe_manager.recipes.recipe_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    favorited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
