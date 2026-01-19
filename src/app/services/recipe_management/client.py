"""Recipe Management Service HTTP client.

This module provides an async HTTP client for interacting with the
downstream Recipe Management Service.
"""

from __future__ import annotations

import httpx
import orjson

from app.core.config import get_settings
from app.observability.logging import get_logger
from app.services.recipe_management.exceptions import (
    RecipeManagementResponseError,
    RecipeManagementTimeoutError,
    RecipeManagementUnavailableError,
    RecipeManagementValidationError,
)
from app.services.recipe_management.schemas import (
    CreateRecipeRequest,
    RecipeResponse,
)


logger = get_logger(__name__)


class RecipeManagementClient:
    """HTTP client for Recipe Management Service.

    Provides methods for creating and managing recipes via the
    downstream Recipe Management Service API.

    Example:
        ```python
        client = RecipeManagementClient()
        await client.initialize()

        recipe = await client.create_recipe(
            request=CreateRecipeRequest(...),
            auth_token="bearer_token",
        )

        await client.shutdown()
        ```
    """

    def __init__(self) -> None:
        """Initialize the client."""
        self._settings = get_settings()
        self._http_client: httpx.AsyncClient | None = None

    @property
    def base_url(self) -> str:
        """Get the base URL for the Recipe Management Service."""
        url = self._settings.downstream_services.recipe_management.url
        if not url:
            msg = "Recipe Management Service URL not configured"
            raise RuntimeError(msg)
        return url

    async def initialize(self) -> None:
        """Initialize HTTP client."""
        timeout = self._settings.downstream_services.recipe_management.timeout
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        logger.info(
            "RecipeManagementClient initialized",
            base_url=self.base_url,
        )

    async def shutdown(self) -> None:
        """Release resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        logger.debug("RecipeManagementClient shutdown")

    async def create_recipe(
        self,
        request: CreateRecipeRequest,
        auth_token: str,
    ) -> RecipeResponse:
        """Create a recipe in the Recipe Management Service.

        Args:
            request: Recipe creation request data.
            auth_token: Bearer token for authentication.

        Returns:
            RecipeResponse with the created recipe ID.

        Raises:
            RecipeManagementUnavailableError: If service is unreachable.
            RecipeManagementTimeoutError: If request times out.
            RecipeManagementValidationError: If request validation fails.
            RecipeManagementResponseError: For other HTTP errors.
        """
        if not self._http_client:
            msg = "Client not initialized. Call initialize() first."
            raise RuntimeError(msg)

        url = f"{self.base_url}/recipes"

        # Serialize with camelCase aliases
        payload = orjson.dumps(request.model_dump(by_alias=True, exclude_none=True))

        logger.debug(
            "Creating recipe in Recipe Management Service",
            url=url,
            title=request.title,
        )

        try:
            response = await self._http_client.post(
                url,
                content=payload,
                headers={
                    "Authorization": f"Bearer {auth_token}",
                },
            )

            if response.status_code == 201:
                data = orjson.loads(response.content)
                result = RecipeResponse.model_validate(data)
                logger.info(
                    "Recipe created successfully",
                    recipe_id=result.id,
                    title=result.title,
                )
                return result

            # Handle error responses
            await self._handle_error_response(response)

            # This line should not be reached
            msg = f"Unexpected response: {response.status_code}"
            raise RecipeManagementResponseError(response.status_code, msg)

        except httpx.TimeoutException as e:
            logger.warning("Request to Recipe Management Service timed out")
            raise RecipeManagementTimeoutError(str(e)) from e

        except httpx.RequestError as e:
            logger.warning(
                "Failed to connect to Recipe Management Service",
                error=str(e),
            )
            error_msg = f"Failed to connect to Recipe Management Service: {e}"
            raise RecipeManagementUnavailableError(error_msg) from e

    async def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle error responses from the downstream service.

        Args:
            response: HTTP response to handle.

        Raises:
            RecipeManagementValidationError: For 422 responses.
            RecipeManagementResponseError: For other error responses.
        """
        status_code = response.status_code

        try:
            error_body = orjson.loads(response.content)
            message = error_body.get("message", "Unknown error")
            details = error_body.get("details")
        except Exception:
            message = response.text or f"HTTP {status_code}"
            details = None

        logger.warning(
            "Recipe Management Service returned error",
            status_code=status_code,
            message=message,
        )

        if status_code == 422:
            raise RecipeManagementValidationError(message, details)

        raise RecipeManagementResponseError(status_code, message)
