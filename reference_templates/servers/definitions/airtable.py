"""Interact with Airtable tables using the REST API."""

import json
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output


_DEFAULT_CLIENT = ExternalApiClient()


SUPPORTED_OPERATIONS = {"list", "retrieve", "create"}


def _parse_record(record: str) -> Optional[Dict[str, Any]]:
    if not record:
        return None
    try:
        return json.loads(record)
    except json.JSONDecodeError:
        return None


def main(
    base_id: str,
    table_name: str,
    *,
    AIRTABLE_API_KEY: str,
    operation: str = "list",
    record_id: str = "",
    record: str = "",
    max_records: int = 5,
    dry_run: bool = True,
    timeout: int = 60,
    context=None,
    client: Optional[ExternalApiClient] = None,
) -> Dict[str, Any]:
    """Perform basic Airtable operations.

    Args:
        base_id: Airtable base ID.
        table_name: Target table name.
        AIRTABLE_API_KEY: API key with access to the base.
        operation: One of "list", "retrieve", or "create".
        record_id: Record ID for retrieve operations.
        record: JSON string of field values for create operations.
        max_records: Maximum records to fetch when listing.
        dry_run: When true, do not call Airtable and instead return the planned request.
        timeout: Request timeout in seconds.
    """
    api_client = client or _DEFAULT_CLIENT

    if not AIRTABLE_API_KEY:
        return error_output(
            "Missing AIRTABLE_API_KEY",
            status_code=401,
            details="Provide a personal access token with base access.",
        )
    if not base_id:
        return error_output("Missing base_id", status_code=400)
    if not table_name:
        return error_output("Missing table_name", status_code=400)

    op = operation.lower()
    if op not in SUPPORTED_OPERATIONS:
        return error_output(f"Unsupported operation: {operation}", status_code=400)

    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json",
    }
    base_url = f"https://api.airtable.com/v0/{base_id}/{table_name}"

    request_details: Dict[str, Any] = {
        "operation": op,
        "url": base_url if op != "retrieve" else f"{base_url}/{record_id}",
        "headers": {"Authorization": "Bearer ****", "Content-Type": "application/json"},
    }

    if op == "create":
        parsed_record = _parse_record(record)
        if parsed_record is None:
            return error_output(
                "Invalid record JSON for create operation",
                status_code=400,
                details="Provide JSON object string like {\"Name\": \"Alice\"}",
            )
        request_details["body"] = {"fields": parsed_record}
    elif op == "list":
        request_details["params"] = {"maxRecords": max_records}
    elif op == "retrieve":
        if not record_id:
            return error_output(
                "record_id required for retrieve operation",
                status_code=400,
                details="Pass the Airtable record ID (rec...) when retrieving a single row.",
            )

    if dry_run:
        return {"output": {"preview": request_details, "message": "Dry run - no API call made"}}

    try:
        if op == "create":
            response = api_client.post(
                base_url,
                headers=headers,
                json={"fields": parsed_record},
                timeout=timeout,
            )
        elif op == "retrieve":
            response = api_client.get(
                f"{base_url}/{record_id}", headers=headers, timeout=timeout
            )
        else:
            response = api_client.get(
                base_url,
                headers=headers,
                params={"maxRecords": max_records},
                timeout=timeout,
            )
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output(
            "Airtable request failed", status_code=status, details=str(exc)
        )

    try:
        data = response.json()
    except ValueError:
        return error_output(
            "Invalid JSON response",
            status_code=response.status_code,
            details=response.text,
        )

    if response.status_code >= 400:
        return error_output(
            data.get("error", "Airtable API call failed"),
            status_code=response.status_code,
            response=data,
        )

    return {"output": data}
