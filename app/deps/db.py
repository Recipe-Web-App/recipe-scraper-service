"""Database dependency utilities.

Provides functions and classes to handle database-related dependencies for FastAPI
routes, such as session injection.
"""

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for FastAPI dependency injection.

    This function provides a SQLAlchemy Session instance to FastAPI routes via
    dependency injection. The session is automatically closed after the request is
    handled.

    Yields:     Session: An active SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
