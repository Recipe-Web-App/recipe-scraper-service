"""Unit tests for RecipeManagementClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import orjson
import pytest

from app.services.recipe_management.client import RecipeManagementClient
from app.services.recipe_management.exceptions import (
    RecipeManagementNotFoundError,
    RecipeManagementResponseError,
    RecipeManagementTimeoutError,
    RecipeManagementUnavailableError,
    RecipeManagementValidationError,
)
from app.services.recipe_management.schemas import (
    CreateRecipeIngredientRequest,
    CreateRecipeRequest,
    CreateRecipeStepRequest,
    IngredientUnit,
)


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings."""
    settings = MagicMock()
    settings.downstream_services.recipe_management.url = (
        "http://localhost:8081/api/v1/recipe-management"
    )
    settings.downstream_services.recipe_management.timeout = 10.0
    return settings


@pytest.fixture
def client(mock_settings: MagicMock) -> RecipeManagementClient:
    """Create a RecipeManagementClient with mocked settings."""
    with patch(
        "app.services.recipe_management.client.get_settings",
        return_value=mock_settings,
    ):
        return RecipeManagementClient()


@pytest.fixture
def sample_request() -> CreateRecipeRequest:
    """Create a sample recipe creation request."""
    return CreateRecipeRequest(
        title="Test Recipe",
        description="A test recipe description",
        servings=4,
        preparation_time=15,
        cooking_time=30,
        ingredients=[
            CreateRecipeIngredientRequest(
                ingredient_name="flour",
                quantity=2.0,
                unit=IngredientUnit.CUP,
            ),
            CreateRecipeIngredientRequest(
                ingredient_name="eggs",
                quantity=2.0,
                unit=IngredientUnit.PIECE,
            ),
        ],
        steps=[
            CreateRecipeStepRequest(
                step_number=1,
                instruction="Mix the ingredients",
            ),
            CreateRecipeStepRequest(
                step_number=2,
                instruction="Bake at 350F for 30 minutes",
            ),
        ],
    )


class TestRecipeManagementClientLifecycle:
    """Tests for client lifecycle methods."""

    async def test_initialize_creates_http_client(
        self,
        client: RecipeManagementClient,
    ) -> None:
        """Should create HTTP client on initialize."""
        assert client._http_client is None

        await client.initialize()

        assert client._http_client is not None
        assert isinstance(client._http_client, httpx.AsyncClient)

        await client.shutdown()

    async def test_shutdown_closes_http_client(
        self,
        client: RecipeManagementClient,
    ) -> None:
        """Should close HTTP client on shutdown."""
        await client.initialize()
        assert client._http_client is not None

        await client.shutdown()

        assert client._http_client is None

    def test_base_url_returns_configured_url(
        self,
        client: RecipeManagementClient,
    ) -> None:
        """Should return configured base URL."""
        assert client.base_url == "http://localhost:8081/api/v1/recipe-management"

    def test_base_url_raises_when_not_configured(self) -> None:
        """Should raise RuntimeError when URL not configured."""
        mock_settings = MagicMock()
        mock_settings.downstream_services.recipe_management.url = None

        with patch(
            "app.services.recipe_management.client.get_settings",
            return_value=mock_settings,
        ):
            client = RecipeManagementClient()
            with pytest.raises(RuntimeError, match="not configured"):
                _ = client.base_url


