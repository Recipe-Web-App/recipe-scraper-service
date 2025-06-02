"""Base database models and common ORM definitions.

Defines the base classes and common functionality used by all database models in the
application.
"""

from sqlalchemy.orm import DeclarativeBase


class BaseDatabaseModel(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models.

    Inherits from:
        DeclarativeBase: SQLAlchemy's declarative base class for ORM models.

    This class should be inherited by all ORM models in the application to ensure
    consistent metadata and base functionality.
    """
