"""End-to-end tests for the POST /recipes endpoint.

These tests verify the full recipe creation flow:
1. Scrape recipe from URL (mocked external website)
2. Parse ingredients via LLM (mocked LLM response)
3. Create recipe in Recipe Management Service (mocked)
4. Return response to client

Tests use testcontainers for Redis and respx for HTTP mocking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient

from app.auth.providers import set_auth_provider, shutdown_auth_provider
from app.auth.providers.header import HeaderAuthProvider
from app.core.config import Settings
from app.core.config.settings import (
    ApiSettings,
    AppSettings,
    AuthSettings,
    DownstreamServicesSettings,
    LLMSettings,
    LoggingSettings,
    ObservabilitySettings,
    RateLimitingSettings,
    RecipeManagementServiceSettings,
    RedisSettings,
    ScrapingSettings,
    ServerSettings,
)
from app.core.config.settings import (
    get_settings as _get_settings,
)
from app.factory import create_app
from app.llm.client.ollama import OllamaClient
from app.services.recipe_management.client import RecipeManagementClient
from app.services.scraping.service import RecipeScraperService
from tests.fixtures.llm_responses import get_recorded_response


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import FastAPI


pytestmark = pytest.mark.e2e


# Sample HTML with JSON-LD recipe data for testing
SAMPLE_RECIPE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Classic Chocolate Chip Cookies</title>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org/",
        "@type": "Recipe",
        "name": "Classic Chocolate Chip Cookies",
        "description": "The best homemade chocolate chip cookies.",
        "author": {"@type": "Person", "name": "Test Chef"},
        "prepTime": "PT15M",
        "cookTime": "PT11M",
        "totalTime": "PT26M",
        "recipeYield": "48 servings",
        "recipeIngredient": [
            "2 1/4 cups all-purpose flour",
            "1 cup butter, softened",
            "3/4 cup granulated sugar",
            "3/4 cup packed brown sugar",
            "2 large eggs",
            "1 tsp vanilla extract",
            "1 tsp baking soda",
            "1 tsp salt",
            "2 cups chocolate chips"
        ],
        "recipeInstructions": [
            {"@type": "HowToStep", "text": "Preheat oven to 375°F."},
            {"@type": "HowToStep", "text": "Cream butter and sugars until fluffy."},
            {"@type": "HowToStep", "text": "Beat in eggs and vanilla."},
            {"@type": "HowToStep", "text": "Mix in flour, baking soda, and salt."},
            {"@type": "HowToStep", "text": "Fold in chocolate chips."},
            {"@type": "HowToStep", "text": "Bake 9-11 minutes until golden."}
        ]
    }
    </script>
</head>
<body>
    <h1>Classic Chocolate Chip Cookies</h1>
</body>
</html>
"""


@pytest.fixture
def recipe_test_settings(redis_url: str) -> Settings:
    """Create test settings with all services configured."""
    parts = redis_url.replace("redis://", "").split(":")
    redis_host = parts[0]
    redis_port = int(parts[1])

    return Settings(
        APP_ENV="test",
        JWT_SECRET_KEY="e2e-test-jwt-secret-key-for-recipes",
        REDIS_PASSWORD="",
        app=AppSettings(
            name="e2e-recipe-test-app",
            version="0.0.1-e2e",
            debug=True,
        ),
        server=ServerSettings(
            host="0.0.0.0",
            port=8000,
        ),
        api=ApiSettings(
            cors_origins=["http://localhost:3000"],
        ),
        auth=AuthSettings(
            mode="header",  # Use header mode for easy E2E testing
        ),
        redis=RedisSettings(
            host=redis_host,
            port=redis_port,
            cache_db=0,
            queue_db=1,
            rate_limit_db=2,
        ),
        rate_limiting=RateLimitingSettings(
            default="100/minute",
            auth="10/minute",
        ),
        logging=LoggingSettings(
            level="DEBUG",
            format="json",
        ),
        observability=ObservabilitySettings(),
        scraping=ScrapingSettings(
            fetch_timeout=30.0,
            cache_enabled=False,  # Disable cache for cleaner tests
            cache_ttl=3600,
        ),
        llm=LLMSettings(enabled=True),
        downstream_services=DownstreamServicesSettings(
            recipe_management=RecipeManagementServiceSettings(
                url="http://recipe-management-service:8080/api/v1/recipe-management",
                timeout=30.0,
            ),
        ),
    )


