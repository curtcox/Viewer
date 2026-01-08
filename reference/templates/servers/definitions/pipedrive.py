# ruff: noqa: F821, F706
"""Interact with Pipedrive CRM to manage deals, persons, and organizations."""

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
_BASE_URL = "https://api.pipedrive.com/v1"

_OPERATIONS = {
    "list_deals": OperationDefinition(),
    "get_deal": OperationDefinition(required=(RequiredField("deal_id"),)),
    "create_deal": OperationDefinition(
        required=(RequiredField("data"),),
        payload_builder=lambda data, **_: data,
    ),
    "update_deal": OperationDefinition(
        required=(RequiredField("deal_id"), RequiredField("data")),
        payload_builder=lambda data, **_: data,
    ),
    "list_persons": OperationDefinition(),
    "get_person": OperationDefinition(required=(RequiredField("person_id"),)),
    "create_person": OperationDefinition(
        required=(RequiredField("data"),),
        payload_builder=lambda data, **_: data,
    ),
    "list_organizations": OperationDefinition(),
    "get_organization": OperationDefinition(required=(RequiredField("organization_id"),)),
    "create_organization": OperationDefinition(
        required=(RequiredField("data"),),
        payload_builder=lambda data, **_: data,
    ),
}

_ENDPOINT_BUILDERS = {
    "list_deals": lambda base_url, **_: f"{base_url}/deals",
    "get_deal": lambda base_url, deal_id, **_: f"{base_url}/deals/{deal_id}",
    "create_deal": lambda base_url, **_: f"{base_url}/deals",
    "update_deal": lambda base_url, deal_id, **_: f"{base_url}/deals/{deal_id}",
    "list_persons": lambda base_url, **_: f"{base_url}/persons",
    "get_person": lambda base_url, person_id, **_: f"{base_url}/persons/{person_id}",
    "create_person": lambda base_url, **_: f"{base_url}/persons",
    "list_organizations": lambda base_url, **_: f"{base_url}/organizations",
    "get_organization": lambda base_url, organization_id, **_: (
        f"{base_url}/organizations/{organization_id}"
    ),
    "create_organization": lambda base_url, **_: f"{base_url}/organizations",
}

_METHODS = {
    "create_deal": "POST",
    "update_deal": "PUT",
    "create_person": "POST",
    "create_organization": "POST",
}


def _build_params(
    operation: str,
    *,
    limit: int,
    api_token: str,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {"api_token": api_token}
    if operation in {"list_deals", "list_persons", "list_organizations"}:
        params["limit"] = limit
    return params


def _build_preview(
    *,
    operation: str,
    url: str,
    method: str,
    payload: Optional[Dict[str, Any]],
    params: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "api_token",
    }

    if params:
        preview["params"] = params
    if payload:
        preview["payload"] = payload

    return preview


def main(
    *,
    operation: str = "list_deals",
    deal_id: Optional[int] = None,
    person_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    data: Optional[Dict[str, Any]] = None,
    limit: int = 100,
    PIPEDRIVE_API_TOKEN: str,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Pipedrive CRM API.

    Args:
        operation: Operation to perform (list_deals, get_deal, create_deal, update_deal,
                   list_persons, get_person, create_person, list_organizations,
                   get_organization, create_organization).
        deal_id: Deal ID (required for get_deal, update_deal).
        person_id: Person ID (required for get_person).
        organization_id: Organization ID (required for get_organization).
        data: Data for creating or updating records.
        limit: Maximum number of results for list operations.
        PIPEDRIVE_API_TOKEN: Pipedrive API token.
        dry_run: When true, return preview without making API call.
        timeout: Request timeout in seconds.
        client: Optional custom HTTP client (for testing).
        context: Request context (optional).

    Returns:
        Dict with 'output' containing the API response or preview.
    """
    api_client = client or _DEFAULT_CLIENT

    if not PIPEDRIVE_API_TOKEN:
        return error_output(
            "Missing PIPEDRIVE_API_TOKEN",
            status_code=401,
            details="Provide a valid API token.",
        )

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        deal_id=deal_id,
        person_id=person_id,
        organization_id=organization_id,
        data=data,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    url = _ENDPOINT_BUILDERS[operation](
        base_url=_BASE_URL,
        deal_id=deal_id,
        person_id=person_id,
        organization_id=organization_id,
    )
    method = _METHODS.get(operation, "GET")
    params = _build_params(operation, limit=limit, api_token=PIPEDRIVE_API_TOKEN)
    payload = result

    if dry_run:
        return {
            "output": _build_preview(
                operation=operation,
                url=url,
                method=method,
                payload=payload,
                params=params,
            )
        }

    headers = {
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
        error_key="error",
        request_error_message="Pipedrive request failed",
    )
