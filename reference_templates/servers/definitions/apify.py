# ruff: noqa: F821, F706
"""Call the Apify API for web scraping and automation."""

from typing import Optional
from server_utils.external_api import (
    ExternalApiClient,
    HttpClientConfig,
    error_response,
    missing_secret_error,
    validation_error,
    generate_form,
    FormField,
)
import json
import requests


API_BASE_URL = "https://api.apify.com/v2"
DOCUMENTATION_URL = "https://docs.apify.com/api/v2"


def main(
    operation: str = "",
    actor_id: str = "",
    run_id: str = "",
    dataset_id: str = "",
    input_data: str = "",
    format: str = "json",
    timeout: int = 60,
    dry_run: bool = True,
    *,
    APIFY_API_TOKEN: str,
    context=None,
    client: Optional[ExternalApiClient] = None,
):
    """
    Make a request to the Apify API.

    Args:
        operation: Operation to perform (list_actors, run_actor, get_run,
                   list_runs, get_dataset, download_dataset, delete_dataset)
        actor_id: Actor ID for actor operations
        run_id: Run ID for run-specific operations
        dataset_id: Dataset ID for dataset operations
        input_data: JSON input data for actor run
        format: Output format for dataset (json, csv, xml)
        timeout: Request timeout in seconds (default: 60)
        dry_run: If True, return preview without making actual API call (default: True)
        APIFY_API_TOKEN: API token for authentication (from secrets)
        context: Request context (optional)
        client: ExternalApiClient instance (optional, for testing)

    Returns:
        Dict with 'output' containing the API response or preview
    """
    if not APIFY_API_TOKEN:
        return missing_secret_error("APIFY_API_TOKEN")

    if not operation:
        return generate_form(
            server_name="apify",
            title="Apify API",
            description="Scrape web data and automate tasks with Apify actors.",
            fields=[
                FormField(name="operation", label="Operation", field_type="select",
                         options=["list_actors", "run_actor", "get_run", "list_runs",
                                 "get_dataset", "download_dataset", "delete_dataset"],
                         required=True),
                FormField(name="actor_id", label="Actor ID", placeholder="actor~username"),
                FormField(name="run_id", label="Run ID", placeholder="run123"),
                FormField(name="dataset_id", label="Dataset ID", placeholder="dataset123"),
                FormField(name="input_data", label="Input Data (JSON)", field_type="textarea"),
                FormField(name="format", label="Format", field_type="select",
                         options=["json", "csv", "xml"], default="json"),
                FormField(name="dry_run", label="Dry Run", field_type="select",
                         options=["true", "false"], default="true"),
            ],
            examples=[{"title": "List Actors", "code": 'operation=list_actors'}],
            documentation_url=DOCUMENTATION_URL,
        )

    valid_operations = ["list_actors", "run_actor", "get_run", "list_runs",
                       "get_dataset", "download_dataset", "delete_dataset"]
    if operation not in valid_operations:
        return validation_error(f"Invalid operation: {operation}")

    if operation == "run_actor" and not actor_id:
        return validation_error("actor_id is required for run_actor")
    if operation in ["get_run"] and not run_id:
        return validation_error(f"run_id is required for {operation}")
    if operation in ["get_dataset", "download_dataset", "delete_dataset"] and not dataset_id:
        return validation_error(f"dataset_id is required for {operation}")

    parsed_input = {}
    if input_data:
        try:
            parsed_input = json.loads(input_data)
        except json.JSONDecodeError as e:
            return validation_error(f"Invalid JSON in input_data: {e}")

    if dry_run:
        preview = {"operation": operation, "api_endpoint": API_BASE_URL, "dry_run": True}
        if actor_id:
            preview["actor_id"] = actor_id
        if run_id:
            preview["run_id"] = run_id
        if dataset_id:
            preview["dataset_id"] = dataset_id
        if parsed_input:
            preview["input"] = parsed_input
        return {"output": preview, "content_type": "application/json"}

    if client is None:
        config = HttpClientConfig(timeout=timeout)
        client = ExternalApiClient(config)

    headers = {"Content-Type": "application/json"}
    params = {"token": APIFY_API_TOKEN}

    try:
        if operation == "list_actors":
            response = client.get(f"{API_BASE_URL}/acts", headers=headers, params=params)
        elif operation == "run_actor":
            response = client.post(f"{API_BASE_URL}/acts/{actor_id}/runs",
                                 headers=headers, params=params, json=parsed_input)
        elif operation == "get_run":
            response = client.get(f"{API_BASE_URL}/actor-runs/{run_id}",
                                headers=headers, params=params)
        elif operation == "list_runs":
            response = client.get(f"{API_BASE_URL}/actor-runs",
                                headers=headers, params=params)
        elif operation == "get_dataset":
            response = client.get(f"{API_BASE_URL}/datasets/{dataset_id}",
                                headers=headers, params=params)
        elif operation == "download_dataset":
            download_params = {**params, "format": format}
            response = client.get(f"{API_BASE_URL}/datasets/{dataset_id}/items",
                                headers=headers, params=download_params)
        elif operation == "delete_dataset":
            response = client.delete(f"{API_BASE_URL}/datasets/{dataset_id}",
                                   headers=headers, params=params)
        else:
            return validation_error(f"Unsupported operation: {operation}")

        response.raise_for_status()
        return {"output": response.json(), "content_type": "application/json"}

    except requests.RequestException as e:
        status_code = e.response.status_code if hasattr(e, "response") and e.response else None
        error_detail = e.response.text if hasattr(e, "response") and e.response else str(e)
        return error_response(f"Apify API request failed: {error_detail}",
                            "api_error", status_code)
    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", "api_error")
