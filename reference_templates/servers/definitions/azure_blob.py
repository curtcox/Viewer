# ruff: noqa: F821, F706
"""Interact with Azure Blob Storage to manage files and containers."""

from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import quote

from server_utils.external_api import ExternalApiClient, error_output, validation_error
from server_utils.external_api.azure_signature import sign_request


_DEFAULT_CLIENT = ExternalApiClient()


def _sign_request(
    method: str,
    url: str,
    headers: Dict[str, str],
    account_name: str,
    account_key: str,
    content_length: int = 0,
) -> Dict[str, str]:
    """Generate Azure Shared Key signature for Blob Storage request using proper implementation."""
    return sign_request(
        method=method,
        url=url,
        headers=headers,
        account_name=account_name,
        account_key=account_key,
        content_length=content_length,
    )


def _build_preview(
    *,
    operation: str,
    account_name: str,
    container: str,
    blob_name: str,
    params: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build a preview of the Azure Blob Storage API call."""
    base_url = f"https://{account_name}.blob.core.windows.net"
    
    method_map = {
        "list_containers": "GET",
        "list_blobs": "GET",
        "get_blob": "GET",
        "upload_blob": "PUT",
        "delete_blob": "DELETE",
        "create_container": "PUT",
        "delete_container": "DELETE",
        "get_container_properties": "GET",
        "copy_blob": "PUT",
        "get_blob_properties": "HEAD",
    }
    
    method = method_map.get(operation, "GET")
    
    if operation == "list_containers":
        url = f"{base_url}/?comp=list"
    elif operation == "list_blobs":
        url = f"{base_url}/{container}?restype=container&comp=list"
    elif operation in ("get_blob", "delete_blob", "upload_blob", "copy_blob", "get_blob_properties"):
        url = f"{base_url}/{container}/{quote(blob_name)}"
    elif operation in ("create_container", "delete_container", "get_container_properties"):
        url = f"{base_url}/{container}?restype=container"
    else:
        url = base_url
    
    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "Azure Shared Key",
    }
    if params:
        preview["params"] = params
    return preview


def main(
    *,
    operation: str = "list_containers",
    container: str = "",
    blob_name: str = "",
    to_blob: str = "",
    prefix: str = "",
    max_results: int = 1000,
    content: str = "",
    content_type: str = "application/octet-stream",
    AZURE_STORAGE_ACCOUNT: str = "",
    AZURE_STORAGE_KEY: str = "",
    AZURE_STORAGE_CONNECTION_STRING: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Manage Azure Blob Storage containers and blobs.
    
    Operations:
    - list_containers: List all containers in the account
    - list_blobs: List blobs in a container
    - get_blob: Download a blob
    - upload_blob: Upload a blob
    - delete_blob: Delete a blob
    - create_container: Create a new container
    - delete_container: Delete a container
    - get_container_properties: Get container metadata
    - copy_blob: Copy a blob
    - get_blob_properties: Get blob metadata
    """
    
    normalized_operation = operation.lower()
    valid_operations = {
        "list_containers",
        "list_blobs",
        "get_blob",
        "upload_blob",
        "delete_blob",
        "create_container",
        "delete_container",
        "get_container_properties",
        "copy_blob",
        "get_blob_properties",
    }
    
    if normalized_operation not in valid_operations:
        return validation_error("Unsupported operation", field="operation")
    
    # Parse connection string if provided
    account_name = AZURE_STORAGE_ACCOUNT
    account_key = AZURE_STORAGE_KEY
    
    if AZURE_STORAGE_CONNECTION_STRING:
        try:
            parts = dict(part.split("=", 1) for part in AZURE_STORAGE_CONNECTION_STRING.split(";") if "=" in part)
            account_name = parts.get("AccountName", "")
            account_key = parts.get("AccountKey", "")
        except Exception:
            return error_output("Invalid AZURE_STORAGE_CONNECTION_STRING format", status_code=400)
    
    # Validate credentials
    if not account_name:
        return error_output("Missing AZURE_STORAGE_ACCOUNT or AZURE_STORAGE_CONNECTION_STRING", status_code=401)
    
    if not account_key:
        return error_output("Missing AZURE_STORAGE_KEY or AZURE_STORAGE_CONNECTION_STRING", status_code=401)
    
    # Validate operation-specific parameters
    if normalized_operation in ("list_blobs", "create_container", "delete_container", "get_container_properties") and not container:
        return validation_error("Missing required container", field="container")
    
    if normalized_operation in ("get_blob", "upload_blob", "delete_blob", "copy_blob", "get_blob_properties") and not blob_name:
        return validation_error("Missing required blob_name", field="blob_name")
    
    if normalized_operation == "upload_blob" and not content:
        return validation_error("Missing required content", field="content")
    
    if normalized_operation == "copy_blob" and not to_blob:
        return validation_error("Missing required to_blob", field="to_blob")
    
    # Build parameters
    params: Dict[str, Any] = {}
    if normalized_operation == "list_blobs":
        if prefix:
            params["prefix"] = prefix
        params["maxresults"] = str(max_results)
    
    # Return preview if in dry-run mode
    if dry_run:
        return {
            "output": _build_preview(
                operation=normalized_operation,
                account_name=account_name,
                container=container,
                blob_name=blob_name,
                params=params if params else None,
            )
        }
    
    # Execute actual API call
    api_client = client or _DEFAULT_CLIENT
    
    try:
        # Build headers
        headers = {}
        if normalized_operation == "upload_blob":
            headers["x-ms-blob-type"] = "BlockBlob"
            headers["Content-Type"] = content_type
            headers["Content-Length"] = str(len(content.encode("utf-8")))
        
        if normalized_operation == "copy_blob":
            source_url = f"https://{account_name}.blob.core.windows.net/{container}/{blob_name}"
            headers["x-ms-copy-source"] = source_url
            blob_name = to_blob
        
        # Sign request
        preview = _build_preview(
            operation=normalized_operation,
            account_name=account_name,
            container=container,
            blob_name=blob_name,
            params=params,
        )
        url = preview["url"]
        method = preview["method"]
        
        signed_headers = _sign_request(
            method=method,
            url=url,
            headers=headers,
            account_name=account_name,
            account_key=account_key,
            content_length=len(content.encode("utf-8")) if normalized_operation == "upload_blob" and content else 0,
        )
        
        # Make request
        request_kwargs: Dict[str, Any] = {
            "method": method,
            "url": url,
            "headers": signed_headers,
            "timeout": timeout,
        }
        
        if normalized_operation == "upload_blob":
            request_kwargs["data"] = content.encode("utf-8")
        
        response = api_client.request(**request_kwargs)
        
        if not response.ok:
            return error_output(
                f"Azure Blob Storage API error: {response.text}",
                status_code=response.status_code,
                response=response.text,
            )
        
        # Parse response based on operation
        if normalized_operation in ("upload_blob", "delete_blob", "create_container", "delete_container", "copy_blob"):
            return {"output": {"status": "success", "status_code": response.status_code}}
        elif normalized_operation == "get_blob":
            return {"output": response.text}
        elif normalized_operation in ("get_blob_properties", "get_container_properties"):
            return {"output": dict(response.headers)}
        else:
            # List operations return XML
            return {"output": response.text}
    
    except Exception as e:
        return error_output(str(e), status_code=500)
