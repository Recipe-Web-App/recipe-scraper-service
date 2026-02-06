"""Integration test fixtures for LLM client.

Uses testcontainers for real Redis, respx for mocked HTTP.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from redis.asyncio import Redis
from testcontainers.redis import RedisContainer

from app.llm.client.ollama import OllamaClient


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator


@pytest.fixture(scope="module")
def redis_container() -> Generator[RedisContainer]:
    """Start a Redis container for the test module."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


@pytest.fixture
async def redis_client(redis_container: RedisContainer) -> AsyncGenerator[Redis]:
    """Create async Redis client connected to container."""
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)

    client: Redis = Redis(host=host, port=int(port), decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
async def ollama_client(redis_client: Redis) -> AsyncGenerator[OllamaClient]:
    """Create OllamaClient with real Redis cache."""
    client = OllamaClient(
        base_url="http://localhost:11434",
        model="mistral:7b",
        cache_client=redis_client,
        cache_enabled=True,
        cache_ttl=60,
    )
    yield client
    await client.shutdown()
