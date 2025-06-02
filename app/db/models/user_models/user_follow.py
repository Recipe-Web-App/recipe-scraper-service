"""User Follow model definition.

Defines the data model for a user follow entity, including its attributes and any
associated ORM configurations.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base_database_model import BaseDatabaseModel


class UserFollow(BaseDatabaseModel):
    """SQLAlchemy ORM model for the 'user_follows' table.

    Represents a user follow relationship between two users.
    """

    __tablename__ = "user_follows"
    __table_args__ = ({"schema": "recipe_manager"},)

    follower_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipe_manager.users.user_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    followee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipe_manager.users.user_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    followed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
