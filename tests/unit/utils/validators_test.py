"""Unit tests for the validators utility module."""

from http import HTTPStatus

import pytest
from fastapi import HTTPException

from app.api.v1.schemas.common.pagination_params import PaginationParams
from app.utils.validators import validate_pagination_params


class TestValidatePaginationParams:
    """Unit tests for the validate_pagination_params function."""

    @pytest.mark.unit
    def test_validate_pagination_params_valid_offset_less_than_limit(self) -> None:
        """Test validation passes when offset is less than limit."""
        # Arrange
        params = PaginationParams(offset=10, limit=20)

        # Act & Assert - should not raise any exception
        validate_pagination_params(params)

    @pytest.mark.unit
    def test_validate_pagination_params_valid_offset_equal_to_limit(self) -> None:
        """Test validation passes when offset equals limit."""
        # Arrange
        params = PaginationParams(offset=15, limit=15)

        # Act & Assert - should not raise any exception
        validate_pagination_params(params)

    @pytest.mark.unit
    def test_validate_pagination_params_valid_zero_offset(self) -> None:
        """Test validation passes when offset is zero."""
        # Arrange
        params = PaginationParams(offset=0, limit=10)

        # Act & Assert - should not raise any exception
        validate_pagination_params(params)

    @pytest.mark.unit
    def test_validate_pagination_params_valid_minimum_limit(self) -> None:
        """Test validation passes when limit is at minimum value."""
        # Arrange
        params = PaginationParams(offset=0, limit=1)

        # Act & Assert - should not raise any exception
        validate_pagination_params(params)

    @pytest.mark.unit
    def test_validate_pagination_params_invalid_offset_greater_than_limit(self) -> None:
        """Test validation fails when offset is greater than limit."""
        # Arrange
        params = PaginationParams(offset=25, limit=20)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validate_pagination_params(params)

        assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST
        assert exc_info.value.detail == "Offset cannot be greater than limit."

    @pytest.mark.unit
    def test_validate_pagination_params_invalid_large_difference(self) -> None:
        """Test validation fails when offset is much greater than limit."""
        # Arrange
        params = PaginationParams(offset=1000, limit=10)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validate_pagination_params(params)

        assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST
        assert exc_info.value.detail == "Offset cannot be greater than limit."

    @pytest.mark.unit
    def test_validate_pagination_params_invalid_offset_one_greater(self) -> None:
        """Test validation fails when offset is one greater than limit."""
        # Arrange
        params = PaginationParams(offset=11, limit=10)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validate_pagination_params(params)

        assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST
        assert exc_info.value.detail == "Offset cannot be greater than limit."

    @pytest.mark.unit
    def test_validate_pagination_params_valid_large_values(self) -> None:
        """Test validation passes with large valid values."""
        # Arrange
        params = PaginationParams(offset=9999, limit=10000)

        # Act & Assert - should not raise any exception
        validate_pagination_params(params)

    @pytest.mark.unit
    def test_validate_pagination_params_valid_same_large_values(self) -> None:
        """Test validation passes when offset and limit are the same large value."""
        # Arrange
        params = PaginationParams(offset=50000, limit=50000)

        # Act & Assert - should not raise any exception
        validate_pagination_params(params)

    @pytest.mark.unit
    def test_validate_pagination_params_http_exception_type(self) -> None:
        """Test that the correct HTTPException type is raised."""
        # Arrange
        params = PaginationParams(offset=15, limit=10)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validate_pagination_params(params)

        # Verify it's specifically an HTTPException
        assert isinstance(exc_info.value, HTTPException)
        assert hasattr(exc_info.value, 'status_code')
        assert hasattr(exc_info.value, 'detail')

    @pytest.mark.unit
    def test_validate_pagination_params_error_message_content(self) -> None:
        """Test that the error message is exactly as expected."""
        # Arrange
        params = PaginationParams(offset=100, limit=50)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validate_pagination_params(params)

        # Verify exact error message
        expected_message = "Offset cannot be greater than limit."
        assert exc_info.value.detail == expected_message

    @pytest.mark.unit
    def test_validate_pagination_params_error_status_code(self) -> None:
        """Test that the correct HTTP status code is used."""
        # Arrange
        params = PaginationParams(offset=30, limit=20)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validate_pagination_params(params)

        # Verify status code
        assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST
        assert exc_info.value.status_code == 400

    @pytest.mark.unit
    def test_validate_pagination_params_boundary_case_offset_at_minimum(
        self,
    ) -> None:
        """Test validation with offset at minimum value (0)."""
        # Arrange
        params = PaginationParams(offset=0, limit=10)

        # Act & Assert - should not raise any exception
        validate_pagination_params(params)

    @pytest.mark.unit
    def test_validate_pagination_params_boundary_case_limit_at_minimum(
        self,
    ) -> None:
        """Test validation with limit at minimum value (1)."""
        # Arrange
        params = PaginationParams(offset=0, limit=1)

        # Act & Assert - should not raise any exception
        validate_pagination_params(params)

    @pytest.mark.unit
    def test_validate_pagination_params_return_none_on_success(self) -> None:
        """Test that the function returns None on successful validation."""
        # Arrange
        params = PaginationParams(offset=5, limit=10)

        # Act - function should complete without raising an exception
        validate_pagination_params(params)

        # Assert - if we reach here, the function completed successfully

    @pytest.mark.unit
    def test_validate_pagination_params_with_default_values(self) -> None:
        """Test validation with PaginationParams default values if any."""
        # Arrange - create params with minimal required data
        params = PaginationParams(offset=1, limit=50)

        # Act & Assert - should not raise any exception
        validate_pagination_params(params)


