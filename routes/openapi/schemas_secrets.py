"""OpenAPI schemas for secret management endpoints."""

from __future__ import annotations

from typing import Any, Dict


def secret_record_schema() -> Dict[str, Any]:
    """Schema describing a secret record."""

    return {
        "type": "object",
        "required": [
            "id",
            "name",
            "definition",
            "created_at",
            "updated_at",
            "enabled",
        ],
        "properties": {
            "id": {"type": "integer", "format": "int64", "example": 1},
            "name": {
                "type": "string",
                "description": "Secret name",
                "example": "service-password",
            },
            "definition": {
                "type": "string",
                "description": "Secret definition value.",
            },
            "created_at": {
                "type": "string",
                "format": "date-time",
                "description": "Creation timestamp in ISO-8601 format.",
            },
            "updated_at": {
                "type": "string",
                "format": "date-time",
                "description": "Last update timestamp in ISO-8601 format.",
            },
            "enabled": {
                "type": "boolean",
                "description": "Whether the secret is active.",
            },
        },
        "additionalProperties": False,
    }


def secret_form_schema() -> Dict[str, Any]:
    """Schema for secret create/edit submissions."""

    return {
        "type": "object",
        "required": ["name", "definition"],
        "properties": {
            "name": {
                "type": "string",
                "description": "Unique secret name.",
                "example": "service-password",
            },
            "definition": {
                "type": "string",
                "description": "Secret value or serialized content.",
                "example": "p@ssw0rd",
            },
            "enabled": {
                "type": "boolean",
                "description": "Whether the secret is active.",
            },
            "change_message": {
                "type": "string",
                "description": "Optional note stored with the change history entry.",
            },
        },
        "additionalProperties": True,
    }


def secrets_bulk_edit_form_schema() -> Dict[str, Any]:
    """Schema for bulk secret JSON submissions."""

    return {
        "type": "object",
        "required": ["secrets_json"],
        "properties": {
            "secrets_json": {
                "type": "string",
                "description": "JSON object mapping secret names to their values.",
                "example": '{"api_key": "rotate-me", "db_password": "hunter2"}',
            },
            "submit": {
                "type": "string",
                "description": "Label of the submit button invoked by the browser.",
            },
        },
        "additionalProperties": True,
    }


__all__ = [
    "secret_record_schema",
    "secret_form_schema",
    "secrets_bulk_edit_form_schema",
]
