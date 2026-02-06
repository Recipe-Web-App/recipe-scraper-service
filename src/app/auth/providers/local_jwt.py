"""Local JWT authentication provider.

This provider validates JWTs locally using a shared secret key.
Use this when:
- Running in a distributed environment where auth-service may be unavailable
- The auth-service and this service share the same JWT secret
- You need offline token validation capability
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError

from app.auth.providers.exceptions import TokenExpiredError, TokenInvalidError
from app.auth.providers.models import AuthResult
from app.observability.logging import get_logger


if TYPE_CHECKING:
    from starlette.requests import Request

logger = get_logger(__name__)


class LocalJWTAuthProvider:
    """Validates JWTs locally using the configured secret key.

    This provider performs JWT validation without calling any external service.
    It's suitable for:
    - Development environments
    - Distributed systems with shared JWT secrets
    - Fallback when introspection is unavailable

    Attributes:
        secret_key: The secret key for HS256 or public key for RS256.
        algorithm: JWT signing algorithm (default: HS256).
        issuer: Expected 'iss' claim value (optional).
        audience: Expected 'aud' claim values (optional).
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        issuer: str | None = None,
        audience: list[str] | None = None,
    ) -> None:
        """Initialize the local JWT provider.

        Args:
            secret_key: Secret key for token verification.
            algorithm: JWT algorithm (HS256, RS256, etc.).
            issuer: Expected issuer claim. If None, issuer is not validated.
            audience: Expected audience claims. If None/empty, audience is not validated.
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.issuer = issuer
        self.audience = audience if audience else None
        self._initialized = False

    @property
    def provider_name(self) -> str:
        """Return provider name for logging."""
        return "local_jwt"

    async def validate_token(
        self,
        token: str,
        _request: Request | None = None,
    ) -> AuthResult:
        """Validate JWT locally and return authentication result.

        Args:
            token: The JWT to validate.
            _request: Unused in this provider.

        Returns:
            AuthResult with validated user information.

        Raises:
            TokenExpiredError: If the token has expired.
            TokenInvalidError: If the token is malformed or signature fails.
        """
        try:
            # Build decode options
            options: dict[str, bool] = {}
            decode_kwargs: dict[str, Any] = {
                "algorithms": [self.algorithm],
            }

            if self.issuer:
                decode_kwargs["issuer"] = self.issuer
            if self.audience:
                decode_kwargs["audience"] = self.audience

            payload = jwt.decode(
                token,
                self.secret_key,
                options=options,
                **decode_kwargs,
            )

            # Verify token type is 'access'
            token_type = payload.get("type", "access")
            if token_type not in ("access", "api_key"):
                msg = f"Invalid token type: {token_type}. Expected 'access'."
                raise TokenInvalidError(msg)

            # Extract user information
            user_id = payload.get("sub")
            if not user_id:
                msg = "Token missing 'sub' claim"
                raise TokenInvalidError(msg)

            # Handle audience as string or list
            aud = payload.get("aud")
            audience_list: list[str] = []
            if aud:
                audience_list = [aud] if isinstance(aud, str) else list(aud)

            return AuthResult(
                user_id=user_id,
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
                scopes=payload.get("scope", "").split() if payload.get("scope") else [],
                token_type=token_type,
                issuer=payload.get("iss"),
                audience=audience_list,
                expires_at=payload.get("exp"),
                issued_at=payload.get("iat"),
                raw_claims=payload,
            )

        except ExpiredSignatureError as e:
            logger.debug("Token expired during local validation")
            msg = "Token has expired"
            raise TokenExpiredError(msg) from e

        except JWTClaimsError as e:
            # Issuer or audience mismatch
            logger.warning("JWT claims validation failed", error=str(e))
            raise TokenInvalidError(str(e)) from e

        except JWTError as e:
            logger.warning("JWT validation failed", error=str(e))
            msg = "Invalid token"
            raise TokenInvalidError(msg) from e

    async def initialize(self) -> None:
        """Initialize the provider.

        For local JWT, this just validates that a secret key is configured.
        """
        if not self.secret_key:
            msg = "JWT secret key is not configured"
            raise TokenInvalidError(msg)

        logger.info(
            "LocalJWTAuthProvider initialized",
            algorithm=self.algorithm,
            issuer_validation=self.issuer is not None,
            audience_validation=self.audience is not None,
        )
        self._initialized = True

    async def shutdown(self) -> None:
        """Shutdown the provider. No cleanup needed for local JWT."""
        logger.debug("LocalJWTAuthProvider shutdown")
        self._initialized = False
