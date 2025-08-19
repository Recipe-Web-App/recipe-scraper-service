"""Unit tests for custom exception classes."""

import pytest

from app.enums.ingredient_unit_enum import IngredientUnitEnum
from app.exceptions.custom_exceptions import (
    DownstreamAuthenticationError,
    DownstreamDataNotFoundError,
    DownstreamServiceError,
    DownstreamServiceUnavailableError,
    IncompatibleUnitsError,
    RecipeScrapingError,
    SubstitutionNotFoundError,
)


class TestIncompatibleUnitsError:
    """Unit tests for the IncompatibleUnitsError exception."""

    @pytest.mark.unit
    def test_incompatible_units_error_initialization(self) -> None:
        """Test that IncompatibleUnitsError initializes correctly."""
        # Arrange
        from_unit = IngredientUnitEnum.G
        to_unit = IngredientUnitEnum.ML

        # Act
        error = IncompatibleUnitsError(from_unit, to_unit)

        # Assert
        assert error.from_unit == from_unit
        assert error.to_unit == to_unit
        expected_msg = (
            "Cannot convert between IngredientUnitEnum.G and IngredientUnitEnum.ML"
        )
        assert str(error) == expected_msg

    @pytest.mark.unit
    def test_incompatible_units_error_get_from_unit(self) -> None:
        """Test that get_from_unit returns the correct unit."""
        # Arrange
        from_unit = IngredientUnitEnum.CUP
        to_unit = IngredientUnitEnum.OZ
        error = IncompatibleUnitsError(from_unit, to_unit)

        # Act & Assert
        assert error.get_from_unit() == from_unit

    @pytest.mark.unit
    def test_incompatible_units_error_get_to_unit(self) -> None:
        """Test that get_to_unit returns the correct unit."""
        # Arrange
        from_unit = IngredientUnitEnum.TBSP
        to_unit = IngredientUnitEnum.KG
        error = IncompatibleUnitsError(from_unit, to_unit)

        # Act & Assert
        assert error.get_to_unit() == to_unit

    @pytest.mark.unit
    def test_incompatible_units_error_is_value_error(self) -> None:
        """Test that IncompatibleUnitsError is a ValueError."""
        # Arrange
        from_unit = IngredientUnitEnum.TSP
        to_unit = IngredientUnitEnum.LB
        error = IncompatibleUnitsError(from_unit, to_unit)

        # Act & Assert
        assert isinstance(error, ValueError)


class TestRecipeScrapingError:
    """Unit tests for the RecipeScrapingError exception."""

    @pytest.mark.unit
    def test_recipe_scraping_error_initialization_without_reason(self) -> None:
        """Test RecipeScrapingError initialization without reason."""
        # Arrange
        url = "https://example.com/recipe"

        # Act
        error = RecipeScrapingError(url)

        # Assert
        assert error.url == url
        assert error.reason is None
        assert str(error) == f"Failed to scrape recipe from {url}"

    @pytest.mark.unit
    def test_recipe_scraping_error_initialization_with_reason(self) -> None:
        """Test RecipeScrapingError initialization with reason."""
        # Arrange
        url = "https://example.com/recipe"
        reason = "Invalid URL format"

        # Act
        error = RecipeScrapingError(url, reason)

        # Assert
        assert error.url == url
        assert error.reason == reason
        assert str(error) == f"Failed to scrape recipe from {url}: {reason}"

    @pytest.mark.unit
    def test_recipe_scraping_error_get_url(self) -> None:
        """Test that get_url returns the correct URL."""
        # Arrange
        url = "https://example.com/recipe"
        error = RecipeScrapingError(url)

        # Act & Assert
        assert error.get_url() == url

    @pytest.mark.unit
    def test_recipe_scraping_error_get_reason(self) -> None:
        """Test that get_reason returns the correct reason."""
        # Arrange
        url = "https://example.com/recipe"
        reason = "Website not supported"
        error = RecipeScrapingError(url, reason)

        # Act & Assert
        assert error.get_reason() == reason

    @pytest.mark.unit
    def test_recipe_scraping_error_get_reason_none(self) -> None:
        """Test that get_reason returns None when no reason provided."""
        # Arrange
        url = "https://example.com/recipe"
        error = RecipeScrapingError(url)

        # Act & Assert
        assert error.get_reason() is None


