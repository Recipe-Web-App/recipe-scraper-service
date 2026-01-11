"""Header-based authentication provider.

This provider extracts user information from request headers.
Use this ONLY for:
- Local development and testing
- Behind a trusted API gateway that has already authenticated the user

WARNING: This provider trusts header values completely. Never use in
production without a trusted upstream service setting these headers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.auth.providers.exceptions import AuthenticationError
from app.auth.providers.models import AuthResult
from app.observability.logging import get_logger


if TYPE_CHECKING:
    from starlette.requests import Request

logger = get_logger(__name__)


class HeaderAuthProvider:
    """Extracts user information from request headers.

    This provider is designed for:
    - Local development without running an auth service
    - Testing with controlled user contexts
    - Deployment behind a gateway that handles authentication

    The provider reads user ID, roles, and permissions from configurable
    headers. If the user ID header is missing, authentication fails.

    Attributes:
        user_id_header: Header name containing the user ID (required).
        roles_header: Header name containing comma-separated roles.
        permissions_header: Header name containing comma-separated permissions.
        default_roles: Roles to assign if roles header is missing.
    """

    def __init__(
        self,
        user_id_header: str = "X-User-ID",
        roles_header: str = "X-User-Roles",
        permissions_header: str = "X-User-Permissions",
        default_roles: list[str] | None = None,
    ) -> None:
        """Initialize the header auth provider.

        Args:
            user_id_header: Header name for user ID (default: X-User-ID).
            roles_header: Header name for roles (default: X-User-Roles).
            permissions_header: Header name for permissions (default: X-User-Permissions).
            default_roles: Default roles if header is missing (default: ["user"]).
        """
        self.user_id_header = user_id_header
        self.roles_header = roles_header
        self.permissions_header = permissions_header
        self.default_roles = default_roles or ["user"]
        self._initialized = False

    @property
    def provider_name(self) -> str:
        """Return provider name for logging."""
        return "header"

    async def validate_token(
        self,
        _token: str,
        request: Request | None = None,
    ) -> AuthResult:
        """Extract user information from request headers.

        Note: The _token parameter is ignored. This provider only uses headers.

        Args:
            token: Ignored in this provider.
            request: Request object to read headers from (required).

        Returns:
            AuthResult with user information from headers.

        Raises:
            AuthenticationError: If request is None or user ID header is missing.
        """
        if request is None:
            msg = "HeaderAuthProvider requires request object for header access"
            raise AuthenticationError(msg)

        # Get user ID (required)
        user_id = request.headers.get(self.user_id_header)
        if not user_id:
            msg = f"Missing required header: {self.user_id_header}"
            raise AuthenticationError(msg)

        # Parse roles (optional, comma-separated)
        roles_str = request.headers.get(self.roles_header, "")
        roles = [r.strip() for r in roles_str.split(",") if r.strip()]
        if not roles:
            roles = self.default_roles.copy()

        # Parse permissions (optional, comma-separated)
        perms_str = request.headers.get(self.permissions_header, "")
        permissions = [p.strip() for p in perms_str.split(",") if p.strip()]

        logger.debug(
            "Authenticated via headers",
            user_id=user_id,
            roles=roles,
            permissions_count=len(permissions),
        )

        return AuthResult(
            user_id=user_id,
            roles=roles,
            permissions=permissions,
            scopes=[],  # No scopes in header mode
            token_type="header",  # noqa: S106 - not a password
            issuer=None,
            audience=[],
            expires_at=None,
            issued_at=None,
            raw_claims={
                "source": "headers",
                "user_id_header": self.user_id_header,
            },
        )

    async def initialize(self) -> None:
        """Initialize the provider."""
        logger.info(
            "HeaderAuthProvider initialized",
            user_id_header=self.user_id_header,
            roles_header=self.roles_header,
            permissions_header=self.permissions_header,
        )
        logger.warning(
            "HeaderAuthProvider is enabled - ensure this is only used in "
            "development/testing or behind a trusted gateway"
        )
        self._initialized = True

    async def shutdown(self) -> None:
        """Shutdown the provider. No cleanup needed."""
        logger.debug("HeaderAuthProvider shutdown")
        self._initialized = False
