# ruff: noqa: F821, F706
"""Interact with Google Forms API to manage forms and responses."""

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


_SCOPES = ("https://www.googleapis.com/auth/forms",)
_DEFAULT_CLIENT = ExternalApiClient()
_DEFAULT_AUTH_MANAGER = GoogleAuthManager()


_OPERATIONS = {
    "get_form": OperationDefinition(
        required=(RequiredField("form_id", "form_id is required for get_form operation"),),
    ),
    "create_form": OperationDefinition(
        required=(RequiredField("title", "title is required for create_form operation"),),
        payload_builder=lambda title, document_title, **_: {
            "info": {
                "title": title,
                **({"documentTitle": document_title} if document_title else {}),
            }
        },
    ),
    "list_responses": OperationDefinition(
        required=(
            RequiredField("form_id", "form_id is required for list_responses operation"),
        ),
    ),
    "get_response": OperationDefinition(
        required=(RequiredField("form_id", "form_id is required for get_response operation"),),
    ),
}

_ENDPOINT_BUILDERS = {
    "get_form": lambda base_url, form_id, **_: f"{base_url}/{form_id}",
    "create_form": lambda base_url, **_: base_url,
    "list_responses": lambda base_url, form_id, **_: f"{base_url}/{form_id}/responses",
    "get_response": lambda base_url, form_id, **_: f"{base_url}/{form_id}/responses",
}

_METHODS = {
    "create_form": "POST",
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


def _google_forms_error_message(_response: object, data: object) -> str:
    if isinstance(data, dict):
        error = data.get("error", {})
        if isinstance(error, dict):
            return error.get("message", "Google Forms API error")
    return "Google Forms API error"


def main(
    *,
    operation: str = "get_form",
    form_id: Optional[str] = None,
    title: Optional[str] = None,
    document_title: Optional[str] = None,
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = None,
    GOOGLE_ACCESS_TOKEN: Optional[str] = None,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    auth_manager: Optional[GoogleAuthManager] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Google Forms API.

    Args:
        operation: Operation to perform (get_form, create_form, list_responses, get_response).
        form_id: Form ID (required for get_form, list_responses, get_response).
        title: Form title (required for create_form).
        document_title: Document title for the form (optional for create_form).
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
        return validation_error(
            f"Invalid operation: {operation}. Valid operations: {', '.join(_OPERATIONS)}"
        )

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        form_id=form_id,
        title=title,
        document_title=document_title,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])
    payload = result

    base_url = "https://forms.googleapis.com/v1/forms"
    url = _ENDPOINT_BUILDERS[operation](base_url=base_url, form_id=form_id)
    method = _METHODS.get(operation, "GET")

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
        error_parser=_google_forms_error_message,
        request_error_message="Google Forms request failed",
    )
