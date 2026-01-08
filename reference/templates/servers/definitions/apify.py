# ruff: noqa: F821, F706
"""Call the Apify API for web scraping and automation."""

from typing import Any, Dict, Optional

import json

from server_utils.external_api import (
    ExternalApiClient,
    FormField,
    HttpClientConfig,
    OperationDefinition,
    RequiredField,
    execute_json_request,
    generate_form,
    missing_secret_error,
    validate_and_build_payload,
    validation_error,
)


API_BASE_URL = "https://api.apify.com/v2"
DOCUMENTATION_URL = "https://docs.apify.com/api/v2"


_OPERATIONS = {
    "list_actors": OperationDefinition(),
    "run_actor": OperationDefinition(
        required=(RequiredField("actor_id", message="actor_id is required"),),
        payload_builder=lambda input_data, **_: input_data or {},
    ),
    "get_run": OperationDefinition(
        required=(RequiredField("run_id", message="run_id is required"),),
    ),
    "list_runs": OperationDefinition(),
    "get_dataset": OperationDefinition(
        required=(RequiredField("dataset_id", message="dataset_id is required"),),
    ),
    "download_dataset": OperationDefinition(
        required=(RequiredField("dataset_id", message="dataset_id is required"),),
    ),
    "delete_dataset": OperationDefinition(
        required=(RequiredField("dataset_id", message="dataset_id is required"),),
    ),
}

_ENDPOINT_BUILDERS = {
    "list_actors": lambda **_: "acts",
    "run_actor": lambda actor_id, **_: f"acts/{actor_id}/runs",
    "get_run": lambda run_id, **_: f"actor-runs/{run_id}",
    "list_runs": lambda **_: "actor-runs",
    "get_dataset": lambda dataset_id, **_: f"datasets/{dataset_id}",
    "download_dataset": lambda dataset_id, **_: f"datasets/{dataset_id}/items",
    "delete_dataset": lambda dataset_id, **_: f"datasets/{dataset_id}",
}

_METHODS = {
    "run_actor": "POST",
    "delete_dataset": "DELETE",
}

_PARAMETER_BUILDERS = {
    "download_dataset": lambda output_format, **_: {"format": output_format},
}


def _build_preview(
    *,
    operation: str,
    actor_id: str,
    run_id: str,
    dataset_id: str,
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    preview: Dict[str, Any] = {
        "operation": operation,
        "api_endpoint": API_BASE_URL,
        "dry_run": True,
    }
    if actor_id:
        preview["actor_id"] = actor_id
    if run_id:
        preview["run_id"] = run_id
    if dataset_id:
        preview["dataset_id"] = dataset_id
    if payload:
        preview["input"] = payload
    return preview


def main(
    operation: str = "",
    actor_id: str = "",
    run_id: str = "",
    dataset_id: str = "",
    input_data: str = "",
    output_format: str = "json",
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
        output_format: Output format for dataset (json, csv, xml)
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

    if operation not in _OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    parsed_input = None
    if input_data:
        try:
            parsed_input = json.loads(input_data)
        except json.JSONDecodeError as exc:
            return validation_error(f"Invalid JSON in input_data: {exc}")

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        actor_id=actor_id,
        run_id=run_id,
        dataset_id=dataset_id,
        input_data=parsed_input,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    endpoint = _ENDPOINT_BUILDERS[operation](
        actor_id=actor_id,
        run_id=run_id,
        dataset_id=dataset_id,
    )
    url = f"{API_BASE_URL}/{endpoint}"
    method = _METHODS.get(operation, "GET")
    payload = result if isinstance(result, dict) else None

    params: Dict[str, Any] = {"token": APIFY_API_TOKEN}
    extra_params = _PARAMETER_BUILDERS.get(operation, lambda **_: None)(
        output_format=output_format
    )
    if extra_params:
        params.update(extra_params)

    if dry_run:
        preview = _build_preview(
            operation=operation,
            actor_id=actor_id,
            run_id=run_id,
            dataset_id=dataset_id,
            payload=payload,
        )
        return {"output": preview, "content_type": "application/json"}

    if client is None:
        config = HttpClientConfig(timeout=timeout)
        client = ExternalApiClient(config)

    headers = {"Content-Type": "application/json"}

    return execute_json_request(
        client,
        method,
        url,
        headers=headers,
        params=params,
        json=payload,
        timeout=timeout,
        request_error_message="Apify API request failed",
    )
