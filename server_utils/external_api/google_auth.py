"""Google authentication helpers for service accounts and OAuth tokens."""

import time
from typing import Any, Dict, Mapping, Optional, Sequence

import jwt
import requests

from .error_response import api_error, error_output, validation_error
from .http_client import ExternalApiClient, HttpClientConfig


GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"


class GoogleAuthManager:
    """Helper to exchange service account assertions for access tokens."""

    def __init__(self, *, http_client: Optional[ExternalApiClient] = None) -> None:
        config = HttpClientConfig(timeout=30)
        self.http_client = http_client or ExternalApiClient(config=config)

    def get_access_token(
        self,
        service_account_info: Mapping[str, Any],
        scopes: Sequence[str],
        *,
        subject: Optional[str] = None,
        token_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return an access token for the provided service account."""

        validation_error_response = self._validate_service_account(service_account_info)
        if validation_error_response:
            return validation_error_response

        if not scopes:
            return validation_error("Missing required scopes", field="scopes")

        if subject is not None and not subject:
            return validation_error("Missing required subject", field="subject")

        token_uri = token_uri or service_account_info.get("token_uri", GOOGLE_TOKEN_URI)
        assertion_result = self._build_jwt_assertion(
            service_account_info, scopes, token_uri, subject=subject
        )
        if "output" in assertion_result:
            return assertion_result
        assertion = assertion_result["assertion"]

        try:
            response = self.http_client.post(
                token_uri,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": assertion,
                },
            )
        except requests.RequestException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            return error_output(
                "Google token request failed", status_code=status, details=str(exc)
            )

        if not response.ok:
            return api_error(
                "Failed to obtain Google access token",
                status_code=response.status_code,
                response_body=getattr(response, "text", None),
            )

        try:
            payload = response.json()
        except ValueError:
            return error_output(
                "Invalid JSON response from Google token endpoint",
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
        service_account_info: Mapping[str, Any],
        scopes: Sequence[str],
        *,
        subject: Optional[str] = None,
        token_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return Authorization headers for the provided service account."""

        token_result = self.get_access_token(
            service_account_info, scopes, subject=subject, token_uri=token_uri
        )
        if "output" in token_result:
            return token_result

        token_type = token_result.get("token_type", "Bearer")
        return {
            "headers": {"Authorization": f"{token_type} {token_result['access_token']}"},
            "token": token_result,
        }

    def refresh_oauth_token(
        self,
        *,
        refresh_token: str,
        client_id: str,
        client_secret: str,
        scopes: Sequence[str],
    ) -> Dict[str, Any]:
        """Exchange a refresh token for a new Google OAuth access token."""

        if not refresh_token:
            return validation_error("Missing required refresh_token", field="refresh_token")
        if not client_id:
            return validation_error("Missing required client_id", field="client_id")
        if not client_secret:
            return validation_error("Missing required client_secret", field="client_secret")
        if not scopes:
            return validation_error("Missing required scopes", field="scopes")

        try:
            response = self.http_client.post(
                GOOGLE_TOKEN_URI,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": " ".join(scopes),
                },
            )
        except requests.RequestException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            return error_output(
                "Google OAuth token request failed",
                status_code=status,
                details=str(exc),
            )

        if not response.ok:
            return api_error(
                "Failed to refresh Google access token",
                status_code=response.status_code,
                response_body=getattr(response, "text", None),
            )

        try:
            payload = response.json()
        except ValueError:
            return error_output(
                "Invalid JSON response from Google OAuth token endpoint",
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
            "refresh_token": payload.get("refresh_token"),
            "raw_response": payload,
        }

    def get_oauth_authorization(
        self,
        *,
        refresh_token: str,
        client_id: str,
        client_secret: str,
        scopes: Sequence[str],
    ) -> Dict[str, Any]:
        """Return Authorization headers for OAuth refresh tokens."""

        token_result = self.refresh_oauth_token(
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
        )
        if "output" in token_result:
            return token_result

        token_type = token_result.get("token_type", "Bearer")
        return {
            "headers": {"Authorization": f"{token_type} {token_result['access_token']}"},
            "token": token_result,
        }

    def _validate_service_account(self, info: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
        required_fields = ["client_email", "private_key"]
        for field in required_fields:
            if not info.get(field):
                return validation_error(
                    f"Missing required service account field: {field}",
                    field=field,
                )
        return None

    def _build_jwt_assertion(
        self,
        info: Mapping[str, Any],
        scopes: Sequence[str],
        token_uri: str,
        *,
        subject: Optional[str] = None,
    ) -> Dict[str, str] | Dict[str, Any]:
        issued_at = int(time.time())
        claims = {
            "iss": info["client_email"],
            "scope": " ".join(scopes),
            "aud": token_uri,
            "iat": issued_at,
            "exp": issued_at + 3600,
        }

        if subject:
            claims["sub"] = subject

        algorithm = info.get("algorithm", "RS256")
        try:
            assertion = jwt.encode(claims, info["private_key"], algorithm=algorithm)
        except Exception as exc:  # pragma: no cover - PyJWT handles most validation
            return error_output(
                "Failed to sign service account assertion",
                details={"error": str(exc)},
            )

        return {"assertion": assertion}
