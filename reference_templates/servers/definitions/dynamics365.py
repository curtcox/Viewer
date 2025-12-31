# ruff: noqa: F821, F706
"""Interact with Microsoft Dynamics 365 API."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import (
    ExternalApiClient,
    MicrosoftAuthManager,
    error_output,
    validation_error,
)


_DEFAULT_CLIENT = ExternalApiClient()
_DEFAULT_AUTH_MANAGER = MicrosoftAuthManager()


_SUPPORTED_OPERATIONS = {
    "list_accounts",
    "get_account",
    "create_account",
    "update_account",
    "list_contacts",
    "get_contact",
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
        "auth": "dynamics365_oauth",
    }

    if payload:
        preview["payload"] = payload

    return preview


def _parse_json_response(response: requests.Response) -> Dict[str, Any]:
    try:
        return response.json()
    except ValueError:
        return error_output(
            "Invalid JSON response",
            status_code=response.status_code,
            details=response.text,
        )


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
    # Validate operation
    if operation not in _SUPPORTED_OPERATIONS:
        return validation_error(
            f"Invalid operation: {operation}. Supported: {', '.join(sorted(_SUPPORTED_OPERATIONS))}"
        )

    # Validate instance URL
    if not instance_url:
        return validation_error("instance_url is required (e.g., 'https://org.crm.dynamics.com')")

    # Validate operation-specific requirements
    if operation in ("get_account", "update_account") and not account_id:
        return validation_error(f"operation={operation} requires account_id")

    if operation == "get_contact" and not contact_id:
        return validation_error("get_contact requires contact_id")

    if operation == "create_account" and not account_name:
        return validation_error("create_account requires account_name")

    if operation in ("create_account", "update_account") and not data:
        return validation_error(f"operation={operation} requires data")

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

    # Build request based on operation
    if operation == "list_accounts":
        url = f"{api_base}/accounts"
        params = {"$top": top}
        method = "GET"
        payload = None
        if dry_run:
            preview = _build_preview(operation=operation, url=url, method=method, payload=params)
            return {"output": preview, "content_type": "application/json"}

    elif operation == "get_account":
        url = f"{api_base}/accounts({account_id})"
        params = {}
        method = "GET"
        payload = None
        if dry_run:
            preview = _build_preview(operation=operation, url=url, method=method, payload=None)
            return {"output": preview, "content_type": "application/json"}

    elif operation == "create_account":
        url = f"{api_base}/accounts"
        try:
            payload = json.loads(data)
            if "name" not in payload:
                payload["name"] = account_name
        except json.JSONDecodeError:
            return validation_error("data must be valid JSON")
        params = {}
        method = "POST"
        if dry_run:
            preview = _build_preview(operation=operation, url=url, method=method, payload=payload)
            return {"output": preview, "content_type": "application/json"}

    elif operation == "update_account":
        url = f"{api_base}/accounts({account_id})"
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            return validation_error("data must be valid JSON")
        params = {}
        method = "PATCH"
        if dry_run:
            preview = _build_preview(operation=operation, url=url, method=method, payload=payload)
            return {"output": preview, "content_type": "application/json"}

    elif operation == "list_contacts":
        url = f"{api_base}/contacts"
        params = {"$top": top}
        method = "GET"
        payload = None
        if dry_run:
            preview = _build_preview(operation=operation, url=url, method=method, payload=params)
            return {"output": preview, "content_type": "application/json"}

    elif operation == "get_contact":
        url = f"{api_base}/contacts({contact_id})"
        params = {}
        method = "GET"
        payload = None
        if dry_run:
            preview = _build_preview(operation=operation, url=url, method=method, payload=None)
            return {"output": preview, "content_type": "application/json"}

    # Execute request
    headers["Content-Type"] = "application/json"
    headers["OData-MaxVersion"] = "4.0"
    headers["OData-Version"] = "4.0"
    headers["Accept"] = "application/json"

    try:
        if method == "GET":
            response = client_instance.get(url, headers=headers, params=params, timeout=timeout)
        elif method == "POST":
            response = client_instance.post(url, headers=headers, json=payload, timeout=timeout)
        elif method == "PATCH":
            response = client_instance.patch(url, headers=headers, json=payload, timeout=timeout)
        else:
            return error_output(f"Unsupported HTTP method: {method}")
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output(
            f"Request failed: {exc}",
            status_code=status,
            details=str(exc),
        )

    if not response.ok:
        error_details = _parse_json_response(response)
        return error_output(
            f"API request failed: {response.status_code}",
            status_code=response.status_code,
            details=error_details,
        )

    # POST may return 204 with no content
    if response.status_code == 204:
        return {"output": {"success": True, "message": "Resource created/updated"}, "content_type": "application/json"}

    result = _parse_json_response(response)
    if "output" in result:
        return result

    return {"output": result, "content_type": "application/json"}
