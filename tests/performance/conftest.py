"""Performance test fixtures.

Provides fixtures for benchmarking with pytest-benchmark.
"""

from __future__ import annotations

import contextlib
import os
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from prometheus_client import REGISTRY
from starlette.testclient import TestClient
from testcontainers.redis import RedisContainer

import app.cache.redis as redis_module
from app.cache.redis import close_redis_pools, init_redis_pools
from app.core.config import Settings
from app.core.config.settings import (
    ApiSettings,
    AppSettings,
    AuthSettings,
    DownstreamServicesSettings,
    LLMCacheSettings,
    LLMFallbackSettings,
    LLMSettings,
    LoggingSettings,
    ObservabilitySettings,
    OllamaSettings,
    RateLimitingSettings,
    RecipeManagementServiceSettings,
    RedisSettings,
    ScrapingSettings,
    ServerSettings,
)
from app.factory import create_app


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from fastapi import FastAPI


pytestmark = pytest.mark.performance


@pytest.fixture(scope="session")
def redis_container() -> Generator[RedisContainer]:
    """Start a Redis container for performance tests."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


@pytest.fixture(scope="session")
def redis_url(redis_container: RedisContainer) -> str:
    """Get the Redis URL from the container."""
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    return f"redis://{host}:{port}"


@pytest.fixture
def test_settings(redis_url: str) -> Settings:
    """Create test settings for performance tests."""
    parts = redis_url.replace("redis://", "").split(":")
    redis_host = parts[0]
    redis_port = int(parts[1])

    return Settings(
        APP_ENV="test",
        JWT_SECRET_KEY="perf-test-jwt-secret-key",
        REDIS_PASSWORD="",
        app=AppSettings(
            name="perf-test-app",
            version="0.0.1-perf",
            debug=False,  # Disable debug for realistic benchmarks
        ),
        server=ServerSettings(
            host="0.0.0.0",
            port=8000,
        ),
        api=ApiSettings(
            cors_origins=["http://localhost:3000"],
        ),
        auth=AuthSettings(
            mode="disabled",
        ),
        redis=RedisSettings(
            host=redis_host,
            port=redis_port,
            cache_db=0,
            queue_db=1,
            rate_limit_db=2,
        ),
        rate_limiting=RateLimitingSettings(
            default="1000/minute",
            auth="100/minute",
        ),
        logging=LoggingSettings(
            level="WARNING",  # Reduce logging for benchmarks
            format="json",
        ),
        observability=ObservabilitySettings(),
        llm=LLMSettings(
            enabled=True,
            provider="ollama",
            ollama=OllamaSettings(
                url="http://localhost:11434",
                model="mistral:7b",
                timeout=60.0,
            ),
            fallback=LLMFallbackSettings(enabled=False),
            cache=LLMCacheSettings(enabled=False),
        ),
        scraping=ScrapingSettings(
            fetch_timeout=30.0,
            max_retries=2,
            cache_enabled=False,  # Disable cache for benchmarks
        ),
        downstream_services=DownstreamServicesSettings(
            recipe_management=RecipeManagementServiceSettings(
                url="http://localhost:8001",
                timeout=10.0,
            ),
        ),
    )


@pytest.fixture
async def initialized_redis(
    test_settings: Settings,
) -> AsyncGenerator[None]:
    """Initialize Redis pools for performance tests."""
    with patch("app.cache.redis.get_settings", return_value=test_settings):
        await init_redis_pools()

    yield

    await close_redis_pools()


@pytest.fixture(autouse=True)
async def reset_redis_state() -> AsyncGenerator[None]:
    """Reset Redis module state between tests."""
    redis_module._cache_pool = None
    redis_module._queue_pool = None
    redis_module._rate_limit_pool = None
    redis_module._cache_client = None
    redis_module._queue_client = None
    redis_module._rate_limit_client = None

    yield

    await close_redis_pools()


@pytest.fixture(autouse=True)
def reset_prometheus_registry() -> Generator[None]:
    """Reset Prometheus registry between tests.

    This prevents 'Duplicated timeseries' errors when creating
    multiple app instances in tests.
    """

    # Collect all collector names before test
    collectors_before = set(REGISTRY._names_to_collectors.keys())

    yield

    # Remove any collectors added during the test
    collectors_to_remove = []
    for name, collector in list(REGISTRY._names_to_collectors.items()):
        if name not in collectors_before:
            collectors_to_remove.append(collector)

    for collector in collectors_to_remove:
        with contextlib.suppress(Exception):
            REGISTRY.unregister(collector)


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    """Create FastAPI app with test settings for performance tests.

    Sets METRICS_ENABLED env var since prometheus-fastapi-instrumentator
    checks this when should_respect_env_var=True.
    """
    original_metrics_enabled = os.environ.get("METRICS_ENABLED")
    os.environ["METRICS_ENABLED"] = "true"

    try:
        with (
            patch("app.observability.metrics.get_settings", return_value=test_settings),
            patch("app.observability.tracing.get_settings", return_value=test_settings),
        ):
            return create_app(test_settings)
    finally:
        if original_metrics_enabled is None:
            os.environ.pop("METRICS_ENABLED", None)
        else:
            os.environ["METRICS_ENABLED"] = original_metrics_enabled


@pytest.fixture
def sync_client(app: FastAPI) -> Generator[TestClient]:
    """Create a sync HTTP client for performance benchmarks.

    Uses Starlette TestClient to avoid event loop conflicts with pytest-benchmark.
    """
    with TestClient(app) as client:
        yield client
