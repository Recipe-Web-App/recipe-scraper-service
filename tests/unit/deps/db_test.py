"""Unit tests for the database dependency utilities."""

from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.deps.db import get_db


class TestDbDependencies:
    """Unit tests for database dependency functions."""

    @pytest.mark.unit
    def test_get_db_yields_session(self) -> None:
        """Test that get_db yields a Session instance."""
        # Arrange
        mock_session = Mock(spec=Session)
        mock_session_local = Mock(return_value=mock_session)

        # Act & Assert
        with patch("app.deps.db.SessionLocal", mock_session_local):
            generator = get_db()
            session = next(generator)

            assert session == mock_session
            mock_session_local.assert_called_once()

    @pytest.mark.unit
    def test_get_db_closes_session(self) -> None:
        """Test that get_db properly closes the session."""
        # Arrange
        mock_session = Mock(spec=Session)
        mock_session_local = Mock(return_value=mock_session)

        # Act
        with patch("app.deps.db.SessionLocal", mock_session_local):
            generator = get_db()
            next(generator)

            # Simulate completion by exhausting the generator
            try:
                next(generator)
            except StopIteration:
                pass

            # Assert
            mock_session.close.assert_called_once()

    @pytest.mark.unit
    def test_get_db_closes_session_on_exception(self) -> None:
        """Test that get_db closes session even when an exception occurs."""
        # Arrange
        mock_session = Mock(spec=Session)
        mock_session_local = Mock(return_value=mock_session)

        # Act
        with patch("app.deps.db.SessionLocal", mock_session_local):
            generator = get_db()
            next(generator)

            # Simulate an exception by calling close on the generator
            generator.close()

            # Assert
            mock_session.close.assert_called_once()

    @pytest.mark.unit
    def test_get_db_is_generator(self) -> None:
        """Test that get_db returns a generator."""
        # Arrange & Act
        with patch("app.deps.db.SessionLocal"):
            result = get_db()

            # Assert
            assert hasattr(result, "__next__")
            assert hasattr(result, "__iter__")
            assert result.__class__.__name__ == "generator"
