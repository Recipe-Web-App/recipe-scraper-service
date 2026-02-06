"""Unit tests for application entry point.

Tests cover:
- Application instance creation
- Module structure verification
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI


pytestmark = pytest.mark.unit


class TestApplicationInstance:
    """Tests for main application instance."""

    def test_app_is_fastapi_instance(self) -> None:
        """Test that app is a FastAPI instance."""
        from app.main import app

        assert isinstance(app, FastAPI)

    def test_app_has_title(self) -> None:
        """Test that app has a title configured."""
        from app.main import app

        assert app.title is not None
        assert len(app.title) > 0

    def test_app_has_version(self) -> None:
        """Test that app has a version."""
        from app.main import app

        assert app.version is not None
