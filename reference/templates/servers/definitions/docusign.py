# ruff: noqa: F821, F706
"""Interact with DocuSign to manage envelopes, documents, and templates."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


def _build_preview(
    *,
    account_id: str,
    operation: str,
    envelope_id: Optional[str],
    params: Optional[Dict[str, Any]],
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    base_url = f"https://demo.docusign.net/restapi/v2.1/accounts/{account_id}"
    
    if operation == "get_envelope" and envelope_id:
        url = f"{base_url}/envelopes/{envelope_id}"
    elif operation == "list_envelopes":
        url = f"{base_url}/envelopes"
    elif operation == "create_envelope":
        url = f"{base_url}/envelopes"
    elif operation == "list_templates":
        url = f"{base_url}/templates"
    elif operation == "get_template" and envelope_id:  # reuse envelope_id for template_id
        url = f"{base_url}/templates/{envelope_id}"
    elif operation == "download_document" and envelope_id:
        url = f"{base_url}/envelopes/{envelope_id}/documents/combined"
    else:
        url = f"{base_url}/{operation}"

    method = "POST" if operation == "create_envelope" else "GET"

    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "Bearer token",
    }
    if params:
        preview["params"] = params
    if payload:
        preview["payload"] = payload
    return preview


def main(
    *,
    operation: str = "list_envelopes",
    envelope_id: str = "",
    template_id: str = "",
    status: str = "sent",
    from_date: str = "",
    email_subject: str = "",
    email_body: str = "",
    recipient_email: str = "",
    recipient_name: str = "",
    document_base64: str = "",
    document_name: str = "document.pdf",
    DOCUSIGN_ACCESS_TOKEN: str = "",
    DOCUSIGN_ACCOUNT_ID: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Manage DocuSign envelopes, documents, and templates.
    
    Operations:
    - list_envelopes: List envelopes with optional filters
    - get_envelope: Get envelope details by ID
    - create_envelope: Create and send a new envelope
    - list_templates: List available templates
    - get_template: Get template details by ID
    - download_document: Download envelope documents
    """

    normalized_operation = operation.lower()
    valid_operations = {
        "list_envelopes",
        "get_envelope",
        "create_envelope",
        "list_templates",
        "get_template",
        "download_document",
    }
    
    if normalized_operation not in valid_operations:
        return validation_error("Unsupported operation", field="operation")

    if not DOCUSIGN_ACCESS_TOKEN:
        return error_output(
            "Missing DOCUSIGN_ACCESS_TOKEN",
            status_code=401,
            details="Provide an OAuth access token for DocuSign API",
        )

    if not DOCUSIGN_ACCOUNT_ID:
        return error_output(
            "Missing DOCUSIGN_ACCOUNT_ID",
            status_code=401,
            details="Provide your DocuSign account ID",
        )

    api_client = client or _DEFAULT_CLIENT

    base_url = f"https://demo.docusign.net/restapi/v2.1/accounts/{DOCUSIGN_ACCOUNT_ID}"
    headers = {
        "Authorization": f"Bearer {DOCUSIGN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None
    resource_id = envelope_id or template_id

    if normalized_operation == "list_envelopes":
        params = {}
        if status:
            params["status"] = status
        if from_date:
            params["from_date"] = from_date
    elif normalized_operation == "get_envelope":
        if not envelope_id:
            return validation_error("Missing required envelope_id", field="envelope_id")
    elif normalized_operation == "create_envelope":
        if not email_subject:
            return validation_error("Missing required email_subject", field="email_subject")
        if not recipient_email:
            return validation_error("Missing required recipient_email", field="recipient_email")
        if not recipient_name:
            return validation_error("Missing required recipient_name", field="recipient_name")
        
        payload = {
            "emailSubject": email_subject,
            "status": "sent",
            "recipients": {
                "signers": [
                    {
                        "email": recipient_email,
                        "name": recipient_name,
                        "recipientId": "1",
                    }
                ]
            },
        }
        
        if document_base64:
            payload["documents"] = [
                {
                    "documentBase64": document_base64,
                    "name": document_name,
                    "fileExtension": "pdf",
                    "documentId": "1",
                }
            ]
        
        if email_body:
            payload["emailBlurb"] = email_body
    elif normalized_operation == "get_template":
        if not template_id:
            return validation_error("Missing required template_id", field="template_id")
    elif normalized_operation == "download_document":
        if not envelope_id:
            return validation_error("Missing required envelope_id", field="envelope_id")

    if dry_run:
        preview = _build_preview(
            account_id=DOCUSIGN_ACCOUNT_ID,
            operation=normalized_operation,
            envelope_id=resource_id,
            params=params,
            payload=payload,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    # Build URL
    if normalized_operation == "get_envelope":
        url = f"{base_url}/envelopes/{envelope_id}"
    elif normalized_operation == "list_envelopes":
        url = f"{base_url}/envelopes"
    elif normalized_operation == "create_envelope":
        url = f"{base_url}/envelopes"
    elif normalized_operation == "list_templates":
        url = f"{base_url}/templates"
    elif normalized_operation == "get_template":
        url = f"{base_url}/templates/{template_id}"
    elif normalized_operation == "download_document":
        url = f"{base_url}/envelopes/{envelope_id}/documents/combined"
    else:
        url = f"{base_url}/{normalized_operation}"

    try:
        if normalized_operation == "create_envelope":
            response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
        else:
            response = api_client.get(url, headers=headers, params=params, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("DocuSign request failed", status_code=status, details=str(exc))

    try:
        data = response.json()
    except ValueError:
        return error_output(
            "Invalid JSON response",
            status_code=getattr(response, "status_code", None),
            details=getattr(response, "text", None),
        )

    if not getattr(response, "ok", False):
        error_msg = data.get("message", "DocuSign API error")
        if isinstance(data, dict) and "errorCode" in data:
            error_msg = f"{data.get('errorCode')}: {error_msg}"
        return error_output(error_msg, status_code=response.status_code, response=data)

    return {"output": data}
