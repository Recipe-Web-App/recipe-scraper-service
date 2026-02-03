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
from app.database import close_database_pool, init_database_pool
from app.llm.client.fallback import FallbackLLMClient
from app.llm.client.groq import GroqClient
from app.llm.client.ollama import OllamaClient
from app.observability.logging import get_logger, setup_logging
from app.observability.tracing import shutdown_tracing
from app.services.allergen.service import AllergenService
from app.services.nutrition.service import NutritionService
from app.services.popular.service import PopularRecipesService
from app.services.recipe_management.client import RecipeManagementClient
from app.services.scraping.service import RecipeScraperService
from app.services.shopping.service import ShoppingService
from app.services.substitution.service import SubstitutionService
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

    # Initialize database connection pool (non-critical)
    await _init_database()

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

    # Initialize Nutrition Service (optional - non-critical)
    await _init_nutrition_service(app, cache_client)

    # Initialize Allergen Service (optional - non-critical)
    await _init_allergen_service(app, cache_client)

    # Initialize Shopping Service (optional - non-critical)
    await _init_shopping_service(app, cache_client)

    # Initialize Substitution Service (optional - non-critical, requires LLM)
    await _init_substitution_service(app, cache_client)

    # Initialize Recipe Scraper Service (optional - non-critical)
    await _init_scraper_service(app, cache_client)

    # Initialize Popular Recipes Service (optional - non-critical)
    await _init_popular_recipes_service(app, cache_client)

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


async def _init_database() -> None:
    """Initialize database connection pool (non-critical)."""
    try:
        await init_database_pool()
    except Exception:
        logger.exception(
            "Failed to initialize database - nutrition queries unavailable"
        )


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


async def _init_nutrition_service(
    app: FastAPI, cache_client: Redis[bytes] | None
) -> None:
    """Initialize nutrition service."""
    try:
        nutrition_service = NutritionService(cache_client=cache_client)
        await nutrition_service.initialize()
        app.state.nutrition_service = nutrition_service
        logger.info("NutritionService initialized")
    except Exception:
        logger.exception(
            "Failed to initialize NutritionService - nutrition queries unavailable"
        )
        app.state.nutrition_service = None


async def _init_allergen_service(
    app: FastAPI, cache_client: Redis[bytes] | None
) -> None:
    """Initialize allergen service."""
    try:
        allergen_service = AllergenService(cache_client=cache_client)
        await allergen_service.initialize()
        app.state.allergen_service = allergen_service
        logger.info("AllergenService initialized")
    except Exception:
        logger.exception(
            "Failed to initialize AllergenService - allergen queries unavailable"
        )
        app.state.allergen_service = None


async def _init_shopping_service(
    app: FastAPI, cache_client: Redis[bytes] | None
) -> None:
    """Initialize shopping service."""
    try:
        shopping_service = ShoppingService(cache_client=cache_client)
        await shopping_service.initialize()
        app.state.shopping_service = shopping_service
        logger.info("ShoppingService initialized")
    except Exception:
        logger.exception(
            "Failed to initialize ShoppingService - shopping queries unavailable"
        )
        app.state.shopping_service = None


async def _init_substitution_service(
    app: FastAPI, cache_client: Redis[bytes] | None
) -> None:
    """Initialize substitution service (requires LLM)."""
    # Get LLM client - required for substitution service
    llm_client: LLMClientProtocol | None = None
    try:
        llm_client = get_llm_client()
    except RuntimeError:
        logger.warning(
            "LLM client not available - substitution service will be unavailable"
        )
        app.state.substitution_service = None
        return

    try:
        substitution_service = SubstitutionService(
            cache_client=cache_client,
            llm_client=llm_client,
        )
        await substitution_service.initialize()
        app.state.substitution_service = substitution_service
        logger.info("SubstitutionService initialized")
    except Exception:
        logger.exception(
            "Failed to initialize SubstitutionService - substitutions unavailable"
        )
        app.state.substitution_service = None


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


