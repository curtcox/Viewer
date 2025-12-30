# ruff: noqa: F821, F706
"""Interact with Google Sheets to read or append values."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

import requests

from server_utils.external_api import (
    ExternalApiClient,
    GoogleAuthManager,
    error_output,
    validation_error,
)


_SCOPES = ("https://www.googleapis.com/auth/spreadsheets",)
_DEFAULT_CLIENT = ExternalApiClient()
_DEFAULT_AUTH_MANAGER = GoogleAuthManager()


def _parse_values(values: Any) -> Dict[str, Any] | List[List[Any]]:
    if values is None:
        return validation_error("Missing required values for append", field="values")

    parsed = values
    if isinstance(values, str):
        try:
            parsed = json.loads(values)
        except json.JSONDecodeError:
            return validation_error("Values must be valid JSON", field="values")

    if not isinstance(parsed, Iterable) or isinstance(parsed, (str, bytes)):
        return validation_error("Values must be a list of rows", field="values")

    rows: List[List[Any]] = []
    for row in parsed:
        if not isinstance(row, Iterable) or isinstance(row, (str, bytes)):
            return validation_error("Each row must be a list of values", field="values")
        rows.append(list(row))

    if not rows:
        return validation_error("Values must include at least one row", field="values")

    return rows


def _build_preview(
    *,
    spreadsheet_id: str,
    range_name: str,
    operation: str,
    values: Optional[List[List[Any]]],
    value_input_option: str,
    credential_source: str,
) -> Dict[str, Any]:
    base_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}"
    if operation == "append":
        url = f"{base_url}:append"
        method = "POST"
        payload: Optional[Dict[str, Any]] = {"values": values} if values is not None else None
        params = {"valueInputOption": value_input_option}
    else:
        url = base_url
        method = "GET"
        payload = None
        params = None

    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": credential_source,
    }
    if params:
        preview["params"] = params
    if payload:
        preview["payload"] = payload
    return preview


def _build_auth_headers(
    *,
    access_token: str,
    service_account_json: str,
    auth_manager: GoogleAuthManager,
    scopes: Iterable[str],
    subject: Optional[str],
) -> Dict[str, Any]:
    if access_token:
        return {"headers": {"Authorization": f"Bearer {access_token}"}}

    if not service_account_json:
        return error_output(
            "Missing Google credentials",
            status_code=401,
            details="Provide GOOGLE_ACCESS_TOKEN or GOOGLE_SERVICE_ACCOUNT_JSON",
        )

    try:
        service_account_info = json.loads(service_account_json)
    except json.JSONDecodeError:
        return validation_error("Invalid GOOGLE_SERVICE_ACCOUNT_JSON", field="GOOGLE_SERVICE_ACCOUNT_JSON")

    auth_result = auth_manager.get_authorization(
        service_account_info,
        scopes,
        subject=subject,
    )
    return auth_result


def main(
    spreadsheet_id: str,
    range_name: str,
    *,
    operation: str = "read",
    values: Any = None,
    value_input_option: str = "RAW",
    access_token: str = "",
    service_account_json: str = "",
    subject: Optional[str] = None,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    auth_manager: Optional[GoogleAuthManager] = None,
    context=None,
) -> Dict[str, Any]:
    """Read or append values in a Google Sheet."""

    if not spreadsheet_id:
        return validation_error("Missing required spreadsheet_id", field="spreadsheet_id")
    if not range_name:
        return validation_error("Missing required range_name", field="range_name")

    normalized_operation = operation.lower()
    if normalized_operation not in {"read", "append"}:
        return validation_error("Unsupported operation", field="operation")

    parsed_values: Optional[List[List[Any]]] = None
    if normalized_operation == "append":
        parsed_values_result = _parse_values(values)
        if isinstance(parsed_values_result, dict) and "output" in parsed_values_result:
            return parsed_values_result
        parsed_values = parsed_values_result  # type: ignore[assignment]

    credential_source = "access_token" if access_token else "service_account"
    api_client = client or _DEFAULT_CLIENT
    auth_helper = auth_manager or _DEFAULT_AUTH_MANAGER

    if dry_run:
        preview = _build_preview(
            spreadsheet_id=spreadsheet_id,
            range_name=range_name,
            operation=normalized_operation,
            values=parsed_values,
            value_input_option=value_input_option,
            credential_source=credential_source,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    auth_result = _build_auth_headers(
        access_token=access_token,
        service_account_json=service_account_json,
        auth_manager=auth_helper,
        scopes=_SCOPES,
        subject=subject,
    )
    if "output" in auth_result:
        return auth_result

    headers = auth_result.get("headers", {})

    base_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}"
    try:
        if normalized_operation == "append":
            response = api_client.post(
                f"{base_url}:append",
                headers=headers,
                params={"valueInputOption": value_input_option},
                json={"values": parsed_values},
                timeout=timeout,
            )
        else:
            response = api_client.get(
                base_url,
                headers=headers,
                timeout=timeout,
            )
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("Google Sheets request failed", status_code=status, details=str(exc))

    try:
        payload = response.json()
    except ValueError:
        return error_output(
            "Invalid JSON response",
            status_code=getattr(response, "status_code", None),
            details=getattr(response, "text", None),
        )

    if not getattr(response, "ok", False):
        return error_output(
            payload.get("error", "Google Sheets API error"),
            status_code=response.status_code,
            response=payload,
        )

    return {"output": payload}
