"""Kroger API service for retrieving ingredient prices."""

from decimal import Decimal

import requests
from ingredient_parser import parse_ingredient

from app.api.v1.schemas.downstream.kroger.ingredient_price import KrogerIngredientPrice
from app.core.config.config import settings
from app.core.logging import get_logger
from app.exceptions.custom_exceptions import (
    DownstreamAuthenticationError,
    DownstreamDataNotFoundError,
    DownstreamServiceUnavailableError,
)

logger = get_logger(__name__)


class KrogerService:
    """Service for interacting with Kroger's API."""

    def __init__(self) -> None:
        """Initialize the Kroger service with configuration."""
        self.client_id = settings.kroger_api_client_id
        self.client_secret = settings.kroger_api_client_secret
        self.base_url = "https://api.kroger.com"
        self.access_token: str | None = None
        self.session = requests.Session()

    def _normalize_ingredient_name(self, ingredient_name: str) -> str:
        """Normalize ingredient name using PyIng to extract the core ingredient.

        Args:
            ingredient_name: Original ingredient name from recipe

        Returns:
            Normalized ingredient name suitable for grocery store search
        """
        try:
            # Use ingredient-parser-nlp to parse the ingredient
            parsed = parse_ingredient(ingredient_name)

            # Extract the core ingredient name from the parsed result
            if parsed.name and len(parsed.name) > 0:
                # Get the name with the highest confidence score
                best_name = max(parsed.name, key=lambda x: x.confidence)
                normalized_name = best_name.text
                confidence = best_name.confidence

                if len(parsed.name) > 1:
                    logger.debug(
                        f"ingredient-parser-nlp found {len(parsed.name)} names, "
                        f"selected highest confidence: '{normalized_name}' "
                        f"({confidence:.3f})"
                    )
                else:
                    logger.debug(
                        f"ingredient-parser-nlp normalized '{ingredient_name}' "
                        f"-> '{normalized_name}' (confidence: {confidence:.3f})"
                    )
                return str(normalized_name.strip())
            else:
                logger.debug(
                    f"No name extracted from '{ingredient_name}', using original"
                )
                return ingredient_name

        except Exception:
            logger.exception(f"Error normalizing ingredient '{ingredient_name}'")
            return ingredient_name

    def _get_token(self) -> str:
        """Get OAuth2 token using client credentials flow."""
        if self.access_token:
            return self.access_token

        try:
            logger.debug("Requesting Kroger API token with client credentials")

            # Prepare OAuth2 client credentials request
            token_url = f"{self.base_url}/v1/connect/oauth2/token"
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
            }
            data = {
                "grant_type": "client_credentials",
                "scope": "product.compact",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }

            response = self.session.post(token_url, headers=headers, data=data)
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data["access_token"]

            logger.debug("Successfully obtained Kroger API token")
            return self.access_token

        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 401:
                logger.error(f"Kroger authentication failed: {e}")
                raise DownstreamAuthenticationError("Kroger API", 401) from e
            elif e.response and e.response.status_code >= 500:
                logger.error(f"Kroger service unavailable: {e}")
                raise DownstreamServiceUnavailableError(
                    "Kroger API", e.response.status_code
                ) from e
            else:
                logger.error(f"Kroger HTTP error: {e}")
                raise DownstreamServiceUnavailableError("Kroger API") from e
        except KeyError as e:
            logger.error(f"Invalid token response format: missing {e}")
            raise DownstreamServiceUnavailableError("Kroger API") from e
        except Exception as e:
            logger.exception("Unexpected error getting Kroger token")
            raise DownstreamServiceUnavailableError("Kroger API") from e

    def get_ingredient_price(self, ingredient_name: str) -> KrogerIngredientPrice:
        """Get ingredient price from Kroger using hardcoded store location.

        Args:
            ingredient_name: Name of the ingredient to search for

        Returns:
            KrogerIngredientPrice object if found

        Raises:
            DownstreamAuthenticationError: If authentication with Kroger API fails
            DownstreamServiceUnavailableError: If Kroger API is unavailable
            DownstreamDataNotFoundError: If no pricing data is found for the ingredient
        """
        logger.debug(
            "Searching Kroger API for ingredient",
            extra={
                "service": "kroger_api",
                "operation": "get_ingredient_price",
                "ingredient_name": ingredient_name,
                "store_location": "02900510",
            },
        )

        try:
            # Normalize the ingredient name using PyIng
            normalized_name = self._normalize_ingredient_name(ingredient_name)

            # Get authentication token
            token = self._get_token()

            # Search for products using Kroger API with normalized name
            search_url = f"{self.base_url}/v1/products"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            params = {
                "filter.term": str(normalized_name),
                "filter.limit": "25",  # Get more results to find best match
                "filter.locationId": "02900510",  # Hardcoded store location for pricing
            }

            logger.debug(
                f"Searching Kroger API for '{normalized_name}' "
                f"(original: '{ingredient_name}')"
            )

            response: requests.Response = self.session.get(
                search_url, headers=headers, params=params
            )
            response.raise_for_status()

            products = response.json()
            logger.debug(f"Kroger API product response: {products}")

            if not products.get("data"):
                logger.debug("No products found for ingredient")
                raise DownstreamDataNotFoundError("Kroger API", ingredient_name)

            # Iterate through all products to find one with pricing
            for i, product in enumerate(products["data"]):
                logger.debug(
                    f"Checking product {i+1}: {product.get('description', 'Unknown')}"
                )

                if not product.get("items"):
                    logger.debug(f"Product {i+1} has no items, skipping")
                    continue

                item = product["items"][0]
                logger.debug(f"Product {i+1} item structure: {item}")

                # Extract pricing information
                price_info = item.get("price", {})
                regular_price = price_info.get("regular")

                if regular_price is not None:
                    logger.debug(f"Found pricing in product {i+1}: ${regular_price}")
                    break
                else:
                    logger.debug(f"Product {i+1} has no pricing information")

            # If we get here without finding pricing, log the issue
            if regular_price is None:
                logger.warning(
                    f"NO PRICING DATA found in any of {len(products['data'])} products "
                    f"for '{ingredient_name}'. Kroger API may not include pricing in "
                    "this endpoint or requires different parameters."
                )
                raise DownstreamDataNotFoundError("Kroger API", ingredient_name)

            price_result = KrogerIngredientPrice(
                ingredient_name=ingredient_name,
                price=Decimal(str(regular_price)),
                unit=item.get("size", "each"),
                location_id="02900510",
                product_id=product.get("productId"),
            )

            logger.debug(
                "Found Kroger price for ingredient",
                extra={
                    "service": "kroger_api",
                    "operation": "get_ingredient_price",
                    "ingredient_name": ingredient_name,
                    "price": str(regular_price),
                    "unit": item.get("size", "each"),
                    "product_id": product.get("productId"),
                    "result": "success",
                },
            )
            return price_result

        except (
            DownstreamAuthenticationError,
            DownstreamServiceUnavailableError,
            DownstreamDataNotFoundError,
        ):
            # Re-raise known downstream exceptions
            raise
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code >= 500:
                logger.error(
                    "Kroger service error",
                    extra={
                        "error_type": "service_error",
                        "service": "kroger_api",
                        "operation": "get_ingredient_price",
                        "ingredient_name": ingredient_name,
                        "status_code": e.response.status_code,
                        "error_detail": str(e),
                    },
                )
                raise DownstreamServiceUnavailableError(
                    "Kroger API", e.response.status_code
                ) from e
            else:
                logger.error(
                    "Kroger HTTP error",
                    extra={
                        "error_type": "http_error",
                        "service": "kroger_api",
                        "operation": "get_ingredient_price",
                        "ingredient_name": ingredient_name,
                        "status_code": e.response.status_code if e.response else None,
                        "error_detail": str(e),
                    },
                )
                raise DownstreamServiceUnavailableError("Kroger API") from e
        except Exception as e:
            logger.exception(
                f"Unexpected error getting Kroger price for {ingredient_name}"
            )
            raise DownstreamServiceUnavailableError("Kroger API") from e
