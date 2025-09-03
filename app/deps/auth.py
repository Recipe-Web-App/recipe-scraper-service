"""Authentication dependency utilities.

Provides functions and classes to handle authentication-related dependencies for FastAPI
routes, such as user authentication and authorization.
"""

from typing import Annotated, Any

from fastapi import Depends, Request

from app.api.v1.schemas.downstream.auth_service.introspection_response import (
    OAuth2IntrospectionResponse,
)
from app.core.config.config import get_settings
from app.core.logging import get_logger
from app.core.security import authenticate_token, require_authentication
from app.exceptions.custom_exceptions import InsufficientPermissionsError

_log = get_logger(__name__)
settings = get_settings()


class UserContext:
    """Container for authenticated user information."""

    def __init__(self, token_info: OAuth2IntrospectionResponse) -> None:
        """Initialize user context from token information.

        Args:
            token_info: The OAuth2 introspection response containing token details.
        """
        self.token_info = token_info
        self.user_id = token_info.sub
        self.username = token_info.username
        self.client_id = token_info.client_id
        self.scopes = token_info.scope.split() if token_info.scope else []
        self.is_service_to_service = (
            token_info.client_id is not None and token_info.sub is None
        )

    def has_scope(self, required_scope: str) -> bool:
        """Check if the user has a specific scope.

        Args:
            required_scope: The scope to check for.

        Returns:
            bool: True if the user has the required scope.
        """
        return required_scope in self.scopes

    def require_scope(self, required_scope: str) -> None:
        """Require a specific scope, raising an exception if not present.

        Args:
            required_scope: The scope that is required.

        Raises:
            InsufficientPermissionsError: If the required scope is not present.
        """
        if not self.has_scope(required_scope):
            raise InsufficientPermissionsError(required_scope)


async def get_optional_user_context(request: Request) -> UserContext | None:
    """Get user context if authentication is provided (optional).

    Args:
        request: The FastAPI request object.

    Returns:
        UserContext | None: The user context if authenticated, None otherwise.
    """
    if not settings.oauth2_service_enabled:
        return None

    token_info = await authenticate_token(request)
    if token_info is None:
        return None

    return UserContext(token_info)


async def get_required_user_context(request: Request) -> UserContext:
    """Get user context, requiring authentication.

    Args:
        request: The FastAPI request object.

    Returns:
        UserContext: The user context.

    Raises:
        AuthenticationRequiredError: If authentication is required but missing.
        InvalidTokenError: If the provided token is invalid.
        ExpiredTokenError: If the provided token has expired.
        OAuth2IntrospectionError: If OAuth2 introspection fails.
    """
    token_info = await require_authentication(request)
    return UserContext(token_info)


async def get_service_to_service_context(request: Request) -> UserContext:
    """Get service-to-service authentication context.

    Args:
        request: The FastAPI request object.

    Returns:
        UserContext: The service context.

    Raises:
        AuthenticationRequiredError: If authentication is required but missing.
        InvalidTokenError: If the provided token is invalid.
        InsufficientPermissionsError: If the token is not a service-to-service token.
    """
    if not settings.oauth2_service_to_service_enabled:
        raise InsufficientPermissionsError("Service-to-service authentication disabled")

    user_context = await get_required_user_context(request)

    if not user_context.is_service_to_service:
        raise InsufficientPermissionsError("Service-to-service token required")

    return user_context


def require_scope(required_scope: str) -> Any:
    """Create a dependency that requires a specific scope.

    Args:
        required_scope: The scope that is required.

    Returns:
        A dependency function that validates the required scope.
    """

    async def scope_dependency(
        user_context: Annotated[UserContext, Depends(get_required_user_context)],
    ) -> UserContext:
        user_context.require_scope(required_scope)
        return user_context

    return scope_dependency


# Common dependency aliases for convenience
OptionalAuth = Annotated[UserContext | None, Depends(get_optional_user_context)]
RequiredAuth = Annotated[UserContext, Depends(get_required_user_context)]
ServiceToServiceAuth = Annotated[UserContext, Depends(get_service_to_service_context)]
