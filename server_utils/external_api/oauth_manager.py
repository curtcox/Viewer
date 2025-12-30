"""OAuth token manager for external APIs."""

from dataclasses import dataclass
import time
from typing import Any, Dict, Optional, Tuple

from requests import Response

from .http_client import ExternalApiClient, HttpClientConfig


@dataclass
class OAuthTokens:
    """Container for OAuth tokens and expiry metadata."""

    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[float] = None
    token_type: str = "Bearer"

    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """Return True when the token is expired or will expire soon."""

        if self.expires_at is None:
            return False
        return time.time() >= (self.expires_at - buffer_seconds)


class OAuthManager:
    """Manage OAuth tokens with optional refresh support.

    The manager returns refreshed tokens to the caller, which is responsible
    for persistence (e.g., updating a secrets store).
    """

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        scopes: Optional[list[str]] = None,
        *,
        http_client: Optional[ExternalApiClient] = None,
    ) -> None:
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes or []
        self._tokens: Optional[OAuthTokens] = None
        config = HttpClientConfig(timeout=30)
        self.http_client = http_client or ExternalApiClient(config=config)

    def get_access_token(
        self, refresh_token: Optional[str] = None
    ) -> Tuple[str, Optional[OAuthTokens]]:
        """Return an access token, refreshing when needed.

        Returns a tuple of the access token and refreshed tokens (if a refresh
        occurred). The caller should persist refreshed tokens.
        """

        if self._tokens and not self._tokens.is_expired():
            return self._tokens.access_token, None

        if refresh_token or (self._tokens and self._tokens.refresh_token):
            refresh_value = refresh_token or self._tokens.refresh_token  # type: ignore[arg-type]
            return self._refresh_token(refresh_value)

        raise ValueError("No valid token available and no refresh token provided")

    def _refresh_token(self, refresh_token: str) -> Tuple[str, OAuthTokens]:
        """Refresh the access token using the provided refresh token."""

        response = self.http_client.post(
            self.token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": " ".join(self.scopes),
            },
        )
        response.raise_for_status()
        token_payload = self._parse_response(response)

        self._tokens = OAuthTokens(
            access_token=token_payload["access_token"],
            refresh_token=token_payload.get("refresh_token", refresh_token),
            expires_at=time.time() + token_payload.get("expires_in", 3600),
            token_type=token_payload.get("token_type", "Bearer"),
        )

        return self._tokens.access_token, self._tokens

    def _parse_response(self, response: Response) -> Dict[str, Any]:
        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise ValueError("Invalid token response JSON") from exc

    def set_tokens(self, tokens: OAuthTokens) -> None:
        """Set tokens directly (for example, from stored secrets)."""

        self._tokens = tokens

    def get_auth_header(
        self, refresh_token: Optional[str] = None
    ) -> Tuple[Dict[str, str], Optional[OAuthTokens]]:
        """Return an Authorization header and refreshed tokens when applicable."""

        token, new_tokens = self.get_access_token(refresh_token)
        token_type = self._tokens.token_type if self._tokens else "Bearer"
        return {"Authorization": f"{token_type} {token}"}, new_tokens
