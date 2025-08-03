"""Base database models and common ORM definitions.

Defines the base classes and common functionality used by all database models in the
application.
"""

import enum
import json

from sqlalchemy.orm import DeclarativeBase


class BaseDatabaseModel(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models.

    Inherits from:     DeclarativeBase: SQLAlchemy's declarative base class for ORM
    models.

    This class should be inherited by all ORM models in the application to ensure
    consistent metadata and base functionality.
    """

    def __repr__(self) -> str:
        """Return a string representation of the Recipe instance.

        Returns:     str: A string representation of the Recipe instance.
        """
        return self._to_json()

    def __str__(self) -> str:
        """Return a string representation of the Recipe instance.

        Returns:     str: A string representation of the Recipe instance.
        """
        return self._to_json()

    def _to_json(self) -> str:
        """Return a JSON representation of the Recipe instance.

        Returns:     str: A JSON representation of the Recipe instance.
        """
        data = self._serialize(self)
        return json.dumps(data, default=str, ensure_ascii=False)

    @staticmethod
    def _get_circular_ref_repr(obj: object) -> str:
        """Get a simple representation for circular references."""
        if hasattr(obj, "__tablename__"):
            # Try to find a primary key field to use as identifier
            primary_key_value = "unknown"
            for attr_name in dir(obj):
                if attr_name.endswith("_id") and not attr_name.startswith("_"):
                    try:
                        primary_key_value = getattr(obj, attr_name, "unknown")
                        break
                    except (AttributeError, TypeError):
                        # Skip attributes that can't be accessed
                        continue

            table_name = getattr(obj, "__tablename__", "UnknownTable")
            class_name = obj.__class__.__name__
            return f"<{class_name}({table_name}, id={primary_key_value})>"
        return f"<circular_ref:{type(obj).__name__}>"

    @staticmethod
    def _serialize(obj: object, visited: set[int] | None = None) -> object:
        if visited is None:
            visited = set()

        # Prevent infinite recursion by tracking visited objects
        obj_id = id(obj)
        if obj_id in visited:
            return BaseDatabaseModel._get_circular_ref_repr(obj)

        visited.add(obj_id)

        try:
            # Handle lists of ORM objects
            if isinstance(obj, list):
                return [BaseDatabaseModel._serialize(item, visited) for item in obj]
            # Handle enums (must come before __dict__)
            if isinstance(obj, enum.Enum):
                return obj.value
            # Handle ORM objects (with __dict__ and no _sa_instance_state)
            if hasattr(obj, "__dict__"):
                return {
                    k: BaseDatabaseModel._serialize(v, visited)
                    for k, v in vars(obj).items()
                    if not k.startswith("_sa_instance_state") and not k.startswith("__")
                }
            # Handle UUID, Decimal, datetime, etc.
            if hasattr(obj, "isoformat"):
                return obj.isoformat()
            return obj
        finally:
            visited.remove(obj_id)
