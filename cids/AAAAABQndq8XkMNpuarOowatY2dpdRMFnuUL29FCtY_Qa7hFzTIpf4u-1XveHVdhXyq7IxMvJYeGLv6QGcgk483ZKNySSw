# ruff: noqa: F821, F706
"""Execute BigQuery queries using Google Cloud BigQuery API."""

from __future__ import annotations

from typing import Any, Dict, Optional
import json

from server_utils.external_api import ExternalApiClient, GoogleAuthManager, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()
_DEFAULT_AUTH_MANAGER = GoogleAuthManager()
_SCOPES = ["https://www.googleapis.com/auth/bigquery"]


def _build_preview(
    *,
    operation: str,
    query: Optional[str],
    project_id: str,
) -> Dict[str, Any]:
    """Build a preview of the BigQuery operation."""
    preview: Dict[str, Any] = {
        "operation": operation,
        "url": f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/queries",
        "method": "POST",
        "auth": "Google Service Account",
        "project_id": project_id,
    }
    if query:
        preview["query"] = query
    return preview


def main(
    *,
    operation: str = "query",
    query: str = "",
    project_id: str = "",
    dataset_id: str = "",
    table_id: str = "",
    max_results: int = 1000,
    GOOGLE_SERVICE_ACCOUNT_JSON: str = "",
    GOOGLE_ACCESS_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    auth_manager: Optional[GoogleAuthManager] = None,
    context=None,
) -> Dict[str, Any]:
    """Execute BigQuery queries using Google Cloud BigQuery API.

    Operations:
    - query: Execute a SQL query
    - list_datasets: List datasets in project
    - list_tables: List tables in dataset
    """

    normalized_operation = operation.lower()
    valid_operations = {"query", "list_datasets", "list_tables"}

    if normalized_operation not in valid_operations:
        return validation_error("Unsupported operation", field="operation")

    # Validate credentials
    if not GOOGLE_SERVICE_ACCOUNT_JSON and not GOOGLE_ACCESS_TOKEN:
        return error_output(
            "Missing GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_ACCESS_TOKEN",
            status_code=401,
        )

    # Validate project_id
    if not project_id:
        return validation_error("Missing required project_id", field="project_id")

    # Validate operation-specific requirements
    if normalized_operation == "query" and not query:
        return validation_error("Missing required query", field="query")

    if normalized_operation == "list_tables" and not dataset_id:
        return validation_error("Missing required dataset_id", field="dataset_id")

    # Return preview if in dry-run mode
    if dry_run:
        return {
            "output": _build_preview(
                operation=normalized_operation,
                query=query if query else None,
                project_id=project_id,
            )
        }

    # Execute actual API call
    api_client = client or _DEFAULT_CLIENT
    google_auth_manager = auth_manager or _DEFAULT_AUTH_MANAGER

    try:
        # Get auth headers
        if GOOGLE_ACCESS_TOKEN:
            headers = {"Authorization": f"Bearer {GOOGLE_ACCESS_TOKEN}"}
        elif GOOGLE_SERVICE_ACCOUNT_JSON:
            try:
                service_account_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
            except json.JSONDecodeError:
                return validation_error("Invalid GOOGLE_SERVICE_ACCOUNT_JSON", field="GOOGLE_SERVICE_ACCOUNT_JSON")

            auth_result = google_auth_manager.get_authorization(
                service_account_info,
                _SCOPES,
            )
            if "output" in auth_result:
                return auth_result
            headers = auth_result["headers"]
        else:
            return error_output(
                "Missing Google credentials",
                status_code=401,
            )

        response = None

        # Build request based on operation
        if normalized_operation == "query":
            url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/queries"
            payload = {
                "query": query,
                "useLegacySql": False,
                "maxResults": max_results,
            }
            response = api_client.post(url=url, headers=headers, json=payload, timeout=timeout)

        elif normalized_operation == "list_datasets":
            url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets"
            response = api_client.get(url=url, headers=headers, timeout=timeout)

        elif normalized_operation == "list_tables":
            url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{dataset_id}/tables"
            response = api_client.get(url=url, headers=headers, timeout=timeout)

        if response is None:
            return validation_error("Unsupported operation", field="operation")

        if not response.ok:
            return error_output(
                f"BigQuery API error: {response.text}",
                status_code=response.status_code,
                response=response.text,
            )

        return {"output": response.json()}

    except Exception as e:
        return error_output(str(e), status_code=500)
