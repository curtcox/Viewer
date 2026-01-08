# ruff: noqa: F821, F706
"""Interact with PandaDoc to manage documents and templates."""

from __future__ import annotations

from typing import Any, Dict, Optional

from server_utils.external_api import (
    ExternalApiClient,
    OperationDefinition,
    RequiredField,
    error_output,
    execute_json_request,
    validate_and_build_payload,
    validation_error,
)


_DEFAULT_CLIENT = ExternalApiClient()

_OPERATIONS = {
    "list_documents": OperationDefinition(),
    "get_document": OperationDefinition(
        required=(RequiredField("document_id", "Missing required document_id"),),
    ),
    "create_document": OperationDefinition(
        required=(
            RequiredField("name", "Missing required name"),
            RequiredField("template_uuid", "Missing required template_uuid"),
            RequiredField("recipient_email", "Missing required recipient_email"),
        ),
        payload_builder=lambda name, template_uuid, recipient_email, recipient_first_name, recipient_last_name, **_: {
            "name": name,
            "template_uuid": template_uuid,
            "recipients": [
                {
                    "email": recipient_email,
                    "first_name": recipient_first_name or "Recipient",
                    "last_name": recipient_last_name or "User",
                    "role": "Signer",
                }
            ],
        },
    ),
    "send_document": OperationDefinition(
        required=(RequiredField("document_id", "Missing required document_id"),),
        payload_builder=lambda message, **_: {
            "message": message or "Please sign this document",
        },
    ),
    "download_document": OperationDefinition(
        required=(RequiredField("document_id", "Missing required document_id"),),
    ),
    "list_templates": OperationDefinition(),
    "get_template": OperationDefinition(
        required=(RequiredField("template_id", "Missing required template_id"),),
    ),
}

_ENDPOINT_BUILDERS = {
    "list_documents": lambda base_url, **_: f"{base_url}/documents",
    "get_document": lambda base_url, document_id, **_: f"{base_url}/documents/{document_id}",
    "create_document": lambda base_url, **_: f"{base_url}/documents",
    "send_document": lambda base_url, document_id, **_: f"{base_url}/documents/{document_id}/send",
    "download_document": lambda base_url, document_id, **_: (
        f"{base_url}/documents/{document_id}/download"
    ),
    "list_templates": lambda base_url, **_: f"{base_url}/templates",
    "get_template": lambda base_url, template_id, **_: f"{base_url}/templates/{template_id}",
}

_METHODS = {
    "create_document": "POST",
    "send_document": "POST",
}


def _build_preview(
    *,
    operation: str,
    url: str,
    method: str,
    params: Optional[Dict[str, Any]],
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "API Key",
    }
    if params:
        preview["params"] = params
    if payload:
        preview["payload"] = payload
    return preview


def main(
    *,
    operation: str = "list_documents",
    document_id: str = "",
    template_id: str = "",
    status: str = "",
    name: str = "",
    template_uuid: str = "",
    recipient_email: str = "",
    recipient_first_name: str = "",
    recipient_last_name: str = "",
    message: str = "",
    PANDADOC_API_KEY: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Manage PandaDoc documents and templates.

    Operations:
    - list_documents: List documents with optional filters
    - get_document: Get document details by ID
    - create_document: Create a new document from a template
    - send_document: Send a document to recipients
    - download_document: Download a completed document (PDF)
    - list_templates: List available templates
    - get_template: Get template details by ID
    """

    if not PANDADOC_API_KEY:
        return error_output(
            "Missing PANDADOC_API_KEY",
            status_code=401,
            details="Provide an API key for PandaDoc API",
        )

    api_client = client or _DEFAULT_CLIENT

    base_url = "https://api.pandadoc.com/public/v1"
    headers = {
        "Authorization": f"API-Key {PANDADOC_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    if operation not in _OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        document_id=document_id,
        template_id=template_id,
        name=name,
        template_uuid=template_uuid,
        recipient_email=recipient_email,
        recipient_first_name=recipient_first_name,
        recipient_last_name=recipient_last_name,
        message=message,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])
    payload = result

    params: Optional[Dict[str, Any]] = None
    if operation == "list_documents" and status:
        params = {"status": status}

    if dry_run:
        url = _ENDPOINT_BUILDERS[operation](
            base_url=base_url,
            document_id=document_id,
            template_id=template_id,
        )
        method = _METHODS.get(operation, "GET")
        preview = _build_preview(
            operation=operation,
            url=url,
            method=method,
            params=params,
            payload=payload,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    url = _ENDPOINT_BUILDERS[operation](
        base_url=base_url,
        document_id=document_id,
        template_id=template_id,
    )
    method = _METHODS.get(operation, "GET")

    if operation == "download_document":
        try:
            response = api_client.get(url, headers=headers, params=params, timeout=timeout)
        except Exception as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            return error_output("PandaDoc request failed", status_code=status, details=str(exc))
        if getattr(response, "ok", False):
            return {"output": {"document": "PDF binary data", "content_type": "application/pdf"}}
        return error_output(
            "PandaDoc API error",
            status_code=getattr(response, "status_code", None),
            response=getattr(response, "text", None),
        )

    return execute_json_request(
        api_client,
        method,
        url,
        headers=headers,
        params=params,
        json=payload,
        timeout=timeout,
        error_parser=lambda _response, data: (
            data.get("detail", data.get("message", "PandaDoc API error"))
            if isinstance(data, dict)
            else "PandaDoc API error"
        ),
        request_error_message="PandaDoc request failed",
    )
