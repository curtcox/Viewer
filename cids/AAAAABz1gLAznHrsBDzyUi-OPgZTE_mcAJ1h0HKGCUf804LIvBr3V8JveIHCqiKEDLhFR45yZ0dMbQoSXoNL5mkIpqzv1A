# ruff: noqa: F821, F706
"""Interact with Microsoft Dynamics 365 API."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from server_utils.external_api import (
    ExternalApiClient,
    MicrosoftAuthManager,
    OperationDefinition,
    RequiredField,
    error_output,
    execute_json_request,
    validate_and_build_payload,
    validation_error,
)


_DEFAULT_CLIENT = ExternalApiClient()
_DEFAULT_AUTH_MANAGER = MicrosoftAuthManager()


_OPERATIONS = {
    "list_accounts": OperationDefinition(),
    "get_account": OperationDefinition(required=(RequiredField("account_id"),)),
    "create_account": OperationDefinition(
        required=(RequiredField("account_name"), RequiredField("data")),
    ),
    "update_account": OperationDefinition(
        required=(RequiredField("account_id"), RequiredField("data")),
    ),
    "list_contacts": OperationDefinition(),
    "get_contact": OperationDefinition(required=(RequiredField("contact_id"),)),
}

_ENDPOINT_BUILDERS = {
    "list_accounts": lambda **_: "accounts",
    "get_account": lambda account_id, **_: f"accounts({account_id})",
    "create_account": lambda **_: "accounts",
    "update_account": lambda account_id, **_: f"accounts({account_id})",
    "list_contacts": lambda **_: "contacts",
    "get_contact": lambda contact_id, **_: f"contacts({contact_id})",
}

_METHODS = {
    "create_account": "POST",
    "update_account": "PATCH",
}

_PARAMETER_BUILDERS = {
    "list_accounts": lambda top, **_: {"$top": top},
    "list_contacts": lambda top, **_: {"$top": top},
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
        "auth": "dynamics365_oauth",
    }

    if params:
        preview["params"] = params
    if payload:
        preview["payload"] = payload

    return preview


def _build_account_payload(account_name: Optional[str], data: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(data)
    if account_name and "name" not in payload:
        payload["name"] = account_name
    return payload


def main(
    *,
    operation: str = "list_accounts",
    instance_url: Optional[str] = None,
    account_id: Optional[str] = None,
    contact_id: Optional[str] = None,
    account_name: Optional[str] = None,
    data: Optional[str] = None,
    top: int = 10,
    DYNAMICS365_ACCESS_TOKEN: Optional[str] = None,
    DYNAMICS365_TENANT_ID: Optional[str] = None,
    DYNAMICS365_CLIENT_ID: Optional[str] = None,
    DYNAMICS365_CLIENT_SECRET: Optional[str] = None,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    auth_manager: Optional[MicrosoftAuthManager] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Dynamics 365 API.

    Args:
        operation: Operation to perform (list_accounts, get_account, create_account, update_account, list_contacts, get_contact).
        instance_url: Dynamics 365 instance URL (e.g., 'https://org.crm.dynamics.com').
        account_id: Account ID (required for get_account, update_account).
        contact_id: Contact ID (required for get_contact).
        account_name: Account name for create_account.
        data: JSON data for create/update operations.
        top: Maximum number of items to return (default: 10).
        DYNAMICS365_ACCESS_TOKEN: Dynamics 365 OAuth access token.
        DYNAMICS365_TENANT_ID: Microsoft tenant ID (for client credentials flow).
        DYNAMICS365_CLIENT_ID: Microsoft client ID (for client credentials flow).
        DYNAMICS365_CLIENT_SECRET: Microsoft client secret (for client credentials flow).
        dry_run: When true, return preview without making API call.
        timeout: Request timeout in seconds.
        client: Optional ExternalApiClient for testing.
        auth_manager: Optional MicrosoftAuthManager for testing.
        context: Request context (optional).

    Returns:
        Dict with 'output' containing the API response or error.
    """
    if operation not in _OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    # Validate instance URL
    if not instance_url:
        return validation_error("instance_url is required (e.g., 'https://org.crm.dynamics.com')")

    parsed_data = None
    if operation in ("create_account", "update_account") and data:
        try:
            parsed_data = json.loads(data)
        except json.JSONDecodeError:
            return validation_error("data must be valid JSON")

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        account_id=account_id,
        contact_id=contact_id,
        account_name=account_name,
        data=parsed_data,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    # Get authentication
    auth_manager_instance = auth_manager or _DEFAULT_AUTH_MANAGER
    client_instance = client or _DEFAULT_CLIENT

    # Determine auth method
    if DYNAMICS365_ACCESS_TOKEN:
        headers = {"Authorization": f"Bearer {DYNAMICS365_ACCESS_TOKEN}"}
    elif DYNAMICS365_TENANT_ID and DYNAMICS365_CLIENT_ID and DYNAMICS365_CLIENT_SECRET:
        # For Dynamics 365, use the instance URL as the resource
        auth_result = auth_manager_instance.get_authorization(
            tenant_id=DYNAMICS365_TENANT_ID,
            client_id=DYNAMICS365_CLIENT_ID,
            client_secret=DYNAMICS365_CLIENT_SECRET,
            scopes=[f"{instance_url}/.default"],
        )
        if "output" in auth_result:
            return auth_result
        headers = auth_result["headers"]
    else:
        return error_output(
            "Authentication required",
            details="Provide DYNAMICS365_ACCESS_TOKEN or all of DYNAMICS365_TENANT_ID, DYNAMICS365_CLIENT_ID, DYNAMICS365_CLIENT_SECRET",
        )

    api_base = f"{instance_url}/api/data/v9.2"
    endpoint = _ENDPOINT_BUILDERS[operation](
        account_id=account_id,
        contact_id=contact_id,
    )
    url = f"{api_base}/{endpoint}"
    method = _METHODS.get(operation, "GET")
    params = _PARAMETER_BUILDERS.get(operation, lambda **_: None)(top=top)
    payload = None
    if operation == "create_account" and parsed_data:
        payload = _build_account_payload(account_name, parsed_data)
    elif operation == "update_account" and parsed_data:
        payload = parsed_data

    if dry_run:
        preview = _build_preview(
            operation=operation,
            url=url,
            method=method,
            params=params,
            payload=payload,
        )
        return {"output": preview, "content_type": "application/json"}

    # Execute request
    headers["Content-Type"] = "application/json"
    headers["OData-MaxVersion"] = "4.0"
    headers["OData-Version"] = "4.0"
    headers["Accept"] = "application/json"

    return execute_json_request(
        client_instance,
        method,
        url,
        headers=headers,
        params=params,
        json=payload,
        timeout=timeout,
        request_error_message="Dynamics 365 request failed",
        empty_response_statuses=(204,),
        empty_response_output={"success": True, "message": "Resource created/updated"},
    )
