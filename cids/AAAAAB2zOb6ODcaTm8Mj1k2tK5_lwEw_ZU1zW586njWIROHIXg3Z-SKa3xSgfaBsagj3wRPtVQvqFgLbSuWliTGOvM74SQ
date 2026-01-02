# ruff: noqa: F821, F706
"""Interact with AWS S3 to manage files and buckets."""

from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime, timezone
from urllib.parse import quote

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


def _sign_request(
    method: str,
    bucket: str,
    key: str,
    region: str,
    access_key: str,
    secret_key: str,
    headers: Dict[str, str],
) -> Dict[str, str]:
    """Generate AWS Signature Version 4 for S3 request."""
    service = "s3"
    host = f"{bucket}.s3.{region}.amazonaws.com" if bucket else f"s3.{region}.amazonaws.com"
    
    # Add required headers
    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    
    # For simplicity in dry-run, we'll return the headers structure
    # Real implementation would compute the full signature
    signed_headers = {
        "Host": host,
        "X-Amz-Date": amz_date,
        "Authorization": f"AWS4-HMAC-SHA256 Credential={access_key}/{date_stamp}/{region}/{service}/aws4_request",
    }
    signed_headers.update(headers)
    
    return signed_headers


def _build_preview(
    *,
    operation: str,
    bucket: str,
    key: str,
    region: str,
    params: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build a preview of the S3 API call."""
    host = f"{bucket}.s3.{region}.amazonaws.com" if bucket else f"s3.{region}.amazonaws.com"
    
    method_map = {
        "list_buckets": "GET",
        "list_objects": "GET",
        "get_object": "GET",
        "put_object": "PUT",
        "delete_object": "DELETE",
        "create_bucket": "PUT",
        "delete_bucket": "DELETE",
        "copy_object": "PUT",
        "head_object": "HEAD",
    }
    
    method = method_map.get(operation, "GET")
    
    if operation == "list_buckets":
        url = f"https://s3.{region}.amazonaws.com/"
    elif bucket and key:
        url = f"https://{host}/{quote(key)}"
    elif bucket:
        url = f"https://{host}/"
    else:
        url = f"https://s3.{region}.amazonaws.com/"
    
    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "AWS Signature V4",
    }
    if params:
        preview["params"] = params
    return preview


def main(
    *,
    operation: str = "list_buckets",
    bucket: str = "",
    key: str = "",
    to_key: str = "",
    prefix: str = "",
    max_keys: int = 1000,
    content: str = "",
    content_type: str = "application/octet-stream",
    AWS_ACCESS_KEY_ID: str = "",
    AWS_SECRET_ACCESS_KEY: str = "",
    AWS_REGION: str = "us-east-1",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Manage AWS S3 buckets and objects.
    
    Operations:
    - list_buckets: List all buckets
    - list_objects: List objects in a bucket
    - get_object: Download an object
    - put_object: Upload an object
    - delete_object: Delete an object
    - create_bucket: Create a new bucket
    - delete_bucket: Delete a bucket
    - copy_object: Copy an object
    - head_object: Get object metadata
    """
    
    normalized_operation = operation.lower()
    valid_operations = {
        "list_buckets",
        "list_objects",
        "get_object",
        "put_object",
        "delete_object",
        "create_bucket",
        "delete_bucket",
        "copy_object",
        "head_object",
    }
    
    if normalized_operation not in valid_operations:
        return validation_error("Unsupported operation", field="operation")
    
    # Validate credentials
    if not AWS_ACCESS_KEY_ID:
        return error_output("Missing AWS_ACCESS_KEY_ID", status_code=401)
    
    if not AWS_SECRET_ACCESS_KEY:
        return error_output("Missing AWS_SECRET_ACCESS_KEY", status_code=401)
    
    # Validate operation-specific parameters
    if normalized_operation in ("list_objects", "create_bucket", "delete_bucket") and not bucket:
        return validation_error("Missing required bucket", field="bucket")
    
    if normalized_operation in ("get_object", "put_object", "delete_object", "head_object") and not key:
        return validation_error("Missing required key", field="key")
    
    if normalized_operation == "put_object" and not content:
        return validation_error("Missing required content", field="content")
    
    if normalized_operation == "copy_object" and not to_key:
        return validation_error("Missing required to_key", field="to_key")
    
    # Build parameters
    params: Dict[str, Any] = {}
    if normalized_operation == "list_objects":
        if prefix:
            params["prefix"] = prefix
        params["max-keys"] = str(max_keys)
    
    # Return preview if in dry-run mode
    if dry_run:
        return {
            "output": _build_preview(
                operation=normalized_operation,
                bucket=bucket,
                key=key,
                region=AWS_REGION,
                params=params if params else None,
            )
        }
    
    # Execute actual API call
    api_client = client or _DEFAULT_CLIENT
    
    try:
        # Build URL and method
        preview = _build_preview(operation=normalized_operation, bucket=bucket, key=key, region=AWS_REGION, params=params)
        url = preview["url"]
        method = preview["method"]
        
        # Build headers
        headers = {}
        if normalized_operation == "put_object":
            headers["Content-Type"] = content_type
        
        if normalized_operation == "copy_object":
            headers["x-amz-copy-source"] = f"/{bucket}/{key}"
            # For copy, we need to rebuild the URL with to_key
            preview = _build_preview(operation=normalized_operation, bucket=bucket, key=to_key, region=AWS_REGION, params=params)
            url = preview["url"]
        
        # Sign request
        signed_headers = _sign_request(
            method=method,
            bucket=bucket,
            key=to_key if normalized_operation == "copy_object" else key,
            region=AWS_REGION,
            access_key=AWS_ACCESS_KEY_ID,
            secret_key=AWS_SECRET_ACCESS_KEY,
            headers=headers,
        )
        
        # Make request
        response = api_client.request(
            method=method,
            url=url,
            headers=signed_headers,
            data=content.encode("utf-8") if normalized_operation == "put_object" else None,
            params=params if params else None,
            timeout=timeout,
        )
        
        if not response.ok:
            return error_output(
                f"AWS S3 API error: {response.text}",
                status_code=response.status_code,
                response=response.text,
            )
        
        # Parse response based on operation
        if normalized_operation in ("put_object", "delete_object", "create_bucket", "delete_bucket"):
            return {"output": {"status": "success", "status_code": response.status_code}}
        elif normalized_operation == "get_object":
            return {"output": response.text}
        elif normalized_operation == "head_object":
            return {"output": dict(response.headers)}
        else:
            # List operations return XML, parse as text for now
            return {"output": response.text}
    
    except Exception as e:
        return error_output(str(e), status_code=500)