class TestValidationEdgeCases:
    """Unit tests for edge cases and boundary conditions."""

    @pytest.mark.unit
    def test_validate_pagination_params_minimal_invalid_case(self) -> None:
        """Test the minimal case where validation should fail."""
        # Arrange
        params = PaginationParams(offset=2, limit=1)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validate_pagination_params(params)

        assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.unit
    def test_validate_pagination_params_exactly_at_boundary(self) -> None:
        """Test validation exactly at the boundary condition."""
        # Arrange - offset equals limit (boundary case)
        params = PaginationParams(offset=42, limit=42)

        # Act & Assert - should pass (offset == limit is allowed)
        validate_pagination_params(params)

    @pytest.mark.unit
    def test_validate_pagination_params_just_over_boundary(self) -> None:
        """Test validation just over the boundary condition."""
        # Arrange - offset is limit + 1 (just over boundary)
        params = PaginationParams(offset=43, limit=42)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validate_pagination_params(params)

        assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.unit
    def test_validate_pagination_params_multiple_calls_same_params(self) -> None:
        """Test that multiple calls with the same params work consistently."""
        # Arrange
        params = PaginationParams(offset=10, limit=20)

        # Act & Assert - multiple calls should all succeed
        validate_pagination_params(params)
        validate_pagination_params(params)
        validate_pagination_params(params)

    @pytest.mark.unit
    def test_validate_pagination_params_multiple_calls_invalid_params(self) -> None:
        """Test that multiple calls with invalid params consistently fail."""
        # Arrange
        params = PaginationParams(offset=30, limit=20)

        # Act & Assert - multiple calls should all fail with same error
        for _ in range(3):
            with pytest.raises(HTTPException) as exc_info:
                validate_pagination_params(params)
            assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST
            assert exc_info.value.detail == "Offset cannot be greater than limit."

    @pytest.mark.unit
    def test_validate_pagination_params_immutability(self) -> None:
        """Test that validation doesn't modify the input parameters."""
        # Arrange
        original_offset = 5
        original_limit = 10
        params = PaginationParams(offset=original_offset, limit=original_limit)

        # Act
        validate_pagination_params(params)

        # Assert - parameters should remain unchanged
        assert params.offset == original_offset
        assert params.limit == original_limit