class TestRecipeManagementClientCreateRecipe:
    """Tests for create_recipe method."""

    async def test_create_recipe_success(
        self,
        client: RecipeManagementClient,
        sample_request: CreateRecipeRequest,
    ) -> None:
        """Should create recipe and return response."""
        await client.initialize()

        response_data = {"id": 123, "title": "Test Recipe", "slug": "test-recipe"}

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = orjson.dumps(response_data)

        client._http_client.post = AsyncMock(return_value=mock_response)  # type: ignore[union-attr]

        result = await client.create_recipe(sample_request, "test-token")

        assert result.id == 123
        assert result.title == "Test Recipe"
        assert result.slug == "test-recipe"

        await client.shutdown()

    async def test_create_recipe_sends_correct_payload(
        self,
        client: RecipeManagementClient,
        sample_request: CreateRecipeRequest,
    ) -> None:
        """Should send correctly formatted payload with camelCase."""
        await client.initialize()

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = orjson.dumps({"id": 1, "title": "Test", "slug": "test"})

        client._http_client.post = AsyncMock(return_value=mock_response)  # type: ignore[union-attr]

        await client.create_recipe(sample_request, "test-token")

        # Verify the payload format
        call_args = client._http_client.post.call_args  # type: ignore[union-attr]
        payload = orjson.loads(call_args.kwargs["content"])

        assert "ingredientName" in str(payload)  # camelCase
        assert "stepNumber" in str(payload)  # camelCase
        assert payload["title"] == "Test Recipe"
        assert payload["servings"] == 4

        await client.shutdown()

    async def test_create_recipe_sends_auth_header(
        self,
        client: RecipeManagementClient,
        sample_request: CreateRecipeRequest,
    ) -> None:
        """Should send Authorization header."""
        await client.initialize()

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = orjson.dumps({"id": 1, "title": "Test", "slug": "test"})

        client._http_client.post = AsyncMock(return_value=mock_response)  # type: ignore[union-attr]

        await client.create_recipe(sample_request, "my-auth-token")

        call_args = client._http_client.post.call_args  # type: ignore[union-attr]
        headers = call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer my-auth-token"

        await client.shutdown()

    async def test_create_recipe_raises_when_not_initialized(
        self,
        client: RecipeManagementClient,
        sample_request: CreateRecipeRequest,
    ) -> None:
        """Should raise RuntimeError if client not initialized."""
        with pytest.raises(RuntimeError, match="not initialized"):
            await client.create_recipe(sample_request, "token")

    async def test_create_recipe_raises_timeout_error(
        self,
        client: RecipeManagementClient,
        sample_request: CreateRecipeRequest,
    ) -> None:
        """Should raise RecipeManagementTimeoutError on timeout."""
        await client.initialize()

        client._http_client.post = AsyncMock(  # type: ignore[union-attr]
            side_effect=httpx.TimeoutException("timeout")
        )

        with pytest.raises(RecipeManagementTimeoutError):
            await client.create_recipe(sample_request, "token")

        await client.shutdown()

    async def test_create_recipe_raises_unavailable_error(
        self,
        client: RecipeManagementClient,
        sample_request: CreateRecipeRequest,
    ) -> None:
        """Should raise RecipeManagementUnavailableError on connection error."""
        await client.initialize()

        client._http_client.post = AsyncMock(  # type: ignore[union-attr]
            side_effect=httpx.RequestError("Connection refused")
        )

        with pytest.raises(RecipeManagementUnavailableError):
            await client.create_recipe(sample_request, "token")

        await client.shutdown()

    async def test_create_recipe_raises_validation_error_on_422(
        self,
        client: RecipeManagementClient,
        sample_request: CreateRecipeRequest,
    ) -> None:
        """Should raise RecipeManagementValidationError on 422 response."""
        await client.initialize()

        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.content = orjson.dumps(
            {
                "message": "Validation failed",
                "details": [{"field": "title", "error": "too short"}],
            }
        )

        client._http_client.post = AsyncMock(return_value=mock_response)  # type: ignore[union-attr]

        with pytest.raises(RecipeManagementValidationError) as exc_info:
            await client.create_recipe(sample_request, "token")

        assert "Validation failed" in str(exc_info.value)

        await client.shutdown()

    async def test_create_recipe_raises_response_error_on_other_errors(
        self,
        client: RecipeManagementClient,
        sample_request: CreateRecipeRequest,
    ) -> None:
        """Should raise RecipeManagementResponseError on non-422 errors."""
        await client.initialize()

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.content = orjson.dumps({"message": "Internal server error"})

        client._http_client.post = AsyncMock(return_value=mock_response)  # type: ignore[union-attr]

        with pytest.raises(RecipeManagementResponseError) as exc_info:
            await client.create_recipe(sample_request, "token")

        assert exc_info.value.status_code == 500

        await client.shutdown()


class TestCreateRecipeRequestSerialization:
    """Tests for request schema serialization."""

    def test_serializes_with_camel_case(self) -> None:
        """Should serialize with camelCase aliases."""
        request = CreateRecipeRequest(
            title="Test",
            description="Test desc",
            servings=4,
            preparation_time=15,
            cooking_time=30,
            ingredients=[
                CreateRecipeIngredientRequest(
                    ingredient_name="flour",
                    quantity=1.0,
                    unit=IngredientUnit.CUP,
                    is_optional=True,
                ),
            ],
            steps=[
                CreateRecipeStepRequest(
                    step_number=1,
                    instruction="Mix",
                    timer_seconds=60,
                ),
            ],
        )

        data = request.model_dump(by_alias=True)

        assert "preparationTime" in data
        assert "cookingTime" in data
        assert data["ingredients"][0]["ingredientName"] == "flour"
        assert data["ingredients"][0]["isOptional"] is True
        assert data["steps"][0]["stepNumber"] == 1
        assert data["steps"][0]["timerSeconds"] == 60

    def test_excludes_none_values(self) -> None:
        """Should exclude None values when serializing."""
        request = CreateRecipeRequest(
            title="Test",
            description="Test desc",
            servings=4,
            ingredients=[
                CreateRecipeIngredientRequest(
                    ingredient_name="flour",
                    quantity=1.0,
                    unit=IngredientUnit.CUP,
                ),
            ],
            steps=[
                CreateRecipeStepRequest(
                    step_number=1,
                    instruction="Mix",
                ),
            ],
        )

        data = request.model_dump(by_alias=True, exclude_none=True)

        assert "preparationTime" not in data
        assert "cookingTime" not in data
        assert "difficulty" not in data


