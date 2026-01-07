# ruff: noqa: F821, F706
"""Interact with DocuSign to manage envelopes, documents, and templates."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

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


_ENDPOINT_MAP = {
    "list_envelopes": "envelopes",
    "get_envelope": "envelopes/{envelope_id}",
    "create_envelope": "envelopes",
    "list_templates": "templates",
    "get_template": "templates/{template_id}",
    "download_document": "envelopes/{envelope_id}/documents/combined",
}


_OPERATIONS = {
    "list_envelopes": OperationDefinition(
        payload_builder=lambda status, from_date, **_: {
            "method": "GET",
            "params": {
                **({} if not status else {"status": status}),
                **({} if not from_date else {"from_date": from_date}),
            } or None,
            "payload": None,
            "envelope_id": None,
            "template_id": None,
        },
    ),
    "get_envelope": OperationDefinition(
        required=(RequiredField("envelope_id"),),
        payload_builder=lambda envelope_id, **_: {
            "method": "GET",
            "params": None,
            "payload": None,
            "envelope_id": envelope_id,
            "template_id": None,
        },
    ),
    "create_envelope": OperationDefinition(
        required=(
            RequiredField("email_subject"),
            RequiredField("recipient_email"),
            RequiredField("recipient_name"),
        ),
        payload_builder=lambda email_subject, recipient_email, recipient_name, email_body, document_base64, document_name, **_: {
            "method": "POST",
            "params": None,
            "payload": {
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
                **({} if not document_base64 else {
                    "documents": [{
                        "documentBase64": document_base64,
                        "name": document_name,
                        "fileExtension": "pdf",
                        "documentId": "1",
                    }]
                }),
                **({} if not email_body else {"emailBlurb": email_body}),
            },
            "envelope_id": None,
            "template_id": None,
        },
    ),
    "list_templates": OperationDefinition(
        payload_builder=lambda **_: {
            "method": "GET",
            "params": None,
            "payload": None,
            "envelope_id": None,
            "template_id": None,
        },
    ),
    "get_template": OperationDefinition(
        required=(RequiredField("template_id"),),
        payload_builder=lambda template_id, **_: {
            "method": "GET",
            "params": None,
            "payload": None,
            "envelope_id": None,
            "template_id": template_id,
        },
    ),
    "download_document": OperationDefinition(
        required=(RequiredField("envelope_id"),),
        payload_builder=lambda envelope_id, **_: {
            "method": "GET",
            "params": None,
            "payload": None,
            "envelope_id": envelope_id,
            "template_id": None,
        },
    ),
}


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

    # Validate credentials
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

    # Validate operation
    normalized_operation = operation.lower()
    if normalized_operation not in _OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    # Validate and build request configuration
    result = validate_and_build_payload(
        normalized_operation,
        _OPERATIONS,
        envelope_id=envelope_id,
        template_id=template_id,
        status=status,
        from_date=from_date,
        email_subject=email_subject,
        email_body=email_body,
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        document_base64=document_base64,
        document_name=document_name,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    # Extract request configuration
    method = result["method"]
    params = result["params"]
    payload = result["payload"]
    envelope_id_param = result["envelope_id"]
    template_id_param = result["template_id"]

    # Build URL
    base_url = f"https://demo.docusign.net/restapi/v2.1/accounts/{DOCUSIGN_ACCOUNT_ID}"
    endpoint = _ENDPOINT_MAP[normalized_operation]
    url = f"{base_url}/{endpoint}"

    # Replace placeholders in URL
    if envelope_id_param:
        url = url.replace("{envelope_id}", envelope_id_param)
    if template_id_param:
        url = url.replace("{template_id}", template_id_param)

    # Dry run preview
    if dry_run:
        preview: Dict[str, Any] = {
            "operation": normalized_operation,
            "url": url,
            "method": method,
            "auth": "Bearer token",
        }
        if params:
            preview["params"] = params
        if payload:
            preview["payload"] = payload
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    # Build headers
    headers = {
        "Authorization": f"Bearer {DOCUSIGN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # Execute request
    api_client = client or _DEFAULT_CLIENT
    return execute_json_request(
        api_client,
        method,
        url,
        headers=headers,
        json=payload,
        params=params,
        timeout=timeout,
        error_key="message",
    )