class TestSubstitutionNotFoundError:
    """Unit tests for the SubstitutionNotFoundError exception."""

    @pytest.mark.unit
    def test_substitution_not_found_error_initialization_without_reason(self) -> None:
        """Test SubstitutionNotFoundError initialization without reason."""
        # Arrange
        ingredient_name = "saffron"

        # Act
        error = SubstitutionNotFoundError(ingredient_name)

        # Assert
        assert error.ingredient_name == ingredient_name
        assert error.reason is None
        assert str(error) == f"No substitutes found for '{ingredient_name}'"

    @pytest.mark.unit
    def test_substitution_not_found_error_initialization_with_reason(self) -> None:
        """Test SubstitutionNotFoundError initialization with reason."""
        # Arrange
        ingredient_name = "saffron"
        reason = "Too rare for common substitutes"

        # Act
        error = SubstitutionNotFoundError(ingredient_name, reason)

        # Assert
        assert error.ingredient_name == ingredient_name
        assert error.reason == reason
        expected_msg = f"No substitutes found for '{ingredient_name}': {reason}"
        assert str(error) == expected_msg

    @pytest.mark.unit
    def test_substitution_not_found_error_get_ingredient_name(self) -> None:
        """Test that get_ingredient_name returns the correct name."""
        # Arrange
        ingredient_name = "truffle oil"
        error = SubstitutionNotFoundError(ingredient_name)

        # Act & Assert
        assert error.get_ingredient_name() == ingredient_name

    @pytest.mark.unit
    def test_substitution_not_found_error_get_reason(self) -> None:
        """Test that get_reason returns the correct reason."""
        # Arrange
        ingredient_name = "cardamom"
        reason = "Service unavailable"
        error = SubstitutionNotFoundError(ingredient_name, reason)

        # Act & Assert
        assert error.get_reason() == reason

    @pytest.mark.unit
    def test_substitution_not_found_error_get_reason_none(self) -> None:
        """Test that get_reason returns None when no reason provided."""
        # Arrange
        ingredient_name = "vanilla extract"
        error = SubstitutionNotFoundError(ingredient_name)

        # Act & Assert
        assert error.get_reason() is None


class TestDownstreamServiceError:
    """Unit tests for the DownstreamServiceError exception."""

    @pytest.mark.unit
    def test_downstream_service_error_initialization(self) -> None:
        """Test DownstreamServiceError initialization."""
        # Arrange
        service_name = "ExternalAPI"
        message = "Connection timeout"

        # Act
        error = DownstreamServiceError(service_name, message)

        # Assert
        assert error.service_name == service_name
        assert str(error) == f"{service_name}: {message}"

    @pytest.mark.unit
    def test_downstream_service_error_is_exception(self) -> None:
        """Test that DownstreamServiceError is an Exception."""
        # Arrange
        service_name = "TestService"
        message = "Test error"
        error = DownstreamServiceError(service_name, message)

        # Act & Assert
        assert isinstance(error, Exception)


class TestDownstreamAuthenticationError:
    """Unit tests for the DownstreamAuthenticationError exception."""

    @pytest.mark.unit
    def test_downstream_authentication_error_without_status_code(self) -> None:
        """Test DownstreamAuthenticationError without status code."""
        # Arrange
        service_name = "AuthService"

        # Act
        error = DownstreamAuthenticationError(service_name)

        # Assert
        assert error.service_name == service_name
        assert error.status_code is None
        assert str(error) == f"{service_name}: Authentication failed"

    @pytest.mark.unit
    def test_downstream_authentication_error_with_status_code(self) -> None:
        """Test DownstreamAuthenticationError with status code."""
        # Arrange
        service_name = "AuthService"
        status_code = 401

        # Act
        error = DownstreamAuthenticationError(service_name, status_code)

        # Assert
        assert error.service_name == service_name
        assert error.status_code == status_code
        expected_msg = f"{service_name}: Authentication failed (HTTP {status_code})"
        assert str(error) == expected_msg

    @pytest.mark.unit
    def test_downstream_authentication_error_is_downstream_service_error(self) -> None:
        """Test that DownstreamAuthenticationError inherits correctly."""
        # Arrange
        service_name = "TestService"
        error = DownstreamAuthenticationError(service_name)

        # Act & Assert
        assert isinstance(error, DownstreamServiceError)


