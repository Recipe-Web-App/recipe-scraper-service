"""Application lifespan event handlers.

This module defines the lifespan context manager that handles:
- Application startup: Initialize connections, warm caches, etc.
- Application shutdown: Close connections, flush buffers, etc.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from app.auth.providers import initialize_auth_provider, shutdown_auth_provider
from app.cache.redis import close_redis_pools, get_cache_client, init_redis_pools
from app.core.config import AuthMode, Settings, get_settings
from app.llm.client.fallback import FallbackLLMClient
from app.llm.client.groq import GroqClient
from app.llm.client.ollama import OllamaClient
from app.observability.logging import get_logger, setup_logging
from app.observability.tracing import shutdown_tracing
from app.services.recipe_management.client import RecipeManagementClient
from app.services.scraping.service import RecipeScraperService
from app.workers.jobs import close_arq_pool, get_arq_pool


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import FastAPI
    from redis.asyncio import Redis

    from app.llm.client.protocol import LLMClientProtocol

logger = get_logger(__name__)


# Container for global LLM client (avoids global statement)
class _LLMClientHolder:
    client: LLMClientProtocol | None = None


async def _startup(app: FastAPI, settings: Settings) -> None:
    """Initialize all application services during startup.

    Args:
        app: The FastAPI application instance.
        settings: Application settings.
    """
    logger.info(
        "Starting application",
        app_name=settings.app.name,
        environment=settings.APP_ENV,
        debug=settings.app.debug,
    )

    # Initialize logging
    setup_logging(
        log_level=settings.logging.level,
        log_format=settings.logging.format,
        is_development=settings.is_development,
    )

    # Initialize Redis connection pools
    cache_client = await _init_cache()

    # Initialize ARQ connection pool for job enqueuing
    await _init_arq()

    # Initialize auth provider (critical - will raise on failure)
    await _init_auth(settings, cache_client)

    # Initialize LLM client (optional - non-critical)
    if settings.llm.enabled:
        try:
            await _init_llm_client(settings)
        except Exception:
            logger.exception(
                "Failed to initialize LLM client - LLM features unavailable"
            )

    # Initialize Recipe Scraper Service (optional - non-critical)
    await _init_scraper_service(app, cache_client)

    # Initialize Recipe Management Client (optional - non-critical)
    await _init_recipe_management_client(app)

    logger.info("Application startup complete")


async def _init_cache() -> Redis[bytes] | None:
    """Initialize Redis cache and return client."""
    try:
        await init_redis_pools()
        return await get_cache_client()
    except Exception:
        logger.exception("Failed to initialize Redis - continuing without cache")
        return None


async def _init_arq() -> None:
    """Initialize ARQ connection pool."""
    try:
        await get_arq_pool()
    except Exception:
        logger.exception("Failed to initialize ARQ pool - background jobs unavailable")


async def _init_auth(settings: Settings, cache_client: Redis[bytes] | None) -> None:
    """Initialize auth provider (critical service)."""
    try:
        auth_cache_client = None
        if settings.auth_mode_enum == AuthMode.INTROSPECTION and cache_client:
            auth_cache_client = cache_client

        await initialize_auth_provider(cache_client=auth_cache_client)
        logger.info("Auth provider initialized", mode=settings.auth.mode)
    except Exception:
        logger.exception("Failed to initialize auth provider")
        raise  # Auth is critical - don't continue without it


async def _init_scraper_service(
    app: FastAPI, cache_client: Redis[bytes] | None
) -> None:
    """Initialize recipe scraper service."""
    try:
        scraper_service = RecipeScraperService(cache_client=cache_client)
        await scraper_service.initialize()
        app.state.scraper_service = scraper_service
        logger.info("RecipeScraperService initialized")
    except Exception:
        logger.exception(
            "Failed to initialize RecipeScraperService - recipe scraping unavailable"
        )
        app.state.scraper_service = None


async def _init_recipe_management_client(app: FastAPI) -> None:
    """Initialize recipe management client."""
    try:
        recipe_management_client = RecipeManagementClient()
        await recipe_management_client.initialize()
        app.state.recipe_management_client = recipe_management_client
        logger.info(
            "RecipeManagementClient initialized",
            base_url=recipe_management_client.base_url,
        )
    except Exception:
        logger.exception(
            "Failed to initialize RecipeManagementClient - recipe creation unavailable"
        )
        app.state.recipe_management_client = None


async def _shutdown(app: FastAPI) -> None:
    """Shutdown all application services.

    Args:
        app: The FastAPI application instance.
    """
    logger.info("Shutting down application")

    # Shutdown Recipe Management Client
    if (
        hasattr(app.state, "recipe_management_client")
        and app.state.recipe_management_client
    ):
        await app.state.recipe_management_client.shutdown()
        logger.debug("RecipeManagementClient shutdown")

    # Shutdown Recipe Scraper Service
    if hasattr(app.state, "scraper_service") and app.state.scraper_service:
        await app.state.scraper_service.shutdown()
        logger.debug("RecipeScraperService shutdown")

    # Shutdown LLM client
    await _shutdown_llm_client()

    # Shutdown auth provider (close HTTP connections, etc.)
    await shutdown_auth_provider()

    # Shutdown tracing (flush pending spans)
    shutdown_tracing()

    # Close ARQ connection pool
    await close_arq_pool()

    # Close Redis connection pools
    await close_redis_pools()

    logger.info("Application shutdown complete")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Manage application lifespan events.

    This context manager handles startup and shutdown events for the application.
    Resources initialized here are available throughout the application's lifetime.

    Args:
        app: The FastAPI application instance.

    Yields:
        None - control returns to the application to handle requests.
    """
    settings = get_settings()
    await _startup(app, settings)
    yield
    await _shutdown(app)


