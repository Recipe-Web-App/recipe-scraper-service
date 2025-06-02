"""Recipe Tag Junction model definition.

Defines the data model for a recipe tag junction entity, including its attributes and
any associated ORM configurations.
"""

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base_database_model import BaseDatabaseModel


class RecipeTagJunction(BaseDatabaseModel):
    """SQLAlchemy ORM model for the 'recipe_tag_junction' table.

    Represents the many-to-many relationship between recipes and tags.
    """

    __tablename__ = "recipe_tag_junction"
    __table_args__ = ({"schema": "recipe_manager"},)

    recipe_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("recipe_manager.recipes.recipe_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    tag_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("recipe_manager.recipe_tags.tag_id"),
        primary_key=True,
        nullable=False,
    )
