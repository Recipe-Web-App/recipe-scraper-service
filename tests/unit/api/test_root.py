"""Unit tests for root endpoint.

Tests cover:
- Service name from settings
- Version from settings
- Operational status
- Documentation URL based on environment
- Health endpoint URL based on API prefix
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.api.v1.endpoints.root import root
from app.schemas.root import RootResponse


pytestmark = pytest.mark.unit


class TestRootEndpoint:
    """Tests for root endpoint function."""

    @pytest.mark.asyncio
    async def test_returns_service_name(self) -> None:
        """Should return service name from settings."""
        mock_settings = MagicMock()
        mock_settings.app.name = "Recipe Scraper Service"
        mock_settings.app.version = "2.0.0"
        mock_settings.is_non_production = True
        mock_settings.api.v1_prefix = "/api/v1/recipe-scraper"

        result = await root(mock_settings)

        assert result.service == "Recipe Scraper Service"

    @pytest.mark.asyncio
    async def test_returns_version(self) -> None:
        """Should return version from settings."""
        mock_settings = MagicMock()
        mock_settings.app.name = "Recipe Scraper Service"
        mock_settings.app.version = "2.5.1"
        mock_settings.is_non_production = True
        mock_settings.api.v1_prefix = "/api/v1/recipe-scraper"

        result = await root(mock_settings)

        assert result.version == "2.5.1"

    @pytest.mark.asyncio
    async def test_returns_operational_status(self) -> None:
        """Should return operational status."""
        mock_settings = MagicMock()
        mock_settings.app.name = "Recipe Scraper Service"
        mock_settings.app.version = "2.0.0"
        mock_settings.is_non_production = True
        mock_settings.api.v1_prefix = "/api/v1/recipe-scraper"

        result = await root(mock_settings)

        assert result.status == "operational"

    @pytest.mark.asyncio
    async def test_docs_url_in_non_production(self) -> None:
        """Should return /docs when in non-production environment."""
        mock_settings = MagicMock()
        mock_settings.app.name = "Recipe Scraper Service"
        mock_settings.app.version = "2.0.0"
        mock_settings.is_non_production = True
        mock_settings.api.v1_prefix = "/api/v1/recipe-scraper"

        result = await root(mock_settings)

        assert result.docs == "/docs"

    @pytest.mark.asyncio
    async def test_docs_disabled_in_production(self) -> None:
        """Should return disabled when in production environment."""
        mock_settings = MagicMock()
        mock_settings.app.name = "Recipe Scraper Service"
        mock_settings.app.version = "2.0.0"
        mock_settings.is_non_production = False
        mock_settings.api.v1_prefix = "/api/v1/recipe-scraper"

        result = await root(mock_settings)

        assert result.docs == "disabled"

    @pytest.mark.asyncio
    async def test_health_url_uses_api_prefix(self) -> None:
        """Should return health URL using configured API prefix."""
        mock_settings = MagicMock()
        mock_settings.app.name = "Recipe Scraper Service"
        mock_settings.app.version = "2.0.0"
        mock_settings.is_non_production = True
        mock_settings.api.v1_prefix = "/api/v1/recipe-scraper"

        result = await root(mock_settings)

        assert result.health == "/api/v1/recipe-scraper/health"

    @pytest.mark.asyncio
    async def test_health_url_with_custom_prefix(self) -> None:
        """Should return health URL with custom API prefix."""
        mock_settings = MagicMock()
        mock_settings.app.name = "Recipe Scraper Service"
        mock_settings.app.version = "2.0.0"
        mock_settings.is_non_production = True
        mock_settings.api.v1_prefix = "/api/v2/custom"

        result = await root(mock_settings)

        assert result.health == "/api/v2/custom/health"

    @pytest.mark.asyncio
    async def test_returns_root_response_type(self) -> None:
        """Should return RootResponse instance."""
        mock_settings = MagicMock()
        mock_settings.app.name = "Recipe Scraper Service"
        mock_settings.app.version = "2.0.0"
        mock_settings.is_non_production = True
        mock_settings.api.v1_prefix = "/api/v1/recipe-scraper"

        result = await root(mock_settings)

        assert isinstance(result, RootResponse)
