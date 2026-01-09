# ruff: noqa: F821, F706
"""Interact with Google People API (Contacts) to manage contacts."""

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


_SCOPES = ("https://www.googleapis.com/auth/contacts",)
_DEFAULT_CLIENT = ExternalApiClient()
_DEFAULT_AUTH_MANAGER = GoogleAuthManager()


_OPERATIONS = {
    "list_contacts": OperationDefinition(),
    "get_contact": OperationDefinition(
        required=(
            RequiredField(
                "resource_name", "resource_name is required for get_contact operation"
            ),
        ),
    ),
    "create_contact": OperationDefinition(
        required=(
            RequiredField("given_name", "given_name is required for create_contact operation"),
        ),
        payload_builder=lambda given_name, family_name, email, phone, **_: _build_contact_payload(
            given_name=given_name,
            family_name=family_name,
            email=email,
            phone=phone,
        ),
    ),
    "update_contact": OperationDefinition(
        required=(
            RequiredField(
                "resource_name", "resource_name is required for update_contact operation"
            ),
        ),
        payload_builder=lambda given_name, family_name, email, phone, **_: _build_contact_payload(
            given_name=given_name,
            family_name=family_name,
            email=email,
            phone=phone,
        ),
    ),
    "delete_contact": OperationDefinition(
        required=(
            RequiredField(
                "resource_name", "resource_name is required for delete_contact operation"
            ),
        ),
    ),
}

_ENDPOINT_BUILDERS = {
    "list_contacts": lambda base_url, page_size, **_: (
        f"{base_url}/people/me/connections?pageSize={page_size}"
        "&personFields=names,emailAddresses,phoneNumbers"
    ),
    "get_contact": lambda base_url, resource_name, **_: (
        f"{base_url}/{resource_name}?personFields=names,emailAddresses,phoneNumbers"
    ),
    "create_contact": lambda base_url, **_: f"{base_url}/people:createContact",
    "update_contact": lambda base_url, resource_name, **_: (
        f"{base_url}/{resource_name}:updateContact?updatePersonFields=names,emailAddresses,phoneNumbers"
    ),
    "delete_contact": lambda base_url, resource_name, **_: f"{base_url}/{resource_name}:deleteContact",
}

_METHODS = {
    "create_contact": "POST",
    "update_contact": "PATCH",
    "delete_contact": "DELETE",
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


def _build_contact_payload(
    *,
    given_name: Optional[str],
    family_name: Optional[str],
    email: Optional[str],
    phone: Optional[str],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}

    if given_name or family_name:
        payload["names"] = [{}]
        if given_name:
            payload["names"][0]["givenName"] = given_name
        if family_name:
            payload["names"][0]["familyName"] = family_name

    if email:
        payload["emailAddresses"] = [{"value": email}]
    if phone:
        payload["phoneNumbers"] = [{"value": phone}]

    return payload


def main(
    *,
    operation: str = "list_contacts",
    resource_name: Optional[str] = None,
    page_size: int = 10,
    given_name: Optional[str] = None,
    family_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = None,
    GOOGLE_ACCESS_TOKEN: Optional[str] = None,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    auth_manager: Optional[GoogleAuthManager] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Google People API (Contacts).

    Args:
        operation: Operation to perform (list_contacts, get_contact, create_contact, update_contact, delete_contact).
        resource_name: Contact resource name (required for get_contact, update_contact, delete_contact).
        page_size: Maximum number of contacts to return (default: 10).
        given_name: Contact's first name (required for create_contact).
        family_name: Contact's last name.
        email: Contact's email address.
        phone: Contact's phone number.
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
        resource_name=resource_name,
        given_name=given_name,
        family_name=family_name,
        email=email,
        phone=phone,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])
    payload = result

    base_url = "https://people.googleapis.com/v1"
    url = _ENDPOINT_BUILDERS[operation](
        base_url=base_url,
        resource_name=resource_name,
        page_size=page_size,
    )
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
        error_parser=lambda _response, data: (
            data.get("error", {}).get("message", "Google Contacts API error")
            if isinstance(data, dict)
            else "Google Contacts API error"
        ),
        request_error_message="Google Contacts request failed",
        empty_response_statuses=(200, 204) if operation == "delete_contact" else None,
        empty_response_output={"message": "Contact deleted successfully"},
    )
