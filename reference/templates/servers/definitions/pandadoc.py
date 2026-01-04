# ruff: noqa: F821, F706
"""Interact with PandaDoc to manage documents and templates."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


def _build_preview(
    *,
    operation: str,
    document_id: Optional[str],
    template_id: Optional[str],
    params: Optional[Dict[str, Any]],
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    base_url = "https://api.pandadoc.com/public/v1"
    
    if operation == "list_documents":
        url = f"{base_url}/documents"
    elif operation == "get_document" and document_id:
        url = f"{base_url}/documents/{document_id}"
    elif operation == "create_document":
        url = f"{base_url}/documents"
    elif operation == "send_document" and document_id:
        url = f"{base_url}/documents/{document_id}/send"
    elif operation == "download_document" and document_id:
        url = f"{base_url}/documents/{document_id}/download"
    elif operation == "list_templates":
        url = f"{base_url}/templates"
    elif operation == "get_template" and template_id:
        url = f"{base_url}/templates/{template_id}"
    else:
        url = f"{base_url}/{operation}"

    method_map = {
        "create_document": "POST",
        "send_document": "POST",
    }
    method = method_map.get(operation, "GET")

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

    normalized_operation = operation.lower()
    valid_operations = {
        "list_documents",
        "get_document",
        "create_document",
        "send_document",
        "download_document",
        "list_templates",
        "get_template",
    }
    
    if normalized_operation not in valid_operations:
        return validation_error("Unsupported operation", field="operation")

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

    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "list_documents":
        params = {}
        if status:
            params["status"] = status
    elif normalized_operation == "get_document":
        if not document_id:
            return validation_error("Missing required document_id", field="document_id")
    elif normalized_operation == "create_document":
        if not name:
            return validation_error("Missing required name", field="name")
        if not template_uuid:
            return validation_error("Missing required template_uuid", field="template_uuid")
        if not recipient_email:
            return validation_error("Missing required recipient_email", field="recipient_email")
        
        payload = {
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
        }
    elif normalized_operation == "send_document":
        if not document_id:
            return validation_error("Missing required document_id", field="document_id")
        payload = {"message": message or "Please sign this document"}
    elif normalized_operation == "download_document":
        if not document_id:
            return validation_error("Missing required document_id", field="document_id")
    elif normalized_operation == "get_template":
        if not template_id:
            return validation_error("Missing required template_id", field="template_id")

    if dry_run:
        preview = _build_preview(
            operation=normalized_operation,
            document_id=document_id,
            template_id=template_id,
            params=params,
            payload=payload,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    # Build URL
    if normalized_operation == "list_documents":
        url = f"{base_url}/documents"
    elif normalized_operation == "get_document":
        url = f"{base_url}/documents/{document_id}"
    elif normalized_operation == "create_document":
        url = f"{base_url}/documents"
    elif normalized_operation == "send_document":
        url = f"{base_url}/documents/{document_id}/send"
    elif normalized_operation == "download_document":
        url = f"{base_url}/documents/{document_id}/download"
    elif normalized_operation == "list_templates":
        url = f"{base_url}/templates"
    elif normalized_operation == "get_template":
        url = f"{base_url}/templates/{template_id}"
    else:
        url = f"{base_url}/{normalized_operation}"

    try:
        if normalized_operation in {"create_document", "send_document"}:
            response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
        else:
            response = api_client.get(url, headers=headers, params=params, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("PandaDoc request failed", status_code=status, details=str(exc))

    # Handle binary download for PDFs
    if normalized_operation == "download_document" and response.ok:
        return {"output": {"document": "PDF binary data", "content_type": "application/pdf"}}

    try:
        data = response.json()
    except ValueError:
        return error_output(
            "Invalid JSON response",
            status_code=getattr(response, "status_code", None),
            details=getattr(response, "text", None),
        )

    if not getattr(response, "ok", False):
        error_msg = data.get("detail", data.get("message", "PandaDoc API error"))
        return error_output(error_msg, status_code=response.status_code, response=data)

    return {"output": data}