@pytest.fixture
async def recipe_app(recipe_test_settings: Settings) -> AsyncGenerator[FastAPI]:
    """Create FastAPI app with recipe test settings and initialized services."""
    # Clear the lru_cache on get_settings to allow our patch to work
    _get_settings.cache_clear()

    # Set up header auth provider with no default roles
    # This allows tests to explicitly control permissions via headers
    provider = HeaderAuthProvider(
        user_id_header="X-User-ID",
        roles_header="X-User-Roles",
        permissions_header="X-User-Permissions",
        default_roles=[],  # Don't default to "user" role
    )
    await provider.initialize()
    set_auth_provider(provider)

    scraper_service = None
    recipe_management_client = None
    llm_client = None

    try:
        with (
            patch(
                "app.observability.metrics.get_settings",
                return_value=recipe_test_settings,
            ),
            patch(
                "app.observability.tracing.get_settings",
                return_value=recipe_test_settings,
            ),
            patch(
                "app.core.config.get_settings",
                return_value=recipe_test_settings,
            ),
            patch(
                "app.core.config.settings.get_settings",
                return_value=recipe_test_settings,
            ),
            patch(
                "app.services.scraping.service.get_settings",
                return_value=recipe_test_settings,
            ),
            patch(
                "app.services.recipe_management.client.get_settings",
                return_value=recipe_test_settings,
            ),
        ):
            # Initialize services inside patch context so they use test settings
            scraper_service = RecipeScraperService(cache_client=None)
            await scraper_service.initialize()

            recipe_management_client = RecipeManagementClient()
            await recipe_management_client.initialize()

            llm_client = OllamaClient(
                base_url="http://localhost:11434",
                model="mistral:7b",
                cache_enabled=False,
            )
            await llm_client.initialize()

            with patch(
                "app.api.dependencies.get_llm_client",
                return_value=llm_client,
            ):
                app = create_app(recipe_test_settings)
                # Set services on app state
                app.state.scraper_service = scraper_service
                app.state.recipe_management_client = recipe_management_client
                yield app
    finally:
        if scraper_service:
            await scraper_service.shutdown()
        if recipe_management_client:
            await recipe_management_client.shutdown()
        if llm_client:
            await llm_client.shutdown()
        await shutdown_auth_provider()
        # Clear the cache again to reset for other tests
        _get_settings.cache_clear()