async def _init_llm_client(settings: Settings) -> None:
    """Initialize the LLM client with optional fallback.

    Creates primary (Ollama) and secondary (Groq) clients, wrapped in
    FallbackLLMClient for automatic failover on connection errors.

    Args:
        settings: Application settings.
    """
    cache_client = None
    if settings.llm.cache.enabled:
        try:
            cache_client = await get_cache_client()
        except Exception:
            logger.warning(
                "Redis not available for LLM caching - continuing without cache"
            )

    # Create primary client (Ollama)
    primary = OllamaClient(
        base_url=settings.llm.ollama.url,
        model=settings.llm.ollama.model,
        timeout=settings.llm.ollama.timeout,
        max_retries=settings.llm.ollama.max_retries,
        cache_client=cache_client,
        cache_ttl=settings.llm.cache.ttl,
        cache_enabled=settings.llm.cache.enabled,
    )

    # Create secondary client (Groq) if fallback enabled and API key present
    secondary: LLMClientProtocol | None = None
    if (
        settings.llm.fallback.enabled
        and settings.llm.fallback.secondary_provider == "groq"
        and settings.GROQ_API_KEY
    ):
        secondary = GroqClient(
            api_key=settings.GROQ_API_KEY,
            model=settings.llm.groq.model,
            base_url=settings.llm.groq.url,
            timeout=settings.llm.groq.timeout,
            max_retries=settings.llm.groq.max_retries,
            cache_client=cache_client,
            cache_ttl=settings.llm.cache.ttl,
            cache_enabled=settings.llm.cache.enabled,
        )
        logger.info(
            "Groq fallback client configured",
            model=settings.llm.groq.model,
        )
    elif settings.llm.fallback.enabled and not settings.GROQ_API_KEY:
        logger.warning(
            "LLM fallback enabled but GROQ_API_KEY not set - "
            "fallback will not be available"
        )

    # Wrap in fallback client
    _LLMClientHolder.client = FallbackLLMClient(
        primary=primary,
        secondary=secondary,
        fallback_enabled=settings.llm.fallback.enabled,
    )
    await _LLMClientHolder.client.initialize()

    logger.info(
        "LLM client initialized",
        primary_provider=settings.llm.provider,
        primary_model=settings.llm.ollama.model,
        fallback_enabled=settings.llm.fallback.enabled,
        has_fallback=secondary is not None,
    )


async def _shutdown_llm_client() -> None:
    """Shutdown the LLM client."""
    if _LLMClientHolder.client is not None:
        await _LLMClientHolder.client.shutdown()
        _LLMClientHolder.client = None
        logger.debug("LLM client shutdown")


def get_llm_client() -> LLMClientProtocol:
    """Get the initialized LLM client.

    Returns:
        The global LLM client instance (FallbackLLMClient wrapping
        primary and optional secondary providers).

    Raises:
        RuntimeError: If LLM client is not initialized.
    """
    if _LLMClientHolder.client is None:
        msg = "LLM client not initialized. Ensure LLM is enabled in settings."
        raise RuntimeError(msg)
    return _LLMClientHolder.client