async def _init_popular_recipes_service(
    app: FastAPI, cache_client: Redis[bytes] | None
) -> None:
    """Initialize popular recipes service."""
    settings = get_settings()
    if not settings.scraping.popular_recipes.enabled:
        logger.info("Popular recipes service disabled via configuration")
        app.state.popular_recipes_service = None
        return

    # Get LLM client if LLM extraction is enabled
    llm_client: LLMClientProtocol | None = None
    if settings.scraping.popular_recipes.use_llm_extraction:
        try:
            llm_client = get_llm_client()
        except RuntimeError:
            logger.warning(
                "LLM client not available - using regex extraction for popular recipes"
            )

    try:
        popular_service = PopularRecipesService(
            cache_client=cache_client,
            llm_client=llm_client,
        )
        await popular_service.initialize()
        app.state.popular_recipes_service = popular_service
        logger.info(
            "PopularRecipesService initialized",
            use_llm_extraction=settings.scraping.popular_recipes.use_llm_extraction,
            llm_available=llm_client is not None,
        )
    except Exception:
        logger.exception(
            "Failed to initialize PopularRecipesService - popular recipes unavailable"
        )
        app.state.popular_recipes_service = None


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

    # Shutdown Popular Recipes Service
    if (
        hasattr(app.state, "popular_recipes_service")
        and app.state.popular_recipes_service
    ):
        await app.state.popular_recipes_service.shutdown()
        logger.debug("PopularRecipesService shutdown")

    # Shutdown Nutrition Service
    if hasattr(app.state, "nutrition_service") and app.state.nutrition_service:
        await app.state.nutrition_service.shutdown()
        logger.debug("NutritionService shutdown")

    # Shutdown Allergen Service
    if hasattr(app.state, "allergen_service") and app.state.allergen_service:
        await app.state.allergen_service.shutdown()
        logger.debug("AllergenService shutdown")

    # Shutdown Shopping Service
    if hasattr(app.state, "shopping_service") and app.state.shopping_service:
        await app.state.shopping_service.shutdown()
        logger.debug("ShoppingService shutdown")

    # Shutdown Substitution Service
    if hasattr(app.state, "substitution_service") and app.state.substitution_service:
        await app.state.substitution_service.shutdown()
        logger.debug("SubstitutionService shutdown")

    # Shutdown LLM client
    await _shutdown_llm_client()

    # Shutdown auth provider (close HTTP connections, etc.)
    await shutdown_auth_provider()

    # Shutdown tracing (flush pending spans)
    shutdown_tracing()

    # Close ARQ connection pool
    await close_arq_pool()

    # Close database connection pool
    await close_database_pool()

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

    Creates primary client based on settings.llm.provider (Groq or Ollama),
    wrapped in FallbackLLMClient for automatic failover on connection errors.

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

    # Create primary client based on provider setting
    primary: LLMClientProtocol
    if settings.llm.provider == "groq":
        if not settings.GROQ_API_KEY:
            logger.warning("Groq selected as primary but GROQ_API_KEY not set")
            return
        primary = GroqClient(
            api_key=settings.GROQ_API_KEY,
            model=settings.llm.groq.model,
            base_url=settings.llm.groq.url,
            timeout=settings.llm.groq.timeout,
            max_retries=settings.llm.groq.max_retries,
            cache_client=cache_client,
            cache_ttl=settings.llm.cache.ttl,
            cache_enabled=settings.llm.cache.enabled,
            requests_per_minute=settings.llm.groq.requests_per_minute,
        )
    else:
        # Default to Ollama
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
            requests_per_minute=settings.llm.groq.requests_per_minute,
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

    primary_model = (
        settings.llm.groq.model
        if settings.llm.provider == "groq"
        else settings.llm.ollama.model
    )
    logger.info(
        "LLM client initialized",
        primary_provider=settings.llm.provider,
        primary_model=primary_model,
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
