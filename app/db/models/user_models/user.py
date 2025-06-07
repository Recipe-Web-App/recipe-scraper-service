"""User model definition.

Defines the data model for a user entity, including its attributes and any associated
ORM configurations.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base_database_model import BaseDatabaseModel

if TYPE_CHECKING:
    from app.db.models.user_models.user_follow import UserFollow


class User(BaseDatabaseModel):
    """SQLAlchemy ORM model for the 'users' table.

    Represents a user entity with attributes corresponding to the database schema.
    """

    __tablename__ = "users"
    __table_args__ = ({"schema": "recipe_manager"},)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
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
    followers: Mapped[list["UserFollow"]] = relationship(
        "UserFollow",
        foreign_keys="[UserFollow.followee_id]",
        back_populates="followee",
        cascade="all, delete-orphan",
        lazy="joined",
    )
    following: Mapped[list["UserFollow"]] = relationship(
        "UserFollow",
        foreign_keys="[UserFollow.follower_id]",
        back_populates="follower",
        cascade="all, delete-orphan",
        lazy="joined",
    )
