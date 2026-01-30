"""Open Food Facts API client for allergen data.

Provides Tier 2 allergen lookup from the Open Food Facts database.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import httpx
import orjson

from app.observability.logging import get_logger
from app.schemas.enums import Allergen


if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = get_logger(__name__)


# Open Food Facts tag to Allergen enum mapping
OFF_TAG_MAPPING: Final[dict[str, Allergen]] = {
    # Major allergens (FDA Big 9)
    "en:gluten": Allergen.GLUTEN,
    "en:milk": Allergen.MILK,
    "en:eggs": Allergen.EGGS,
    "en:nuts": Allergen.TREE_NUTS,
    "en:peanuts": Allergen.PEANUTS,
    "en:soybeans": Allergen.SOYBEANS,
    "en:fish": Allergen.FISH,
    "en:crustaceans": Allergen.SHELLFISH,
    "en:molluscs": Allergen.SHELLFISH,
    "en:sesame-seeds": Allergen.SESAME,
    # EU additional allergens
    "en:celery": Allergen.CELERY,
    "en:mustard": Allergen.MUSTARD,
    "en:lupin": Allergen.LUPIN,
    "en:sulphur-dioxide-and-sulphites": Allergen.SULPHITES,
    # Specific tree nuts
    "en:almonds": Allergen.ALMONDS,
    "en:cashews": Allergen.CASHEWS,
    "en:hazelnuts": Allergen.HAZELNUTS,
    "en:walnuts": Allergen.WALNUTS,
    # Other allergens
    "en:wheat": Allergen.WHEAT,
    "en:coconut": Allergen.COCONUT,
}


@dataclass(frozen=True, slots=True)
class OpenFoodFactsAllergen:
    """Allergen data from Open Food Facts."""

    allergen: Allergen
    presence_type: str  # "CONTAINS" or "MAY_CONTAIN"


@dataclass(frozen=True, slots=True)
class OpenFoodFactsProduct:
    """Product data from Open Food Facts."""

    product_name: str
    allergens: tuple[OpenFoodFactsAllergen, ...]


class OpenFoodFactsClient:
    """Client for Open Food Facts API.

    Searches for products by ingredient name and extracts allergen information.
    """

    BASE_URL: Final[str] = "https://world.openfoodfacts.org"
    SEARCH_ENDPOINT: Final[str] = "/cgi/search.pl"
    CACHE_PREFIX: Final[str] = "off"
    CACHE_TTL: Final[int] = 7 * 24 * 60 * 60  # 7 days

    def __init__(
        self,
        cache_client: Redis[bytes] | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the client.

        Args:
            cache_client: Redis client for caching responses.
            http_client: HTTP client for API requests.
        """
        self._cache = cache_client
        self._http = http_client
        self._owns_http_client = http_client is None

    async def initialize(self) -> None:
        """Initialize the HTTP client if not provided."""
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=10.0)
        logger.info("OpenFoodFactsClient initialized")

    async def shutdown(self) -> None:
        """Close the HTTP client if we own it."""
        if self._owns_http_client and self._http is not None:
            await self._http.aclose()
            self._http = None
        logger.info("OpenFoodFactsClient shutdown")

    async def search_by_name(
        self,
        name: str,
    ) -> OpenFoodFactsProduct | None:
        """Search for a product and extract allergen information.

        Args:
            name: Ingredient/product name to search.

        Returns:
            OpenFoodFactsProduct with allergen data, or None if not found.
        """
        if self._http is None:
            logger.warning("HTTP client not initialized")
            return None

        # Check cache first
        cached = await self._get_from_cache(name)
        if cached is not None:
            logger.debug("Cache hit for OFF product", ingredient=name)
            return cached

        # Make API request
        params = {
            "search_terms": name,
            "search_simple": "1",
            "action": "process",
            "json": "1",
            "page_size": "1",
        }

        try:
            response = await self._http.get(
                f"{self.BASE_URL}{self.SEARCH_ENDPOINT}",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as e:
            logger.warning(
                "Open Food Facts API request failed",
                ingredient=name,
                error=str(e),
            )
            return None

        products = data.get("products", [])
        if not products:
            logger.debug("No products found in OFF", ingredient=name)
            return None

        product = products[0]
        result = self._parse_product(product)

        # Cache result
        if result and result.allergens:
            await self._save_to_cache(name, result)

        return result

    def _parse_product(self, product: dict[str, object]) -> OpenFoodFactsProduct:
        """Parse Open Food Facts product response."""
        allergens: list[OpenFoodFactsAllergen] = []
        seen_allergens: set[Allergen] = set()

        # Parse allergens_tags (definitely contains)
        allergens_tags = product.get("allergens_tags", [])
        if isinstance(allergens_tags, list):
            for tag in allergens_tags:
                if isinstance(tag, str) and tag in OFF_TAG_MAPPING:
                    allergen = OFF_TAG_MAPPING[tag]
                    if allergen not in seen_allergens:
                        allergens.append(
                            OpenFoodFactsAllergen(
                                allergen=allergen,
                                presence_type="CONTAINS",
                            )
                        )
                        seen_allergens.add(allergen)

        # Parse traces_tags (may contain)
        traces_tags = product.get("traces_tags", [])
        if isinstance(traces_tags, list):
            for tag in traces_tags:
                if isinstance(tag, str) and tag in OFF_TAG_MAPPING:
                    allergen = OFF_TAG_MAPPING[tag]
                    if allergen not in seen_allergens:
                        allergens.append(
                            OpenFoodFactsAllergen(
                                allergen=allergen,
                                presence_type="MAY_CONTAIN",
                            )
                        )
                        seen_allergens.add(allergen)

        product_name = product.get("product_name", "")
        if not isinstance(product_name, str):
            product_name = ""

        return OpenFoodFactsProduct(
            product_name=product_name,
            allergens=tuple(allergens),
        )

    async def _get_from_cache(self, name: str) -> OpenFoodFactsProduct | None:
        """Get product from cache."""
        if self._cache is None:
            return None

        try:
            cache_key = f"{self.CACHE_PREFIX}:{name.lower()}"
            cached = await self._cache.get(cache_key)
            if cached:
                return self._deserialize(cached)
        except Exception:
            logger.exception("Cache read error for OFF")
        return None

    async def _save_to_cache(self, name: str, product: OpenFoodFactsProduct) -> None:
        """Save product to cache."""
        if self._cache is None:
            return

        try:
            cache_key = f"{self.CACHE_PREFIX}:{name.lower()}"
            await self._cache.setex(
                cache_key,
                self.CACHE_TTL,
                self._serialize(product),
            )
            logger.debug("Cached OFF product", key=cache_key)
        except Exception:
            logger.exception("Cache write error for OFF")

    def _serialize(self, product: OpenFoodFactsProduct) -> bytes:
        """Serialize product for caching."""
        return orjson.dumps(
            {
                "product_name": product.product_name,
                "allergens": [
                    {"allergen": a.allergen.value, "presence_type": a.presence_type}
                    for a in product.allergens
                ],
            }
        )

    def _deserialize(self, data: bytes) -> OpenFoodFactsProduct:
        """Deserialize product from cache."""
        obj = orjson.loads(data)
        return OpenFoodFactsProduct(
            product_name=obj["product_name"],
            allergens=tuple(
                OpenFoodFactsAllergen(
                    allergen=Allergen(a["allergen"]),
                    presence_type=a["presence_type"],
                )
                for a in obj["allergens"]
            ),
        )
