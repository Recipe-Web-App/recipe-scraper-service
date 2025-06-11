"""Base database models and common ORM definitions.

Defines the base classes and common functionality used by all database models in the
application.
"""

import enum
import json

from sqlalchemy.orm import DeclarativeBase


class BaseDatabaseModel(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models.

    Inherits from:
        DeclarativeBase: SQLAlchemy's declarative base class for ORM models.

    This class should be inherited by all ORM models in the application to ensure
    consistent metadata and base functionality.
    """

    def __repr__(self) -> str:
        """Return a string representation of the Recipe instance.

        Returns:
            str: A string representation of the Recipe instance.
        """
        return self._to_json()

    def __str__(self) -> str:
        """Return a string representation of the Recipe instance.

        Returns:
            str: A string representation of the Recipe instance.
        """
        return self._to_json()

    def _to_json(self) -> str:
        """Return a JSON representation of the Recipe instance.

        Returns:
            str: A JSON representation of the Recipe instance.
        """

        def serialize(obj: object) -> object:
            # Handle lists of ORM objects
            if isinstance(obj, list):
                return [serialize(item) for item in obj]
            # Handle enums (must come before __dict__)
            if isinstance(obj, enum.Enum):
                return obj.value
            # Handle ORM objects (with __dict__ and no _sa_instance_state)
            if hasattr(obj, "__dict__"):
                return {
                    k: serialize(v)
                    for k, v in vars(obj).items()
                    if not k.startswith("_sa_instance_state") and not k.startswith("__")
                }
            # Handle UUID, Decimal, datetime, etc.
            if hasattr(obj, "isoformat"):
                return obj.isoformat()
            return obj

        data = serialize(self)
        return json.dumps(data, default=str, ensure_ascii=False)
