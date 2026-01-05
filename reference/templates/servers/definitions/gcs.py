# ruff: noqa: F821, F706
"""Interact with Google Cloud Storage to manage files and buckets."""

from __future__ import annotations

from typing import Any, Dict, Optional
import json

from server_utils.external_api import ExternalApiClient, error_output, validation_error, GoogleAuthManager


_DEFAULT_CLIENT = ExternalApiClient()
_DEFAULT_AUTH_MANAGER = GoogleAuthManager()
_SCOPES = ["https://www.googleapis.com/auth/devstorage.full_control"]


def _build_preview(
    *,
    operation: str,
    bucket: str,
    object_name: str,
    params: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build a preview of the GCS API call."""
    api_base = "https://storage.googleapis.com/storage/v1"
    
    method_map = {
        "list_buckets": "GET",
        "list_objects": "GET",
        "get_object": "GET",
        "upload_object": "POST",
        "delete_object": "DELETE",
        "create_bucket": "POST",
        "delete_bucket": "DELETE",
        "get_bucket": "GET",
        "copy_object": "POST",
    }
    
    method = method_map.get(operation, "GET")
    
    if operation == "list_buckets":
        url = f"{api_base}/b"
    elif operation == "list_objects":
        url = f"{api_base}/b/{bucket}/o"
    elif operation in ("get_object", "delete_object"):
        url = f"{api_base}/b/{bucket}/o/{object_name}"
    elif operation == "upload_object":
        url = f"https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o"
    elif operation == "copy_object":
        url = f"{api_base}/b/{bucket}/o/{object_name}/copyTo/b/{bucket}/o"
    elif operation == "create_bucket":
        url = f"{api_base}/b"
    elif operation in ("delete_bucket", "get_bucket"):
        url = f"{api_base}/b/{bucket}"
    else:
        url = api_base
    
    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "Google OAuth / Service Account",
    }
    if params:
        preview["params"] = params
    return preview


def main(
    *,
    operation: str = "list_buckets",
    bucket: str = "",
    object_name: str = "",
    to_object: str = "",
    prefix: str = "",
    max_results: int = 1000,
    content: str = "",
    content_type: str = "application/octet-stream",
    project_id: str = "",
    GOOGLE_SERVICE_ACCOUNT_JSON: str = "",
    GOOGLE_ACCESS_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    auth_manager: Optional[GoogleAuthManager] = None,
    context=None,
) -> Dict[str, Any]:
    """Manage Google Cloud Storage buckets and objects.
    
    Operations:
    - list_buckets: List all buckets in a project
    - list_objects: List objects in a bucket
    - get_object: Download an object
    - upload_object: Upload an object
    - delete_object: Delete an object
    - create_bucket: Create a new bucket
    - delete_bucket: Delete a bucket
    - get_bucket: Get bucket metadata
    - copy_object: Copy an object within a bucket
    """
    
    normalized_operation = operation.lower()
    valid_operations = {
        "list_buckets",
        "list_objects",
        "get_object",
        "upload_object",
        "delete_object",
        "create_bucket",
        "delete_bucket",
        "get_bucket",
        "copy_object",
    }
    
    if normalized_operation not in valid_operations:
        return validation_error("Unsupported operation", field="operation")
    
    # Validate credentials
    if not GOOGLE_SERVICE_ACCOUNT_JSON and not GOOGLE_ACCESS_TOKEN:
        return error_output(
            "Missing GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_ACCESS_TOKEN",
            status_code=401,
        )
    
    # Validate operation-specific parameters
    if normalized_operation == "list_buckets" and not project_id:
        return validation_error("Missing required project_id for list_buckets", field="project_id")
    
    if normalized_operation in ("list_objects", "get_bucket", "delete_bucket", "create_bucket") and not bucket:
        return validation_error("Missing required bucket", field="bucket")
    
    if normalized_operation in ("get_object", "upload_object", "delete_object", "copy_object") and not object_name:
        return validation_error("Missing required object_name", field="object_name")
    
    if normalized_operation == "upload_object" and not content:
        return validation_error("Missing required content", field="content")
    
    if normalized_operation == "copy_object" and not to_object:
        return validation_error("Missing required to_object", field="to_object")
    
    # Build parameters
    params: Dict[str, Any] = {}
    if normalized_operation == "list_buckets":
        params["project"] = project_id
    elif normalized_operation == "list_objects":
        if prefix:
            params["prefix"] = prefix
        params["maxResults"] = str(max_results)
    elif normalized_operation == "upload_object":
        params["uploadType"] = "media"
        params["name"] = object_name
    
    # Return preview if in dry-run mode
    if dry_run:
        return {
            "output": _build_preview(
                operation=normalized_operation,
                bucket=bucket,
                object_name=object_name,
                params=params if params else None,
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
                details="Provide GOOGLE_ACCESS_TOKEN or GOOGLE_SERVICE_ACCOUNT_JSON",
            )
        
        # Add content type for uploads
        if normalized_operation == "upload_object":
            headers["Content-Type"] = content_type
        
        # Build URL
        preview = _build_preview(
            operation=normalized_operation,
            bucket=bucket,
            object_name=object_name,
            params=params,
        )
        url = preview["url"]
        method = preview["method"]
        
        # Handle copy operation URL
        if normalized_operation == "copy_object":
            url = url + to_object
        
        # Make request
        request_kwargs: Dict[str, Any] = {
            "method": method,
            "url": url,
            "headers": headers,
            "timeout": timeout,
        }
        
        if params:
            request_kwargs["params"] = params
        
        if normalized_operation == "upload_object":
            request_kwargs["data"] = content.encode("utf-8")
        elif normalized_operation == "create_bucket":
            request_kwargs["json"] = {"name": bucket}
            if project_id:
                request_kwargs["params"] = {"project": project_id}
        
        response = api_client.request(**request_kwargs)
        
        if not response.ok:
            return error_output(
                f"GCS API error: {response.text}",
                status_code=response.status_code,
                response=response.text,
            )
        
        # Parse response based on operation
        if normalized_operation in ("upload_object", "delete_object", "create_bucket", "delete_bucket", "copy_object"):
            if response.text:
                try:
                    return {"output": response.json()}
                except Exception:
                    return {"output": {"status": "success", "status_code": response.status_code}}
            return {"output": {"status": "success", "status_code": response.status_code}}
        elif normalized_operation == "get_object":
            return {"output": response.text}
        else:
            # List and get operations return JSON
            return {"output": response.json()}
    
    except Exception as e:
        return error_output(str(e), status_code=500)
