# ruff: noqa: F821, F706
"""Interact with HubSpot CRM to manage contacts and companies."""

from __future__ import annotations

from typing import Any, Dict, Optional

from server_utils.external_api import (
    ExternalApiClient,
    OperationDefinition,
    RequiredField,
    error_output,
    execute_json_request,
    validate_and_build_payload,
    validation_error,
)


_DEFAULT_CLIENT = ExternalApiClient()


_OPERATIONS = {
    "list_contacts": OperationDefinition(),
    "get_contact": OperationDefinition(required=(RequiredField("contact_id"),)),
    "create_contact": OperationDefinition(
        required=(RequiredField("properties"),),
        payload_builder=lambda properties, **_: {"properties": properties},
    ),
    "list_companies": OperationDefinition(),
    "get_company": OperationDefinition(required=(RequiredField("company_id"),)),
    "create_company": OperationDefinition(
        required=(RequiredField("properties"),),
        payload_builder=lambda properties, **_: {"properties": properties},
    ),
}

_ENDPOINT_BUILDERS = {
    "list_contacts": lambda **_: "crm/v3/objects/contacts",
    "get_contact": lambda contact_id, **_: f"crm/v3/objects/contacts/{contact_id}",
    "create_contact": lambda **_: "crm/v3/objects/contacts",
    "list_companies": lambda **_: "crm/v3/objects/companies",
    "get_company": lambda company_id, **_: f"crm/v3/objects/companies/{company_id}",
    "create_company": lambda **_: "crm/v3/objects/companies",
}

_METHODS = {
    "create_contact": "POST",
    "create_company": "POST",
}

_PARAMETER_BUILDERS = {
    "list_contacts": lambda limit, **_: {"limit": limit},
    "list_companies": lambda limit, **_: {"limit": limit},
}


def _build_preview(
    *,
    operation: str,
    url: str,
    method: str,
    params: Optional[Dict[str, Any]],
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "bearer",
    }

    if params:
        preview["params"] = params
    if payload:
        preview["payload"] = payload

    return preview

def _hubspot_error_message(_response: object, data: Any) -> str:
    if isinstance(data, dict):
        return data.get("message", "HubSpot API error")
    return "HubSpot API error"


def main(
    *,
    operation: str = "list_contacts",
    contact_id: Optional[str] = None,
    company_id: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None,
    limit: int = 100,
    HUBSPOT_ACCESS_TOKEN: str,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with HubSpot CRM API.

    Args:
        operation: Operation to perform (list_contacts, get_contact, create_contact,
                   list_companies, get_company, create_company).
        contact_id: Contact ID (required for get_contact).
        company_id: Company ID (required for get_company).
        properties: Properties dict for creating contacts/companies.
        limit: Maximum number of results for list operations.
        HUBSPOT_ACCESS_TOKEN: HubSpot OAuth access token.
        dry_run: When true, return preview without making API call.
        timeout: Request timeout in seconds.
        client: Optional custom HTTP client (for testing).
        context: Request context (optional).

    Returns:
        Dict with 'output' containing the API response or preview.
    """
    api_client = client or _DEFAULT_CLIENT

    if not HUBSPOT_ACCESS_TOKEN:
        return error_output(
            "Missing HUBSPOT_ACCESS_TOKEN",
            status_code=401,
            details="Provide a valid OAuth access token.",
        )

    if operation not in _OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        contact_id=contact_id,
        company_id=company_id,
        properties=properties,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    base_url = "https://api.hubapi.com"
    endpoint = _ENDPOINT_BUILDERS[operation](
        contact_id=contact_id,
        company_id=company_id,
    )
    url = f"{base_url}/{endpoint}"
    method = _METHODS.get(operation, "GET")
    payload = result if isinstance(result, dict) else None
    params = _PARAMETER_BUILDERS.get(operation, lambda **_: None)(limit=limit)

    if dry_run:
        return {
            "output": _build_preview(
                operation=operation,
                url=url,
                method=method,
                params=params,
                payload=payload,
            )
        }

    headers = {
        "Authorization": f"Bearer {HUBSPOT_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    return execute_json_request(
        api_client,
        method,
        url,
        headers=headers,
        params=params,
        json=payload,
        timeout=timeout,
        request_error_message="HubSpot request failed",
        error_parser=_hubspot_error_message,
    )
