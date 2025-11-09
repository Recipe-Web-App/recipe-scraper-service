"""Service token manager for OAuth2 service-to-service authentication.

Handles acquisition and caching of OAuth2 access tokens for calling downstream services
using the client credentials grant type.
"""

import base64
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import HTTPException

from app.api.v1.schemas.downstream.auth_service import TokenResponse
from app.core.config.config import settings
from app.core.config.service_urls import ServiceURLs
from app.core.logging import get_logger
from app.exceptions.custom_exceptions import DownstreamAuthenticationError

_log = get_logger(__name__)


class ServiceTokenManager:
    """Manages OAuth2 service tokens for downstream service calls.

    Handles token acquisition via client credentials flow and stores tokens as class
    attributes (singleton pattern ensures single instance).
    """

    def __init__(self) -> None:
        """Initialize the service token manager."""
        self._http_client: httpx.AsyncClient | None = None
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None
        self._token_scope: str | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client.

        Returns:
            Configured HTTP client instance
        """
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=10.0)
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client and cleanup resources."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def get_service_token(self, scope: str | None = None) -> str:
        """Get a valid service access token.

        Checks if a valid token is already stored. If not, or if the stored token
        has expired or has a different scope, requests a new token from auth service.

        Args:
            scope: Optional OAuth2 scope (e.g., "notification:admin")

        Returns:
            Valid access token string

        Raises:
            DownstreamAuthenticationError: If authentication with auth service fails
            HTTPException: If auth service is unavailable or returns an error
        """
        # Check if we have a valid cached token with the right scope
        if (
            self._access_token
            and self._token_expires_at
            and self._token_scope == scope
            and datetime.now(UTC) < self._token_expires_at
        ):
            _log.debug("Using stored service token for scope: {}", scope or "default")
            return self._access_token

        # Need to request a new token
        _log.info(
            "Requesting new service token from auth-service for scope: {}",
            scope or "default",
        )
        token_response = await self._request_token_from_auth_service(scope)

        # Store the token with 60 second safety margin before expiry
        self._access_token = token_response.access_token
        self._token_expires_at = datetime.now(UTC) + timedelta(
            seconds=token_response.expires_in - 60
        )
        self._token_scope = scope

        _log.debug(
            "Stored new service token (expires in {} seconds)",
            token_response.expires_in - 60,
        )
        return self._access_token

    async def _request_token_from_auth_service(
        self,
        scope: str | None = None,
    ) -> TokenResponse:
        """Request a new token from the auth service via client credentials flow.

        Args:
            scope: Optional OAuth2 scope to request

        Returns:
            Token response from auth service

        Raises:
            DownstreamAuthenticationError: If authentication fails (401)
            HTTPException: If auth service returns error or is unavailable
        """
        token_url = ServiceURLs.auth_service_token_url()
        basic_auth_header = self._build_basic_auth_header()

        # Build request form data
        form_data = {"grant_type": "client_credentials"}
        if scope:
            form_data["scope"] = scope

        headers = {
            "Authorization": basic_auth_header,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            client = await self._get_http_client()
            response = await client.post(
                token_url,
                data=form_data,
                headers=headers,
            )

            # Handle HTTP errors
            if response.status_code == 401:
                _log.error("Authentication with auth-service failed (401 Unauthorized)")
                raise DownstreamAuthenticationError(
                    service_name="auth-service",
                    status_code=401,
                )

            response.raise_for_status()

            # Parse and validate response
            token_data = response.json()
            return TokenResponse(**token_data)

        except DownstreamAuthenticationError:
            # Re-raise authentication errors as-is
            raise

        except httpx.HTTPStatusError as e:
            _log.error(
                "Auth-service returned HTTP error {}: {}",
                e.response.status_code,
                e.response.text,
            )
            raise HTTPException(
                status_code=503,
                detail=f"Auth service unavailable (HTTP {e.response.status_code})",
            ) from e

        except httpx.RequestError as e:
            _log.error("Failed to connect to auth-service: {}", e)
            raise HTTPException(
                status_code=503,
                detail="Auth service unavailable (connection error)",
            ) from e

        except Exception as e:
            _log.error("Unexpected error requesting service token: {}", e)
            raise HTTPException(
                status_code=503,
                detail="Auth service unavailable (unexpected error)",
            ) from e

    def _build_basic_auth_header(self) -> str:
        """Build HTTP Basic Authorization header from client credentials.

        Returns:
            Basic auth header value (e.g., "Basic base64(client_id:client_secret)")

        Raises:
            ValueError: If client credentials are not configured
        """
        client_id = settings.oauth2_client_id
        client_secret = settings.oauth2_client_secret

        if not client_id or not client_secret:
            _log.error("OAuth2 client credentials not configured")
            raise ValueError("OAuth2 client credentials not configured")

        # Encode client_id:client_secret as base64
        credentials = f"{client_id}:{client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode(
            "utf-8"
        )

        return f"Basic {encoded_credentials}"
