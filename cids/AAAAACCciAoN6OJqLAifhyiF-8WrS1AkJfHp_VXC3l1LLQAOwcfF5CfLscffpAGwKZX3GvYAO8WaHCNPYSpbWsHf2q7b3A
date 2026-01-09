# ruff: noqa: F821, F706
"""Interact with AWS S3 to manage files and buckets."""

from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import quote

from server_utils.external_api import (
    ExternalApiClient,
    OperationDefinition,
    RequiredField,
    error_output,
    validate_and_build_payload,
    validation_error,
)
from server_utils.external_api.limit_validator import AWS_S3_MAX_KEYS, get_limit_info, validate_limit
from server_utils.external_api.aws_signature import sign_request


_DEFAULT_CLIENT = ExternalApiClient()
_METHOD_MAP = {
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

_OPERATIONS = {
    "list_buckets": OperationDefinition(),
    "list_objects": OperationDefinition(required=(RequiredField("bucket"),)),
    "get_object": OperationDefinition(required=(RequiredField("key"),)),
    "put_object": OperationDefinition(
        required=(RequiredField("key"), RequiredField("content"))
    ),
    "delete_object": OperationDefinition(required=(RequiredField("key"),)),
    "create_bucket": OperationDefinition(required=(RequiredField("bucket"),)),
    "delete_bucket": OperationDefinition(required=(RequiredField("bucket"),)),
    "copy_object": OperationDefinition(required=(RequiredField("to_key"),)),
    "head_object": OperationDefinition(required=(RequiredField("key"),)),
}

_SUCCESS_OPERATIONS = {
    "put_object",
    "delete_object",
    "create_bucket",
    "delete_bucket",
}


def _sign_request(
    method: str,
    url: str,
    bucket: str,
    key: str,
    region: str,
    access_key: str,
    secret_key: str,
    headers: Dict[str, str],
    payload: bytes = b"",
) -> Dict[str, str]:
    """Generate AWS Signature Version 4 for S3 request using the proper implementation."""
    return sign_request(
        method=method,
        url=url,
        headers=headers,
        access_key=access_key,
        secret_key=secret_key,
        region=region,
        service="s3",
        payload=payload,
    )


def _build_preview(
    *,
    operation: str,
    bucket: str,
    key: str,
    region: str,
    params: Optional[Dict[str, Any]],
    max_keys: Optional[int] = None,
) -> Dict[str, Any]:
    """Build a preview of the S3 API call."""
    host = f"{bucket}.s3.{region}.amazonaws.com" if bucket else f"s3.{region}.amazonaws.com"
    method = _METHOD_MAP.get(operation, "GET")

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

    # Include limit constraint information for operations that use it
    if max_keys is not None and operation == "list_objects":
        preview["limit_constraint"] = get_limit_info(max_keys, AWS_S3_MAX_KEYS, "max_keys")

    return preview


def _build_url(*, operation: str, bucket: str, key: str, region: str) -> str:
    host = f"{bucket}.s3.{region}.amazonaws.com" if bucket else f"s3.{region}.amazonaws.com"
    if operation == "list_buckets":
        return f"https://s3.{region}.amazonaws.com/"
    if bucket and key:
        return f"https://{host}/{quote(key)}"
    if bucket:
        return f"https://{host}/"
    return f"https://s3.{region}.amazonaws.com/"


def _success_response(status_code: int) -> Dict[str, Any]:
    return {"output": {"status": "success", "status_code": status_code}}


def _build_params(operation: str, prefix: str, max_keys: int) -> Dict[str, Any] | None:
    if operation != "list_objects":
        return None
    params: Dict[str, Any] = {}
    if prefix:
        params["prefix"] = prefix
    params["max-keys"] = str(max_keys)
    return params


def _build_output(operation: str, response: Any) -> Dict[str, Any]:
    if operation in _SUCCESS_OPERATIONS:
        return _success_response(response.status_code)
    if operation == "get_object":
        return {"output": response.text}
    if operation == "head_object":
        return {"output": dict(response.headers)}
    return {"output": response.text}


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

    payload_result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        bucket=bucket,
        key=key,
        to_key=to_key,
        content=content,
    )
    if isinstance(payload_result, tuple):
        return validation_error(payload_result[0], field=payload_result[1])

    if not AWS_ACCESS_KEY_ID:
        return error_output("Missing AWS_ACCESS_KEY_ID", status_code=401)

    if not AWS_SECRET_ACCESS_KEY:
        return error_output("Missing AWS_SECRET_ACCESS_KEY", status_code=401)

    # Validate limit parameter (max_keys)
    # AWS S3 API enforces a maximum of 1000 keys per list operation
    if error := validate_limit(max_keys, AWS_S3_MAX_KEYS, "max_keys"):
        return error

    # Build parameters
    params = _build_params(operation, prefix, max_keys)

    # Return preview if in dry-run mode
    if dry_run:
        return {
            "output": _build_preview(
                operation=operation,
                bucket=bucket,
                key=key,
                region=AWS_REGION,
                params=params,
                max_keys=max_keys if operation == "list_objects" else None,
            )
        }

    # Execute actual API call
    api_client = client or _DEFAULT_CLIENT

    try:
        # Build URL and method
        method = _METHOD_MAP.get(operation, "GET")
        url = _build_url(operation=operation, bucket=bucket, key=key, region=AWS_REGION)

        # Build headers
        headers = {}
        if operation == "put_object":
            headers["Content-Type"] = content_type

        if operation == "copy_object":
            headers["x-amz-copy-source"] = f"/{bucket}/{key}"
            # For copy, we need to rebuild the URL with to_key
            url = _build_url(operation=operation, bucket=bucket, key=to_key, region=AWS_REGION)

        # Sign request
        payload = content.encode("utf-8") if operation == "put_object" and content else b""
        signed_headers = _sign_request(
            method=method,
            url=url,
            bucket=bucket,
            key=to_key if operation == "copy_object" else key,
            region=AWS_REGION,
            access_key=AWS_ACCESS_KEY_ID,
            secret_key=AWS_SECRET_ACCESS_KEY,
            headers=headers,
            payload=payload,
        )

        # Make request
        response = api_client.request(
            method=method,
            url=url,
            headers=signed_headers,
            data=content.encode("utf-8") if operation == "put_object" else None,
            params=params,
            timeout=timeout,
        )

        if not response.ok:
            return error_output(
                f"AWS S3 API error: {response.text}",
                status_code=response.status_code,
                response=response.text,
            )

        return _build_output(operation, response)

    except Exception as e:
        return error_output(str(e), status_code=500)