class TestRecipeManagementClientGetRecipe:
    """Tests for get_recipe method."""

    async def test_get_recipe_success(
        self,
        client: RecipeManagementClient,
    ) -> None:
        """Should fetch recipe and return response."""
        await client.initialize()

        response_data = {
            "id": 123,
            "title": "Test Recipe",
            "slug": "test-recipe",
            "description": "A test recipe",
            "servings": 4,
            "ingredients": [
                {
                    "id": 1,
                    "ingredientName": "flour",
                    "quantity": 2.0,
                    "unit": "CUP",
                }
            ],
            "steps": [{"id": 1, "stepNumber": 1, "instruction": "Mix"}],
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = orjson.dumps(response_data)

        client._http_client.get = AsyncMock(return_value=mock_response)  # type: ignore[union-attr]

        result = await client.get_recipe(123, "test-token")

        assert result.id == 123
        assert result.title == "Test Recipe"
        assert len(result.ingredients) == 1

        await client.shutdown()

    async def test_get_recipe_sends_auth_header(
        self,
        client: RecipeManagementClient,
    ) -> None:
        """Should send Authorization header."""
        await client.initialize()

        response_data = {
            "id": 1,
            "title": "Test",
            "slug": "test",
            "description": "desc",
            "servings": 2,
            "ingredients": [],
            "steps": [],
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = orjson.dumps(response_data)

        client._http_client.get = AsyncMock(return_value=mock_response)  # type: ignore[union-attr]

        await client.get_recipe(1, "my-auth-token")

        call_args = client._http_client.get.call_args  # type: ignore[union-attr]
        headers = call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer my-auth-token"

        await client.shutdown()

    async def test_get_recipe_raises_when_not_initialized(
        self,
        client: RecipeManagementClient,
    ) -> None:
        """Should raise RuntimeError if client not initialized."""
        with pytest.raises(RuntimeError, match="not initialized"):
            await client.get_recipe(123, "token")

    async def test_get_recipe_raises_not_found_on_404(
        self,
        client: RecipeManagementClient,
    ) -> None:
        """Should raise RecipeManagementNotFoundError on 404."""
        await client.initialize()

        mock_response = MagicMock()
        mock_response.status_code = 404

        client._http_client.get = AsyncMock(return_value=mock_response)  # type: ignore[union-attr]

        with pytest.raises(RecipeManagementNotFoundError):
            await client.get_recipe(999, "token")

        await client.shutdown()

    async def test_get_recipe_raises_timeout_error(
        self,
        client: RecipeManagementClient,
    ) -> None:
        """Should raise RecipeManagementTimeoutError on timeout."""
        await client.initialize()

        client._http_client.get = AsyncMock(  # type: ignore[union-attr]
            side_effect=httpx.TimeoutException("timeout")
        )

        with pytest.raises(RecipeManagementTimeoutError):
            await client.get_recipe(123, "token")

        await client.shutdown()

    async def test_get_recipe_raises_unavailable_error(
        self,
        client: RecipeManagementClient,
    ) -> None:
        """Should raise RecipeManagementUnavailableError on connection error."""
        await client.initialize()

        client._http_client.get = AsyncMock(  # type: ignore[union-attr]
            side_effect=httpx.RequestError("Connection refused")
        )

        with pytest.raises(RecipeManagementUnavailableError):
            await client.get_recipe(123, "token")

        await client.shutdown()

    async def test_get_recipe_raises_response_error_on_server_error(
        self,
        client: RecipeManagementClient,
    ) -> None:
        """Should raise RecipeManagementResponseError on 500."""
        await client.initialize()

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.content = orjson.dumps({"message": "Internal error"})

        client._http_client.get = AsyncMock(return_value=mock_response)  # type: ignore[union-attr]

        with pytest.raises(RecipeManagementResponseError) as exc_info:
            await client.get_recipe(123, "token")

        assert exc_info.value.status_code == 500

        await client.shutdown()


class TestRecipeManagementClientErrorHandling:
    """Tests for error response handling edge cases."""

    async def test_handles_invalid_json_in_error_response(
        self,
        client: RecipeManagementClient,
        sample_request: CreateRecipeRequest,
    ) -> None:
        """Should handle non-JSON error response body."""
        await client.initialize()

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.content = b"Not valid JSON"
        mock_response.text = "Internal Server Error"

        client._http_client.post = AsyncMock(return_value=mock_response)  # type: ignore[union-attr]

        with pytest.raises(RecipeManagementResponseError) as exc_info:
            await client.create_recipe(sample_request, "token")

        assert exc_info.value.status_code == 500
        assert "Internal Server Error" in str(exc_info.value)

        await client.shutdown()

    async def test_handles_empty_error_response_body(
        self,
        client: RecipeManagementClient,
        sample_request: CreateRecipeRequest,
    ) -> None:
        """Should handle empty error response body."""
        await client.initialize()

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.content = b""
        mock_response.text = ""

        client._http_client.post = AsyncMock(return_value=mock_response)  # type: ignore[union-attr]

        with pytest.raises(RecipeManagementResponseError) as exc_info:
            await client.create_recipe(sample_request, "token")

        assert exc_info.value.status_code == 503

        await client.shutdown()
