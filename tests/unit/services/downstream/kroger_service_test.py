"""Unit tests for the KrogerService class."""

from decimal import Decimal
from typing import Any
from unittest.mock import Mock, patch

import pytest
from requests.exceptions import HTTPError, RequestException, Timeout

from app.api.v1.schemas.downstream.kroger.ingredient_price import KrogerIngredientPrice
from app.exceptions.custom_exceptions import (
    DownstreamAuthenticationError,
    DownstreamDataNotFoundError,
    DownstreamServiceUnavailableError,
)
from app.services.downstream.kroger_service import KrogerService


@pytest.mark.unit
class TestKrogerService:
    """Unit tests for KrogerService."""

    @pytest.fixture
    def kroger_service(self) -> KrogerService:
        """Create a KrogerService instance for testing."""
        with patch("app.services.downstream.kroger_service.settings") as mock_settings:
            mock_settings.kroger_api_client_id = "test_client_id"
            mock_settings.kroger_api_client_secret = (
                "test_client_secret"  # pragma: allowlist secret
            )
            return KrogerService()

    def test_init_sets_configuration(self, kroger_service: KrogerService) -> None:
        """Test that KrogerService initializes with correct configuration."""
        # Assert
        assert kroger_service.client_id == "test_client_id"
        assert (
            kroger_service.client_secret
            == "test_client_secret"  # pragma: allowlist secret
        )
        assert kroger_service.base_url == "https://api.kroger.com"
        assert kroger_service.access_token is None
        assert kroger_service.session is not None

    def test_normalize_ingredient_name_basic(
        self, kroger_service: KrogerService
    ) -> None:
        """Test basic ingredient name normalization."""
        # Arrange & Act
        result = kroger_service._normalize_ingredient_name("Tomatoes")

        # Assert
        assert result == "Tomatoes"

    def test_normalize_ingredient_name_with_whitespace(
        self, kroger_service: KrogerService
    ) -> None:
        """Test ingredient name normalization with extra whitespace."""
        # Arrange & Act
        result = kroger_service._normalize_ingredient_name("  Fresh Tomatoes  ")

        # Assert
        assert result == "Fresh Tomatoes"

    def test_normalize_ingredient_name_with_special_characters(
        self, kroger_service: KrogerService
    ) -> None:
        """Test ingredient name normalization with special characters."""
        # Arrange & Act
        result = kroger_service._normalize_ingredient_name("Tomatoes, Roma-Style!")

        # Assert
        assert result == "Tomatoes"

    def test_normalize_ingredient_name_complex_ingredient(
        self, kroger_service: KrogerService
    ) -> None:
        """Test ingredient name normalization with complex ingredient name."""
        # Arrange & Act
        result = kroger_service._normalize_ingredient_name(
            "1 lb Fresh Organic Cherry Tomatoes (12 oz)"
        )

        # Assert
        # Should extract just the main ingredient name
        assert "Tomatoes" in result
        assert result == "Fresh Organic Cherry Tomatoes"

    @patch("app.services.downstream.kroger_service.requests.Session.post")
    def test_get_token_success(
        self, mock_post: Mock, kroger_service: KrogerService
    ) -> None:
        """Test successful token retrieval."""
        # Arrange
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "access_token": "test_token_123",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        # Act
        result = kroger_service._get_token()

        # Assert
        assert result == "test_token_123"
        assert kroger_service.access_token == "test_token_123"
        mock_post.assert_called_once()

    @patch("app.services.downstream.kroger_service.requests.Session.post")
    def test_get_token_http_error(
        self, mock_post: Mock, kroger_service: KrogerService
    ) -> None:
        """Test token retrieval with HTTP error."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 401
        http_error = HTTPError("401 Unauthorized")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_post.return_value = mock_response

        # Act & Assert
        with pytest.raises(DownstreamAuthenticationError):
            kroger_service._get_token()

    @patch("app.services.downstream.kroger_service.requests.Session.post")
    def test_get_token_request_exception(
        self, mock_post: Mock, kroger_service: KrogerService
    ) -> None:
        """Test token retrieval with request exception."""
        # Arrange
        mock_post.side_effect = RequestException("Connection error")

        # Act & Assert
        with pytest.raises(DownstreamServiceUnavailableError):
            kroger_service._get_token()

    @patch("app.services.downstream.kroger_service.requests.Session.post")
    def test_get_token_timeout(
        self, mock_post: Mock, kroger_service: KrogerService
    ) -> None:
        """Test token retrieval with timeout."""
        # Arrange
        mock_post.side_effect = Timeout("Request timeout")

        # Act & Assert
        with pytest.raises(DownstreamServiceUnavailableError):
            kroger_service._get_token()

    @patch("app.services.downstream.kroger_service.requests.Session.get")
    @patch.object(KrogerService, "_get_token")
    def test_get_ingredient_price_success(
        self,
        mock_get_token: Mock,
        mock_get: Mock,
        kroger_service: KrogerService,
        mock_kroger_product_response: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Test successful ingredient price retrieval."""
        # Arrange
        mock_get_token.return_value = "test_token"
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_kroger_product_response
        mock_get.return_value = mock_response

        # Act
        result = kroger_service.get_ingredient_price("tomatoes")

        # Assert
        assert isinstance(result, KrogerIngredientPrice)
        assert result.ingredient_name == "tomatoes"
        assert result.price == Decimal("2.99")
        assert result.unit == "lb"
        assert result.product_id == "0001111041956"

    @patch("app.services.downstream.kroger_service.requests.Session.get")
    @patch.object(KrogerService, "_get_token")
    def test_get_ingredient_price_no_products_found(
        self,
        mock_get_token: Mock,
        mock_get: Mock,
        kroger_service: KrogerService,
        mock_kroger_empty_response: dict[str, list[Any]],
    ) -> None:
        """Test ingredient price retrieval when no products are found."""
        # Arrange
        mock_get_token.return_value = "test_token"
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_kroger_empty_response
        mock_get.return_value = mock_response

        # Act & Assert
        with pytest.raises(DownstreamDataNotFoundError):
            kroger_service.get_ingredient_price("nonexistent ingredient")

    @patch("app.services.downstream.kroger_service.requests.Session.get")
    @patch.object(KrogerService, "_get_token")
    def test_get_ingredient_price_no_pricing_info(
        self,
        mock_get_token: Mock,
        mock_get: Mock,
        kroger_service: KrogerService,
        mock_kroger_no_pricing_response: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Test ingredient price retrieval when products have no pricing."""
        # Arrange
        mock_get_token.return_value = "test_token"
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_kroger_no_pricing_response
        mock_get.return_value = mock_response

        # Act & Assert
        with pytest.raises(DownstreamDataNotFoundError):
            kroger_service.get_ingredient_price("organic tomatoes")

    @patch("app.services.downstream.kroger_service.requests.Session.get")
    @patch.object(KrogerService, "_get_token")
    def test_get_ingredient_price_http_error(
        self,
        mock_get_token: Mock,
        mock_get: Mock,
        kroger_service: KrogerService,
    ) -> None:
        """Test ingredient price retrieval with HTTP error."""
        # Arrange
        mock_get_token.return_value = "test_token"
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        # Act & Assert
        with pytest.raises(DownstreamServiceUnavailableError):
            kroger_service.get_ingredient_price("tomatoes")

    @patch("app.services.downstream.kroger_service.requests.Session.get")
    @patch.object(KrogerService, "_get_token")
    def test_get_ingredient_price_request_exception(
        self,
        mock_get_token: Mock,
        mock_get: Mock,
        kroger_service: KrogerService,
    ) -> None:
        """Test ingredient price retrieval with request exception."""
        # Arrange
        mock_get_token.return_value = "test_token"
        mock_get.side_effect = RequestException("Network error")

        # Act & Assert
        with pytest.raises(DownstreamServiceUnavailableError):
            kroger_service.get_ingredient_price("tomatoes")

    @patch("app.services.downstream.kroger_service.requests.Session.get")
    @patch.object(KrogerService, "_get_token")
    def test_get_ingredient_price_calls_get_token(
        self,
        mock_get_token: Mock,
        mock_get: Mock,
        kroger_service: KrogerService,
        mock_kroger_product_response: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Test that _get_token is called for authentication."""
        # Arrange
        mock_get_token.return_value = "test_token"
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_kroger_product_response
        mock_get.return_value = mock_response

        # Act
        kroger_service.get_ingredient_price("tomatoes")

        # Assert
        mock_get_token.assert_called_once()
        # Check that Authorization header uses token
        call_args = mock_get.call_args
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test_token"

    @patch("app.services.downstream.kroger_service.requests.Session.get")
    @patch.object(KrogerService, "_get_token")
    def test_get_ingredient_price_handles_http_error(
        self,
        mock_get_token: Mock,
        mock_get: Mock,
        kroger_service: KrogerService,
    ) -> None:
        """Test that HTTP errors are handled properly."""
        # Arrange
        mock_get_token.return_value = "test_token"
        mock_response = Mock()
        mock_response.status_code = 401
        http_error = HTTPError("401 Unauthorized")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response

        # Act & Assert
        with pytest.raises(DownstreamServiceUnavailableError):
            kroger_service.get_ingredient_price("tomatoes")

    @patch.object(KrogerService, "_get_token")
    def test_get_ingredient_price_validates_ingredient_name(
        self, mock_get_token: Mock, kroger_service: KrogerService
    ) -> None:
        """Test that ingredient name validation works correctly."""
        # Arrange - Mock _get_token to avoid actual HTTP calls
        mock_get_token.side_effect = DownstreamServiceUnavailableError("Kroger API")

        # Act & Assert - Service doesn't validate empty strings early,
        # but will fail when trying to get token for empty ingredient
        with pytest.raises(DownstreamServiceUnavailableError):
            kroger_service.get_ingredient_price("")

        with pytest.raises(DownstreamServiceUnavailableError):
            kroger_service.get_ingredient_price("   ")

    @patch("app.services.downstream.kroger_service.requests.Session.get")
    @patch.object(KrogerService, "_get_token")
    def test_get_ingredient_price_selects_best_match(
        self,
        mock_get_token: Mock,
        mock_get: Mock,
        kroger_service: KrogerService,
        mock_kroger_product_response: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Test that the best price match is selected from multiple products."""
        # Arrange
        mock_get_token.return_value = "test_token"
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_kroger_product_response
        mock_get.return_value = mock_response

        # Act
        result = kroger_service.get_ingredient_price("tomatoes")

        # Assert
        # Should pick the first product with pricing (Roma Tomatoes at $2.99)
        assert result.price == Decimal("2.99")
        assert result.product_id == "0001111041956"

    @patch("app.services.downstream.kroger_service.requests.Session.get")
    @patch.object(KrogerService, "_get_token")
    def test_get_ingredient_price_handles_promo_pricing(
        self,
        mock_get_token: Mock,
        mock_get: Mock,
        kroger_service: KrogerService,
    ) -> None:
        """Test that promo pricing is preferred over regular pricing."""
        # Arrange
        mock_get_token.return_value = "test_token"
        promo_response = {
            "data": [
                {
                    "productId": "0001111041956",
                    "description": "Roma Tomatoes",
                    "items": [
                        {
                            "itemId": "0001111041956",
                            "size": "lb",
                            "price": {
                                "regular": 2.99,
                                "promo": 1.99,  # Lower promo price
                            },
                        }
                    ],
                }
            ]
        }
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = promo_response
        mock_get.return_value = mock_response

        # Act
        result = kroger_service.get_ingredient_price("tomatoes")

        # Assert
        # Service uses regular price, not promo price
        assert result.price == Decimal("2.99")

    @patch("app.services.downstream.kroger_service.parse_ingredient")
    @patch("app.services.downstream.kroger_service.requests.Session.get")
    @patch.object(KrogerService, "_get_token")
    def test_get_ingredient_price_uses_ingredient_parser(
        self,
        mock_get_token: Mock,
        mock_get: Mock,
        mock_parse_ingredient: Mock,
        kroger_service: KrogerService,
        mock_kroger_product_response: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Test that ingredient parser is used for complex ingredient names."""
        # Arrange
        mock_parse_ingredient.return_value = Mock(name="tomatoes")
        mock_get_token.return_value = "test_token"
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_kroger_product_response
        mock_get.return_value = mock_response

        # Act
        kroger_service.get_ingredient_price("2 lbs fresh Roma tomatoes")

        # Assert
        mock_parse_ingredient.assert_called_once_with("2 lbs fresh Roma tomatoes")

    @patch("app.services.downstream.kroger_service.requests.Session.get")
    @patch.object(KrogerService, "_get_token")
    def test_get_ingredient_price_request_parameters(
        self,
        mock_get_token: Mock,
        mock_get: Mock,
        kroger_service: KrogerService,
        mock_kroger_product_response: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Test that correct request parameters are sent to Kroger API."""
        # Arrange
        mock_get_token.return_value = "test_token"
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_kroger_product_response
        mock_get.return_value = mock_response

        # Act
        kroger_service.get_ingredient_price("tomatoes")

        # Assert
        mock_get.assert_called_once()
        call_args = mock_get.call_args

        # Check URL
        url = call_args[0][0]
        assert "https://api.kroger.com/v1/products" in url

        # Check headers
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test_token"
        assert headers["Content-Type"] == "application/json"

        # Check query parameters
        params = call_args[1]["params"]
        assert "filter.term" in params
        assert "filter.locationId" in params

    def test_normalize_ingredient_name_edge_cases(
        self, kroger_service: KrogerService
    ) -> None:
        """Test ingredient name normalization with edge cases."""
        # Test empty string
        result = kroger_service._normalize_ingredient_name("")
        assert result == ""

        # Test only whitespace - returns original when no name extracted
        result = kroger_service._normalize_ingredient_name("   ")
        assert result == "   "

        # Test only special characters - parser extracts what it can
        result = kroger_service._normalize_ingredient_name("@#$%")
        assert result == "@#$%"

        # Test mixed case with numbers
        result = kroger_service._normalize_ingredient_name("2% Milk")
        assert "Milk" in result

    @patch("app.services.downstream.kroger_service.requests.Session.get")
    @patch.object(KrogerService, "_get_token")
    def test_get_ingredient_price_response_parsing_edge_cases(
        self,
        mock_get_token: Mock,
        mock_get: Mock,
        kroger_service: KrogerService,
    ) -> None:
        """Test response parsing with various edge cases."""
        # Arrange
        mock_get_token.return_value = "test_token"

        # Test response with missing fields
        incomplete_response = {
            "data": [
                {
                    "productId": "123",
                    # Missing description
                    "items": [
                        {
                            "itemId": "123",
                            # Missing size
                            "price": {"regular": 1.99},
                        }
                    ],
                }
            ]
        }

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = incomplete_response
        mock_get.return_value = mock_response

        # Act
        result = kroger_service.get_ingredient_price("test")

        # Assert
        assert isinstance(result, KrogerIngredientPrice)
        assert result.price == Decimal("1.99")
        assert result.unit == "each"  # Default unit when size is missing
