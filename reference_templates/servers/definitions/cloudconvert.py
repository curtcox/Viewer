# ruff: noqa: F821, F706
"""Call the CloudConvert API for file conversion operations."""

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


API_BASE_URL = "https://api.cloudconvert.com/v2"
DOCUMENTATION_URL = "https://cloudconvert.com/api/v2"


def main(
    operation: str = "",
    input_format: str = "",
    output_format: str = "",
    task_id: str = "",
    job_id: str = "",
    file_url: str = "",
    filename: str = "",
    options: str = "",
    timeout: int = 60,
    dry_run: bool = True,
    *,
    CLOUDCONVERT_API_KEY: str,
    context=None,
    client: Optional[ExternalApiClient] = None,
):
    """
    Make a request to the CloudConvert API.

    Args:
        operation: Operation to perform (create_job, get_job, list_jobs, get_task,
                   cancel_task, delete_task, export_file)
        input_format: Input file format (e.g., pdf, docx, jpg)
        output_format: Output file format (e.g., pdf, txt, png)
        task_id: Task ID for task operations
        job_id: Job ID for job operations
        file_url: URL of file to convert
        filename: Filename for the conversion
        options: JSON string with conversion options
        timeout: Request timeout in seconds (default: 60)
        dry_run: If True, return preview without making actual API call (default: True)
        CLOUDCONVERT_API_KEY: API key for authentication (from secrets)
        context: Request context (optional)
        client: ExternalApiClient instance (optional, for testing)

    Returns:
        Dict with 'output' containing the API response or preview
    """
    # Validate secrets first
    if not CLOUDCONVERT_API_KEY:
        return missing_secret_error("CLOUDCONVERT_API_KEY")

    # Show form if no operation provided
    if not operation:
        return generate_form(
            server_name="cloudconvert",
            title="CloudConvert API",
            description=(
                "Convert files between 200+ formats including documents, images, "
                "videos, audio, and more using CloudConvert API."
            ),
            fields=[
                FormField(
                    name="operation",
                    label="Operation",
                    field_type="select",
                    options=[
                        "create_job",
                        "get_job",
                        "list_jobs",
                        "get_task",
                        "cancel_task",
                        "delete_task",
                        "export_file",
                    ],
                    required=True,
                ),
                FormField(
                    name="input_format",
                    label="Input Format",
                    placeholder="pdf",
                    help_text="Required for create_job (e.g., pdf, docx, jpg)",
                ),
                FormField(
                    name="output_format",
                    label="Output Format",
                    placeholder="txt",
                    help_text="Required for create_job (e.g., txt, pdf, png)",
                ),
                FormField(
                    name="file_url",
                    label="File URL",
                    placeholder="https://example.com/file.pdf",
                    help_text="URL of file to convert (for create_job)",
                ),
                FormField(
                    name="filename",
                    label="Filename",
                    placeholder="document.pdf",
                    help_text="Filename for the conversion",
                ),
                FormField(
                    name="job_id",
                    label="Job ID",
                    placeholder="abc123-def456",
                    help_text="Required for get_job",
                ),
                FormField(
                    name="task_id",
                    label="Task ID",
                    placeholder="task123",
                    help_text="Required for task operations",
                ),
                FormField(
                    name="options",
                    label="Conversion Options (JSON)",
                    field_type="textarea",
                    placeholder='{"quality": 90}',
                    help_text="Optional conversion parameters as JSON",
                ),
                FormField(
                    name="dry_run",
                    label="Dry Run",
                    field_type="select",
                    options=["true", "false"],
                    default="true",
                    help_text="Preview the request without executing",
                ),
            ],
            examples=[
                {
                    "title": "Convert PDF to Text",
                    "code": 'operation=create_job&input_format=pdf&output_format=txt&file_url=https://example.com/doc.pdf',
                },
                {
                    "title": "Get Job Status",
                    "code": 'operation=get_job&job_id=abc123-def456',
                },
                {
                    "title": "List Recent Jobs",
                    "code": 'operation=list_jobs',
                },
            ],
            documentation_url=DOCUMENTATION_URL,
        )

    # Validate operation
    valid_operations = [
        "create_job", "get_job", "list_jobs", "get_task",
        "cancel_task", "delete_task", "export_file"
    ]
    if operation not in valid_operations:
        return validation_error(
            f"Invalid operation: {operation}. Must be one of {valid_operations}"
        )

    # Operation-specific validation
    if operation == "create_job":
        if not input_format:
            return validation_error("input_format is required for create_job")
        if not output_format:
            return validation_error("output_format is required for create_job")
        if not file_url:
            return validation_error("file_url is required for create_job")

    if operation == "get_job" and not job_id:
        return validation_error("job_id is required for get_job")

    if operation in ["get_task", "cancel_task", "delete_task"]:
        if not task_id:
            return validation_error(f"task_id is required for {operation}")

    if operation == "export_file" and not task_id:
        return validation_error("task_id is required for export_file")

    # Parse options if provided
    parsed_options = {}
    if options:
        try:
            parsed_options = json.loads(options)
        except json.JSONDecodeError as e:
            return validation_error(f"Invalid JSON in options: {e}")

    # Dry run preview
    if dry_run:
        preview = {
            "operation": operation,
            "api_endpoint": API_BASE_URL,
            "dry_run": True,
        }
        
        if operation == "create_job":
            preview["conversion"] = {
                "input_format": input_format,
                "output_format": output_format,
                "file_url": file_url,
                "filename": filename or f"output.{output_format}",
                "options": parsed_options,
            }
        elif operation == "get_job":
            preview["job_id"] = job_id
        elif operation == "list_jobs":
            preview["action"] = "List all jobs"
        elif operation in ["get_task", "cancel_task", "delete_task", "export_file"]:
            preview["task_id"] = task_id

        return {"output": preview, "content_type": "application/json"}

    # Create HTTP client
    if client is None:
        config = HttpClientConfig(timeout=timeout)
        client = ExternalApiClient(config)

    headers = {
        "Authorization": f"Bearer {CLOUDCONVERT_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        # Build request based on operation
        if operation == "create_job":
            # Create a conversion job with import, convert, and export tasks
            job_payload = {
                "tasks": {
                    "import-file": {
                        "operation": "import/url",
                        "url": file_url,
                        "filename": filename or f"input.{input_format}",
                    },
                    "convert-file": {
                        "operation": f"convert",
                        "input": "import-file",
                        "input_format": input_format,
                        "output_format": output_format,
                        **parsed_options,
                    },
                    "export-file": {
                        "operation": "export/url",
                        "input": "convert-file",
                    },
                },
            }
            response = client.post(f"{API_BASE_URL}/jobs", headers=headers, json=job_payload)
        
        elif operation == "get_job":
            response = client.get(f"{API_BASE_URL}/jobs/{job_id}", headers=headers)
        
        elif operation == "list_jobs":
            response = client.get(f"{API_BASE_URL}/jobs", headers=headers)
        
        elif operation == "get_task":
            response = client.get(f"{API_BASE_URL}/tasks/{task_id}", headers=headers)
        
        elif operation == "cancel_task":
            response = client.post(f"{API_BASE_URL}/tasks/{task_id}/cancel", headers=headers)
        
        elif operation == "delete_task":
            response = client.delete(f"{API_BASE_URL}/tasks/{task_id}", headers=headers)
        
        elif operation == "export_file":
            response = client.get(f"{API_BASE_URL}/tasks/{task_id}", headers=headers)
        
        else:
            return validation_error(f"Unsupported operation: {operation}")

        response.raise_for_status()
        return {"output": response.json(), "content_type": "application/json"}

    except requests.RequestException as e:
        status_code = e.response.status_code if hasattr(e, "response") and e.response else None
        error_detail = ""
        if hasattr(e, "response") and e.response:
            try:
                error_detail = e.response.text
            except Exception:
                error_detail = str(e)
        else:
            error_detail = str(e)
        
        return error_response(
            message=f"CloudConvert API request failed: {error_detail}",
            error_type="api_error",
            status_code=status_code,
        )
    except Exception as e:
        return error_response(
            message=f"Unexpected error: {str(e)}",
            error_type="api_error",
        )
