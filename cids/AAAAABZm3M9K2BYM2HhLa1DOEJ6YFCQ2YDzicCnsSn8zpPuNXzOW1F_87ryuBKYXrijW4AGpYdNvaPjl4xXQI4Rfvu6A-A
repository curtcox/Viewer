# ruff: noqa: F821, F706
"""Interact with Google Docs API to manage documents."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from server_utils.external_api import (
    ExternalApiClient,
    GoogleAuthManager,
    OperationDefinition,
    RequiredField,
    error_output,
    execute_json_request,
    validate_and_build_payload,
    validation_error,
)


_SCOPES = ("https://www.googleapis.com/auth/documents",)
_DEFAULT_CLIENT = ExternalApiClient()
_DEFAULT_AUTH_MANAGER = GoogleAuthManager()


_OPERATIONS = {
    "get_document": OperationDefinition(
        required=(RequiredField("document_id"),),
    ),
    "create_document": OperationDefinition(
        required=(RequiredField("title"),),
        payload_builder=lambda title, **_: {"title": title},
    ),
    "batch_update": OperationDefinition(
        required=(RequiredField("document_id"), RequiredField("requests_payload")),
        payload_builder=lambda requests_payload, **_: {"requests": requests_payload},
    ),
}

_ENDPOINT_BUILDERS = {
    "get_document": lambda document_id, **_: f"{document_id}",
    "create_document": lambda **_: "",
    "batch_update": lambda document_id, **_: f"{document_id}:batchUpdate",
}

_METHODS = {
    "create_document": "POST",
    "batch_update": "POST",
}


def _build_preview(
    *,
    operation: str,
    url: str,
    method: str,
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "google_service_account",
    }

    if payload:
        preview["payload"] = payload

    return preview


def _build_url(base_url: str, endpoint: str) -> str:
    if not endpoint:
        return base_url
    return f"{base_url}/{endpoint}"


def main(
    *,
    operation: str = "get_document",
    document_id: Optional[str] = None,
    title: Optional[str] = None,
    requests_payload: Optional[str] = None,
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = None,
    GOOGLE_ACCESS_TOKEN: Optional[str] = None,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    auth_manager: Optional[GoogleAuthManager] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Google Docs API.

    Args:
        operation: Operation to perform (get_document, create_document, batch_update).
        document_id: Document ID (required for get_document, batch_update).
        title: Document title (required for create_document).
        requests_payload: JSON string with batch update requests (required for batch_update).
        GOOGLE_SERVICE_ACCOUNT_JSON: Google service account JSON string.
        GOOGLE_ACCESS_TOKEN: Google OAuth access token (alternative to service account).
        dry_run: When true, return preview without making API call.
        timeout: Request timeout in seconds.
        client: Optional custom HTTP client (for testing).
        auth_manager: Optional custom auth manager (for testing).
        context: Request context (optional).

    Returns:
        Dict with 'output' containing the API response or preview.
    """
    api_client = client or _DEFAULT_CLIENT
    auth_mgr = auth_manager or _DEFAULT_AUTH_MANAGER

    if not GOOGLE_SERVICE_ACCOUNT_JSON and not GOOGLE_ACCESS_TOKEN:
        return error_output(
            "Missing GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_ACCESS_TOKEN",
            status_code=401,
            details="Provide either a service account JSON or an access token.",
        )

    if operation not in _OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    parsed_requests = None
    if operation == "batch_update" and requests_payload:
        try:
            parsed_requests = json.loads(requests_payload)
        except json.JSONDecodeError:
            return validation_error("requests_payload must be valid JSON")

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        document_id=document_id,
        title=title,
        requests_payload=parsed_requests,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    base_url = "https://docs.googleapis.com/v1/documents"
    endpoint = _ENDPOINT_BUILDERS[operation](document_id=document_id)
    url = _build_url(base_url, endpoint)
    method = _METHODS.get(operation, "GET")
    payload = result if isinstance(result, dict) else None

    if dry_run:
        return {"output": _build_preview(operation=operation, url=url, method=method, payload=payload)}

    # Get access token
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        try:
            service_account_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        except json.JSONDecodeError:
            return error_output(
                "Invalid GOOGLE_SERVICE_ACCOUNT_JSON format",
                status_code=400,
                details="Service account JSON must be valid JSON.",
            )

        token_response = auth_mgr.get_access_token(
            service_account_info=service_account_info,
            scopes=_SCOPES,
        )
        if "error" in token_response.get("output", {}):
            return token_response

        access_token = token_response["access_token"]
    else:
        access_token = GOOGLE_ACCESS_TOKEN

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    return execute_json_request(
        api_client,
        method,
        url,
        headers=headers,
        json=payload,
        timeout=timeout,
        error_key="error",
        request_error_message="Google Docs request failed",
    )
