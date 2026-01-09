"""Performance benchmarks for JWT operations.

Benchmarks cover:
- Token creation speed
- Token decoding speed
- Token validation overhead
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import pytest

from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
)


if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture


pytestmark = pytest.mark.performance


class TestTokenCreationBenchmarks:
    """Benchmarks for token creation operations."""

    def test_create_access_token_benchmark(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark access token creation."""

        def create_token() -> str:
            return create_access_token(
                subject="user-123",
                roles=["user", "admin"],
                permissions=["read", "write", "delete"],
            )

        result = benchmark(create_token)

        # Verify result is valid
        assert result is not None
        assert len(result) > 0

    def test_create_refresh_token_benchmark(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark refresh token creation."""

        def create_token() -> str:
            return create_refresh_token(subject="user-123")

        result = benchmark(create_token)

        assert result is not None
        assert len(result) > 0

    def test_create_token_with_minimal_claims(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark token creation with minimal claims."""

        def create_token() -> str:
            return create_access_token(
                subject="user-123",
                roles=[],
                permissions=[],
            )

        result = benchmark(create_token)
        assert result is not None

    def test_create_token_with_many_claims(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark token creation with many claims."""
        many_roles = [f"role_{i}" for i in range(20)]
        many_permissions = [f"perm_{i}" for i in range(50)]

        def create_token() -> str:
            return create_access_token(
                subject="user-123",
                roles=many_roles,
                permissions=many_permissions,
            )

        result = benchmark(create_token)
        assert result is not None


class TestTokenDecodingBenchmarks:
    """Benchmarks for token decoding operations."""

    @pytest.fixture
    def access_token(self) -> str:
        """Create a valid access token for benchmarking."""
        return create_access_token(
            subject="user-123",
            roles=["user", "admin"],
            permissions=["read", "write"],
        )

    @pytest.fixture
    def refresh_token(self) -> str:
        """Create a valid refresh token for benchmarking."""
        return create_refresh_token(subject="user-123")

    def test_decode_access_token_benchmark(
        self,
        benchmark: BenchmarkFixture,
        access_token: str,
    ) -> None:
        """Benchmark access token decoding."""

        def decode() -> object:
            return decode_token(access_token)

        result = benchmark(decode)

        assert result is not None
        assert result.sub == "user-123"

    def test_decode_refresh_token_benchmark(
        self,
        benchmark: BenchmarkFixture,
        refresh_token: str,
    ) -> None:
        """Benchmark refresh token decoding."""

        def decode() -> object:
            return decode_token(refresh_token)

        result = benchmark(decode)

        assert result is not None
        assert result.sub == "user-123"


class TestTokenRoundtripBenchmarks:
    """Benchmarks for full token roundtrip operations."""

    def test_create_and_decode_roundtrip(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark full create-decode roundtrip."""

        def roundtrip() -> object:
            token = create_access_token(
                subject="user-123",
                roles=["user"],
                permissions=["read"],
            )
            return decode_token(token)

        result = benchmark(roundtrip)

        assert result is not None
        assert result.sub == "user-123"

    def test_create_decode_multiple_tokens(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark creating and decoding multiple tokens."""

        def process_batch() -> list:
            results = []
            for i in range(10):
                token = create_access_token(
                    subject=f"user-{i}",
                    roles=["user"],
                    permissions=[],
                )
                payload = decode_token(token)
                results.append(payload)
            return results

        result = benchmark(process_batch)

        assert len(result) == 10


class TestTokenValidationBenchmarks:
    """Benchmarks focused on token validation overhead."""

    @pytest.fixture
    def tokens_batch(self) -> list[str]:
        """Create batch of tokens for validation benchmarks."""
        return [
            create_access_token(
                subject=f"user-{i}",
                roles=["user"],
                permissions=["read"],
            )
            for i in range(100)
        ]

    def test_validate_many_tokens(
        self,
        benchmark: BenchmarkFixture,
        tokens_batch: list[str],
    ) -> None:
        """Benchmark validating many tokens."""

        def validate_all() -> int:
            valid_count = 0
            for token in tokens_batch:
                with contextlib.suppress(Exception):
                    decode_token(token)
                    valid_count += 1
            return valid_count

        result = benchmark(validate_all)

        assert result == 100

    def test_sequential_token_creation(
        self,
        benchmark: BenchmarkFixture,
    ) -> None:
        """Benchmark creating many tokens sequentially."""

        def create_many() -> list[str]:
            return [
                create_access_token(
                    subject=f"user-{i}",
                    roles=["user"],
                    permissions=[],
                )
                for i in range(100)
            ]

        result = benchmark(create_many)

        assert len(result) == 100
