"""Unit tests for OpenFoodFactsClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.clients.open_food_facts.client import (
    OFF_TAG_MAPPING,
    OpenFoodFactsAllergen,
    OpenFoodFactsClient,
    OpenFoodFactsProduct,
)
from app.schemas.enums import Allergen


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_cache_client() -> MagicMock:
    """Create mock Redis cache client."""
    client = MagicMock()
    client.get = AsyncMock(return_value=None)
    client.setex = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Create mock httpx AsyncClient."""
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock()
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def client(
    mock_cache_client: MagicMock,
    mock_http_client: MagicMock,
) -> OpenFoodFactsClient:
    """Create OpenFoodFactsClient with mocked dependencies."""
    return OpenFoodFactsClient(
        cache_client=mock_cache_client,
        http_client=mock_http_client,
    )


@pytest.fixture
def sample_off_response() -> dict[str, object]:
    """Create sample Open Food Facts API response."""
    return {
        "products": [
            {
                "product_name": "Wheat Flour",
                "allergens_tags": ["en:gluten", "en:wheat"],
                "traces_tags": ["en:nuts", "en:sesame-seeds"],
            }
        ]
    }


class TestOffTagMapping:
    """Tests for OFF_TAG_MAPPING constant."""

    def test_contains_major_allergens(self) -> None:
        """Should map major allergens."""
        assert OFF_TAG_MAPPING["en:gluten"] == Allergen.GLUTEN
        assert OFF_TAG_MAPPING["en:milk"] == Allergen.MILK
        assert OFF_TAG_MAPPING["en:eggs"] == Allergen.EGGS
        assert OFF_TAG_MAPPING["en:peanuts"] == Allergen.PEANUTS

    def test_maps_shellfish_variants(self) -> None:
        """Should map both crustaceans and molluscs to SHELLFISH."""
        assert OFF_TAG_MAPPING["en:crustaceans"] == Allergen.SHELLFISH
        assert OFF_TAG_MAPPING["en:molluscs"] == Allergen.SHELLFISH


class TestOpenFoodFactsAllergen:
    """Tests for OpenFoodFactsAllergen dataclass."""

    def test_creation(self) -> None:
        """Should create with allergen and presence_type."""
        allergen = OpenFoodFactsAllergen(
            allergen=Allergen.GLUTEN,
            presence_type="CONTAINS",
        )
        assert allergen.allergen == Allergen.GLUTEN
        assert allergen.presence_type == "CONTAINS"

    def test_is_frozen(self) -> None:
        """Should be immutable."""
        allergen = OpenFoodFactsAllergen(
            allergen=Allergen.MILK,
            presence_type="MAY_CONTAIN",
        )
        with pytest.raises(AttributeError):
            allergen.presence_type = "CONTAINS"  # type: ignore[misc]


class TestOpenFoodFactsProduct:
    """Tests for OpenFoodFactsProduct dataclass."""

    def test_creation(self) -> None:
        """Should create with product_name and allergens."""
        product = OpenFoodFactsProduct(
            product_name="Test Product",
            allergens=(
                OpenFoodFactsAllergen(Allergen.GLUTEN, "CONTAINS"),
                OpenFoodFactsAllergen(Allergen.MILK, "MAY_CONTAIN"),
            ),
        )
        assert product.product_name == "Test Product"
        assert len(product.allergens) == 2


class TestClientLifecycle:
    """Tests for client lifecycle methods."""

    async def test_initialize_creates_http_client(self) -> None:
        """Should create HTTP client on initialize if not provided."""
        client = OpenFoodFactsClient()
        assert client._http is None

        await client.initialize()
        assert client._http is not None

        await client.shutdown()

    async def test_shutdown_closes_owned_client(self) -> None:
        """Should close HTTP client if we own it."""
        client = OpenFoodFactsClient()
        await client.initialize()
        assert client._http is not None

        await client.shutdown()
        assert client._http is None

    async def test_shutdown_preserves_injected_client(
        self,
        mock_http_client: MagicMock,
    ) -> None:
        """Should not close HTTP client if injected."""
        client = OpenFoodFactsClient(http_client=mock_http_client)
        await client.shutdown()

        mock_http_client.aclose.assert_not_called()


