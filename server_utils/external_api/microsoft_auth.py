"""Microsoft authentication helpers for Graph and other AAD-backed APIs."""

from typing import Any, Dict, Optional, Sequence

import requests

from .error_response import api_error, error_output, validation_error
from .http_client import ExternalApiClient, HttpClientConfig


class MicrosoftAuthManager:
    """Helper to exchange client credentials for Microsoft access tokens."""

    def __init__(self, *, http_client: Optional[ExternalApiClient] = None) -> None:
        config = HttpClientConfig(timeout=30)
        self.http_client = http_client or ExternalApiClient(config=config)

    def get_access_token(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        scopes: Sequence[str],
    ) -> Dict[str, Any]:
        """Return an access token using the client credentials flow."""

        if not tenant_id:
            return validation_error("Missing required tenant_id", field="tenant_id")
        if not client_id:
            return validation_error("Missing required client_id", field="client_id")
        if not client_secret:
            return validation_error("Missing required client_secret", field="client_secret")
        if not scopes:
            return validation_error("Missing required scopes", field="scopes")

        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        try:
            response = self.http_client.post(
                token_url,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "client_credentials",
                    "scope": " ".join(scopes),
                },
            )
        except requests.RequestException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            return error_output(
                "Microsoft token request failed", status_code=status, details=str(exc)
            )

        if not response.ok:
            return api_error(
                "Failed to obtain Microsoft access token",
                status_code=response.status_code,
                response_body=getattr(response, "text", None),
            )

        try:
            payload = response.json()
        except ValueError:
            return error_output(
                "Invalid JSON response from Microsoft token endpoint",
                status_code=response.status_code,
                response=getattr(response, "text", None),
            )

        access_token = payload.get("access_token")
        if not access_token:
            return error_output(
                "Token response missing access_token",
                status_code=response.status_code,
                response=payload,
            )

        return {
            "access_token": access_token,
            "token_type": payload.get("token_type", "Bearer"),
            "expires_in": payload.get("expires_in"),
            "raw_response": payload,
        }

    def get_authorization(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        scopes: Sequence[str],
    ) -> Dict[str, Any]:
        """Return Authorization headers for client credential tokens."""

        token_result = self.get_access_token(tenant_id, client_id, client_secret, scopes)
        if "output" in token_result:
            return token_result

        token_type = token_result.get("token_type", "Bearer")
        return {
            "headers": {"Authorization": f"{token_type} {token_result['access_token']}"},
            "token": token_result,
        }
