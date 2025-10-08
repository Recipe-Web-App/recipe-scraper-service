"""Recipe Revision model definition.

Defines the data model for a recipe revision entity, including its attributes and any
associated ORM configurations.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base_database_model import BaseDatabaseModel


class RecipeRevision(BaseDatabaseModel):
    """SQLAlchemy ORM model for the 'recipe_revisions' table.

    Represents a revision of a recipe, with attributes corresponding to the database
    schema.
    """

    __tablename__ = "recipe_revisions"
    __table_args__ = ({"schema": "recipe_manager"},)

    revision_id: Mapped[int] = mapped_column(
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
        PG_UUID(as_uuid=True),
        ForeignKey("recipe_manager.users.user_id"),
        nullable=False,
    )
    revision_category: Mapped[str] = mapped_column(
        SAEnum(
            name="REVISION_CATEGORY_ENUM",
            schema="recipe_manager",
            native_enum=False,
            create_constraint=False,
        ),
        nullable=False,
    )
    revision_type: Mapped[str] = mapped_column(
        SAEnum(
            name="REVISION_TYPE_ENUM",
            schema="recipe_manager",
            native_enum=False,
            create_constraint=False,
        ),
        nullable=False,
    )
    # TODO(jsamuelsen11): Define types to enforce valid JSON structure
    previous_data: Mapped[Any] = mapped_column(
        JSON,
        nullable=False,
    )
    new_data: Mapped[Any] = mapped_column(
        JSON,
        nullable=False,
    )
    change_comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