class TestSearchByName:
    """Tests for search_by_name method."""

    async def test_returns_none_when_http_not_initialized(
        self,
        mock_cache_client: MagicMock,
    ) -> None:
        """Should return None if HTTP client not initialized."""
        client = OpenFoodFactsClient(cache_client=mock_cache_client)

        result = await client.search_by_name("flour")

        assert result is None

    async def test_returns_cached_product(
        self,
        client: OpenFoodFactsClient,
        mock_cache_client: MagicMock,
    ) -> None:
        """Should return cached product if available."""
        cached_data = (
            b'{"product_name":"Cached","allergens":'
            b'[{"allergen":"GLUTEN","presence_type":"CONTAINS"}]}'
        )
        mock_cache_client.get.return_value = cached_data

        result = await client.search_by_name("flour")

        assert result is not None
        assert result.product_name == "Cached"
        assert result.allergens[0].allergen == Allergen.GLUTEN

    async def test_returns_product_from_api(
        self,
        client: OpenFoodFactsClient,
        mock_http_client: MagicMock,
        sample_off_response: dict[str, object],
    ) -> None:
        """Should fetch and return product from API."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_off_response
        mock_response.raise_for_status = MagicMock()
        mock_http_client.get.return_value = mock_response

        result = await client.search_by_name("flour")

        assert result is not None
        assert result.product_name == "Wheat Flour"
        allergen_types = {a.allergen for a in result.allergens}
        assert Allergen.GLUTEN in allergen_types
        assert Allergen.WHEAT in allergen_types

    async def test_returns_none_when_no_products(
        self,
        client: OpenFoodFactsClient,
        mock_http_client: MagicMock,
    ) -> None:
        """Should return None when API returns no products."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"products": []}
        mock_response.raise_for_status = MagicMock()
        mock_http_client.get.return_value = mock_response

        result = await client.search_by_name("nonexistent")

        assert result is None

    async def test_returns_none_on_http_error(
        self,
        client: OpenFoodFactsClient,
        mock_http_client: MagicMock,
    ) -> None:
        """Should return None on HTTP error."""
        mock_http_client.get.side_effect = httpx.HTTPError("Connection failed")

        result = await client.search_by_name("flour")

        assert result is None

    async def test_caches_successful_response(
        self,
        client: OpenFoodFactsClient,
        mock_http_client: MagicMock,
        mock_cache_client: MagicMock,
        sample_off_response: dict[str, object],
    ) -> None:
        """Should cache product with allergens."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_off_response
        mock_response.raise_for_status = MagicMock()
        mock_http_client.get.return_value = mock_response

        await client.search_by_name("flour")

        mock_cache_client.setex.assert_called_once()


class TestParseProduct:
    """Tests for _parse_product method."""

    def test_parses_allergens_tags(self) -> None:
        """Should parse allergens_tags as CONTAINS."""
        client = OpenFoodFactsClient()
        product_data = {
            "product_name": "Test",
            "allergens_tags": ["en:gluten", "en:milk"],
            "traces_tags": [],
        }

        result = client._parse_product(product_data)

        assert len(result.allergens) == 2
        for allergen in result.allergens:
            assert allergen.presence_type == "CONTAINS"

    def test_parses_traces_tags(self) -> None:
        """Should parse traces_tags as MAY_CONTAIN."""
        client = OpenFoodFactsClient()
        product_data = {
            "product_name": "Test",
            "allergens_tags": [],
            "traces_tags": ["en:nuts", "en:sesame-seeds"],
        }

        result = client._parse_product(product_data)

        assert len(result.allergens) == 2
        for allergen in result.allergens:
            assert allergen.presence_type == "MAY_CONTAIN"

    def test_ignores_unknown_tags(self) -> None:
        """Should ignore unknown allergen tags."""
        client = OpenFoodFactsClient()
        product_data = {
            "product_name": "Test",
            "allergens_tags": ["en:unknown-tag", "en:gluten"],
            "traces_tags": [],
        }

        result = client._parse_product(product_data)

        assert len(result.allergens) == 1
        assert result.allergens[0].allergen == Allergen.GLUTEN

    def test_deduplicates_allergens(self) -> None:
        """Should not duplicate allergens in both contains and traces."""
        client = OpenFoodFactsClient()
        product_data = {
            "product_name": "Test",
            "allergens_tags": ["en:gluten"],
            "traces_tags": ["en:gluten"],  # Duplicate
        }

        result = client._parse_product(product_data)

        assert len(result.allergens) == 1
        assert result.allergens[0].presence_type == "CONTAINS"

    def test_handles_missing_fields(self) -> None:
        """Should handle missing allergen fields."""
        client = OpenFoodFactsClient()
        product_data = {
            "product_name": "Test",
        }

        result = client._parse_product(product_data)

        assert result.product_name == "Test"
        assert result.allergens == ()


class TestSerialization:
    """Tests for cache serialization/deserialization."""

    def test_round_trip(self) -> None:
        """Should serialize and deserialize correctly."""
        client = OpenFoodFactsClient()
        original = OpenFoodFactsProduct(
            product_name="Test Product",
            allergens=(
                OpenFoodFactsAllergen(Allergen.GLUTEN, "CONTAINS"),
                OpenFoodFactsAllergen(Allergen.MILK, "MAY_CONTAIN"),
            ),
        )

        serialized = client._serialize(original)
        deserialized = client._deserialize(serialized)

        assert deserialized.product_name == original.product_name
        assert len(deserialized.allergens) == len(original.allergens)
        assert deserialized.allergens[0].allergen == Allergen.GLUTEN
        assert deserialized.allergens[1].allergen == Allergen.MILK


class TestParseProductEdgeCases:
    """Tests for _parse_product edge cases."""

    def test_handles_non_string_product_name(self) -> None:
        """Should handle non-string product_name."""
        client = OpenFoodFactsClient()
        product_data: dict[str, object] = {
            "product_name": 12345,  # Not a string
            "allergens_tags": [],
        }

        result = client._parse_product(product_data)

        assert result.product_name == ""

    def test_handles_non_list_allergens_tags(self) -> None:
        """Should handle non-list allergens_tags."""
        client = OpenFoodFactsClient()
        product_data: dict[str, object] = {
            "product_name": "Test",
            "allergens_tags": "not a list",
        }

        result = client._parse_product(product_data)

        assert result.allergens == ()

    def test_handles_non_string_tag_in_list(self) -> None:
        """Should skip non-string tags in allergens_tags."""
        client = OpenFoodFactsClient()
        product_data: dict[str, object] = {
            "product_name": "Test",
            "allergens_tags": [123, "en:gluten"],  # First is not a string
        }

        result = client._parse_product(product_data)

        assert len(result.allergens) == 1
        assert result.allergens[0].allergen == Allergen.GLUTEN


class TestCacheEdgeCases:
    """Tests for cache-related edge cases."""

    async def test_get_from_cache_returns_none_when_no_cache(self) -> None:
        """Should return None when cache client is None."""
        client = OpenFoodFactsClient(cache_client=None)

        result = await client._get_from_cache("test")

        assert result is None

    async def test_get_from_cache_handles_exception(
        self,
        mock_cache_client: MagicMock,
    ) -> None:
        """Should handle cache read exceptions gracefully."""
        mock_cache_client.get.side_effect = Exception("Redis error")
        client = OpenFoodFactsClient(cache_client=mock_cache_client)

        result = await client._get_from_cache("test")

        assert result is None

    async def test_save_to_cache_does_nothing_when_no_cache(self) -> None:
        """Should not error when cache client is None."""
        client = OpenFoodFactsClient(cache_client=None)
        product = OpenFoodFactsProduct(
            product_name="Test",
            allergens=(OpenFoodFactsAllergen(Allergen.GLUTEN, "CONTAINS"),),
        )

        # Should not raise
        await client._save_to_cache("test", product)

    async def test_save_to_cache_handles_exception(
        self,
        mock_cache_client: MagicMock,
    ) -> None:
        """Should handle cache write exceptions gracefully."""
        mock_cache_client.setex.side_effect = Exception("Redis error")
        client = OpenFoodFactsClient(cache_client=mock_cache_client)
        product = OpenFoodFactsProduct(
            product_name="Test",
            allergens=(OpenFoodFactsAllergen(Allergen.GLUTEN, "CONTAINS"),),
        )

        # Should not raise
        await client._save_to_cache("test", product)