class TestDownstreamServiceUnavailableError:
    """Unit tests for the DownstreamServiceUnavailableError exception."""

    @pytest.mark.unit
    def test_downstream_service_unavailable_error_without_status_code(self) -> None:
        """Test DownstreamServiceUnavailableError without status code."""
        # Arrange
        service_name = "ExternalAPI"

        # Act
        error = DownstreamServiceUnavailableError(service_name)

        # Assert
        assert error.service_name == service_name
        assert error.status_code is None
        assert str(error) == f"{service_name}: Service temporarily unavailable"

    @pytest.mark.unit
    def test_downstream_service_unavailable_error_with_status_code(self) -> None:
        """Test DownstreamServiceUnavailableError with status code."""
        # Arrange
        service_name = "ExternalAPI"
        status_code = 503

        # Act
        error = DownstreamServiceUnavailableError(service_name, status_code)

        # Assert
        assert error.service_name == service_name
        assert error.status_code == status_code
        expected_msg = (
            f"{service_name}: Service temporarily unavailable (HTTP {status_code})"
        )
        assert str(error) == expected_msg

    @pytest.mark.unit
    def test_downstream_service_unavailable_error_is_downstream_service_error(
        self,
    ) -> None:
        """Test that DownstreamServiceUnavailableError inherits correctly."""
        # Arrange
        service_name = "TestService"
        error = DownstreamServiceUnavailableError(service_name)

        # Act & Assert
        assert isinstance(error, DownstreamServiceError)


class TestDownstreamDataNotFoundError:
    """Unit tests for the DownstreamDataNotFoundError exception."""

    @pytest.mark.unit
    def test_downstream_data_not_found_error_initialization(self) -> None:
        """Test DownstreamDataNotFoundError initialization."""
        # Arrange
        service_name = "DataService"
        resource = "recipe/123"

        # Act
        error = DownstreamDataNotFoundError(service_name, resource)

        # Assert
        assert error.service_name == service_name
        assert error.resource == resource
        expected_msg = f"{service_name}: Data not found for: {resource}"
        assert str(error) == expected_msg

    @pytest.mark.unit
    def test_downstream_data_not_found_error_is_downstream_service_error(self) -> None:
        """Test that DownstreamDataNotFoundError inherits correctly."""
        # Arrange
        service_name = "TestService"
        resource = "test/resource"
        error = DownstreamDataNotFoundError(service_name, resource)

        # Act & Assert
        assert isinstance(error, DownstreamServiceError)


class TestExceptionHierarchy:
    """Unit tests for exception inheritance hierarchy."""

    @pytest.mark.unit
    def test_downstream_service_error_hierarchy(self) -> None:
        """Test that all downstream service errors inherit correctly."""
        # Arrange & Act
        base_error = DownstreamServiceError("Service", "Error")
        auth_error = DownstreamAuthenticationError("Service")
        unavailable_error = DownstreamServiceUnavailableError("Service")
        not_found_error = DownstreamDataNotFoundError("Service", "resource")

        # Assert
        assert isinstance(auth_error, DownstreamServiceError)
        assert isinstance(unavailable_error, DownstreamServiceError)
        assert isinstance(not_found_error, DownstreamServiceError)

        # All should also be base Exception
        assert isinstance(base_error, Exception)
        assert isinstance(auth_error, Exception)
        assert isinstance(unavailable_error, Exception)
        assert isinstance(not_found_error, Exception)

    @pytest.mark.unit
    def test_application_specific_errors_are_exceptions(self) -> None:
        """Test that all application-specific errors are Exceptions."""
        # Arrange & Act
        units_error = IncompatibleUnitsError(
            IngredientUnitEnum.G, IngredientUnitEnum.ML
        )
        scraping_error = RecipeScrapingError("http://example.com")
        substitution_error = SubstitutionNotFoundError("ingredient")

        # Assert
        assert isinstance(units_error, Exception)
        assert isinstance(scraping_error, Exception)
        assert isinstance(substitution_error, Exception)