@pytest.fixture
async def recipe_client(recipe_app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """Create async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=recipe_app),
        base_url="http://test",
    ) as ac:
        yield ac


def auth_headers(
    user_id: str = "e2e-test-user",
    roles: str = "user",
    permissions: str = "recipe:create,recipe:read",
) -> dict[str, str]:
    """Create auth headers for header-based authentication."""
    return {
        "Authorization": "Bearer ignored-in-header-mode",
        "X-User-ID": user_id,
        "X-User-Roles": roles,
        "X-User-Permissions": permissions,
    }


class TestRecipeCreationE2E:
    """E2E tests for the full recipe creation flow."""

    @respx.mock
    async def test_create_recipe_full_flow(
        self,
        recipe_client: AsyncClient,
    ) -> None:
        """Test the complete recipe creation flow with all services mocked."""
        recipe_url = "https://example.com/recipes/chocolate-chip-cookies"

        # Mock the external recipe website
        respx.get(recipe_url).mock(
            return_value=httpx.Response(200, text=SAMPLE_RECIPE_HTML)
        )

        # Mock the LLM endpoint for ingredient parsing
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json=get_recorded_response("ingredient_batch_parsing"),
            )
        )

        # Mock the Recipe Management Service
        respx.post(
            "http://recipe-management-service:8080/api/v1/recipe-management/recipes"
        ).mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": 42,
                    "title": "Classic Chocolate Chip Cookies",
                    "slug": "classic-chocolate-chip-cookies",
                },
            )
        )

        # Make the request
        response = await recipe_client.post(
            "/api/v1/recipe-scraper/recipes",
            json={"recipeUrl": recipe_url},
            headers=auth_headers(),
        )

        # Verify response
        assert response.status_code == 201
        data = response.json()

        assert "recipe" in data
        recipe = data["recipe"]

        assert recipe["recipeId"] == 42
        assert recipe["title"] == "Classic Chocolate Chip Cookies"
        assert recipe["description"] == "The best homemade chocolate chip cookies."
        assert recipe["originUrl"] == recipe_url
        assert recipe["servings"] == 48.0
        assert recipe["preparationTime"] == 15
        assert recipe["cookingTime"] == 11

        # Verify ingredients were parsed
        assert len(recipe["ingredients"]) == 9
        assert recipe["ingredients"][0]["name"] == "all-purpose flour"
        assert recipe["ingredients"][0]["quantity"]["amount"] == 2.25
        assert recipe["ingredients"][0]["quantity"]["measurement"] == "CUP"

        # Verify steps were extracted
        assert len(recipe["steps"]) == 6
        assert recipe["steps"][0]["stepNumber"] == 1
        assert "Preheat oven" in recipe["steps"][0]["instruction"]

    @respx.mock
    async def test_create_recipe_scraping_failure(
        self,
        recipe_client: AsyncClient,
    ) -> None:
        """Test handling of scraping failures."""
        recipe_url = "https://example.com/bad-recipe"

        # Mock a 404 response from the recipe website
        respx.get(recipe_url).mock(return_value=httpx.Response(404, text="Not Found"))

        response = await recipe_client.post(
            "/api/v1/recipe-scraper/recipes",
            json={"recipeUrl": recipe_url},
            headers=auth_headers(),
        )

        assert response.status_code == 400
        data = response.json()
        assert "INVALID_RECIPE_URL" in data["message"]

    @respx.mock
    async def test_create_recipe_no_recipe_data(
        self,
        recipe_client: AsyncClient,
    ) -> None:
        """Test handling when page has no recipe data."""
        recipe_url = "https://example.com/not-a-recipe"

        # Mock a page with no recipe data
        respx.get(recipe_url).mock(
            return_value=httpx.Response(
                200,
                text="<html><body><h1>Just a regular page</h1></body></html>",
            )
        )

        response = await recipe_client.post(
            "/api/v1/recipe-scraper/recipes",
            json={"recipeUrl": recipe_url},
            headers=auth_headers(),
        )

        assert response.status_code == 400
        data = response.json()
        assert "RECIPE_NOT_FOUND" in data["message"]

    @respx.mock
    async def test_create_recipe_downstream_service_unavailable(
        self,
        recipe_client: AsyncClient,
    ) -> None:
        """Test handling when Recipe Management Service is unavailable."""
        recipe_url = "https://example.com/recipes/test"

        # Mock the recipe website
        respx.get(recipe_url).mock(
            return_value=httpx.Response(200, text=SAMPLE_RECIPE_HTML)
        )

        # Mock LLM
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json=get_recorded_response("ingredient_batch_parsing"),
            )
        )

        # Mock downstream service failure
        respx.post(
            "http://recipe-management-service:8080/api/v1/recipe-management/recipes"
        ).mock(side_effect=httpx.ConnectError("Connection refused"))

        response = await recipe_client.post(
            "/api/v1/recipe-scraper/recipes",
            json={"recipeUrl": recipe_url},
            headers=auth_headers(),
        )

        assert response.status_code == 503
        data = response.json()
        assert "SERVICE_UNAVAILABLE" in data["message"]

    @respx.mock
    async def test_create_recipe_downstream_validation_error(
        self,
        recipe_client: AsyncClient,
    ) -> None:
        """Test handling of downstream validation errors."""
        recipe_url = "https://example.com/recipes/test"

        # Mock the recipe website
        respx.get(recipe_url).mock(
            return_value=httpx.Response(200, text=SAMPLE_RECIPE_HTML)
        )

        # Mock LLM
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json=get_recorded_response("ingredient_batch_parsing"),
            )
        )

        # Mock downstream 422 validation error
        respx.post(
            "http://recipe-management-service:8080/api/v1/recipe-management/recipes"
        ).mock(
            return_value=httpx.Response(
                422,
                json={
                    "message": "Title must be unique",
                    "details": [{"field": "title", "error": "Already exists"}],
                },
            )
        )

        response = await recipe_client.post(
            "/api/v1/recipe-scraper/recipes",
            json={"recipeUrl": recipe_url},
            headers=auth_headers(),
        )

        assert response.status_code == 422
        data = response.json()
        assert "VALIDATION_ERROR" in data["message"]

    async def test_create_recipe_unauthorized(
        self,
        recipe_client: AsyncClient,
    ) -> None:
        """Test that unauthenticated requests are rejected."""
        response = await recipe_client.post(
            "/api/v1/recipe-scraper/recipes",
            json={"recipeUrl": "https://example.com/recipe"},
        )

        assert response.status_code == 401

    async def test_create_recipe_forbidden_without_permission(
        self,
        recipe_client: AsyncClient,
    ) -> None:
        """Test that requests without recipe:create permission are rejected."""
        # Must use empty roles to avoid role-based permissions
        # (the "user" role includes recipe:create by default)
        response = await recipe_client.post(
            "/api/v1/recipe-scraper/recipes",
            json={"recipeUrl": "https://example.com/recipe"},
            headers=auth_headers(roles="", permissions="recipe:read"),
        )

        assert response.status_code == 403


class TestRecipeCreationE2ETimeout:
    """E2E tests for timeout scenarios."""

    @respx.mock
    async def test_create_recipe_scraping_timeout(
        self,
        recipe_client: AsyncClient,
    ) -> None:
        """Test handling of scraping timeout."""
        recipe_url = "https://slow-website.com/recipe"

        # Mock a timeout
        respx.get(recipe_url).mock(side_effect=httpx.TimeoutException("Timeout"))

        response = await recipe_client.post(
            "/api/v1/recipe-scraper/recipes",
            json={"recipeUrl": recipe_url},
            headers=auth_headers(),
        )

        assert response.status_code == 504
        data = response.json()
        assert "SCRAPING_TIMEOUT" in data["message"]
