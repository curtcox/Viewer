# ruff: noqa: F821, F706
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "list_sheets",
    "get_sheet",
    "list_rows",
    "get_row",
    "add_rows",
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


def _parse_json_response(response: requests.Response) -> Dict[str, Any]:
    try:
        return response.json()
    except ValueError:
        return error_output(
            "Invalid JSON response",
            status_code=response.status_code,
            details=response.text,
        )


def _handle_response(response: requests.Response) -> Dict[str, Any]:
    data = _parse_json_response(response)
    if "output" in data:
        return data

    if not response.ok:
        message = "Smartsheet API error"
        if isinstance(data, dict):
            error_data = data.get("message") or data.get("error")
            if error_data:
                message = error_data if isinstance(error_data, str) else str(error_data)
        return error_output(message, status_code=response.status_code, details=data)

    return {"output": data}


def main(
    *,
    operation: str = "list_sheets",
    sheet_id: str = "",
    row_id: str = "",
    rows_data: str = "",
    SMARTSHEET_ACCESS_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Smartsheet sheets and rows."""

    normalized_operation = operation.lower()

    if normalized_operation not in _SUPPORTED_OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    if not SMARTSHEET_ACCESS_TOKEN:
        return error_output(
            "Missing SMARTSHEET_ACCESS_TOKEN",
            status_code=401,
            details="Provide an access token to authenticate Smartsheet API calls.",
        )

    if normalized_operation in ("get_sheet", "list_rows", "add_rows") and not sheet_id:
        return validation_error("Missing required sheet_id", field="sheet_id")

    if normalized_operation == "get_row" and not row_id:
        return validation_error("Missing required row_id", field="row_id")

    if normalized_operation == "add_rows" and not rows_data:
        return validation_error("Missing required rows_data", field="rows_data")

    base_url = "https://api.smartsheet.com/2.0"
    url = f"{base_url}/sheets"
    method = "GET"
    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "list_sheets":
        url = f"{base_url}/sheets"
    elif normalized_operation == "get_sheet":
        url = f"{base_url}/sheets/{sheet_id}"
    elif normalized_operation == "list_rows":
        url = f"{base_url}/sheets/{sheet_id}"
    elif normalized_operation == "get_row":
        url = f"{base_url}/sheets/{sheet_id}/rows/{row_id}"
    elif normalized_operation == "add_rows":
        url = f"{base_url}/sheets/{sheet_id}/rows"
        method = "POST"
        try:
            import json
            payload = json.loads(rows_data)
        except (json.JSONDecodeError, ImportError):
            return validation_error("Invalid rows_data JSON format", field="rows_data")

    if dry_run:
        preview = _build_preview(
            operation=normalized_operation,
            url=url,
            method=method,
            params=params,
            payload=payload,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    headers = {
        "Authorization": f"Bearer {SMARTSHEET_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    api_client = client or _DEFAULT_CLIENT

    try:
        if method == "POST":
            response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
        else:
            response = api_client.get(url, headers=headers, params=params, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("Smartsheet request failed", status_code=status, details=str(exc))

    return _handle_response(response)
