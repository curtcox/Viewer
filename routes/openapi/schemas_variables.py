"""OpenAPI schemas for variable management endpoints."""
from __future__ import annotations

from typing import Any, Dict


def variable_record_schema() -> Dict[str, Any]:
    """Schema describing a variable record."""

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
                "description": "Variable name",
                "example": "api_token",
            },
            "definition": {
                "type": "string",
                "description": "Variable definition value.",
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
            "enabled": {"type": "boolean", "description": "Whether the variable is active."},
        },
        "additionalProperties": False,
    }


def variable_form_schema() -> Dict[str, Any]:
    """Schema for variable create/edit submissions."""

    return {
        "type": "object",
        "required": ["name", "definition"],
        "properties": {
            "name": {
                "type": "string",
                "description": "Unique variable name.",
                "example": "api_token",
            },
            "definition": {
                "type": "string",
                "description": "Variable content or serialized value.",
                "example": "token-123",
            },
            "enabled": {
                "type": "boolean",
                "description": "Whether the variable is active.",
            },
            "change_message": {
                "type": "string",
                "description": "Optional note captured with the change history entry.",
            },
        },
        "additionalProperties": True,
    }


def variables_bulk_edit_form_schema() -> Dict[str, Any]:
    """Schema for bulk variable JSON submissions."""

    return {
        "type": "object",
        "required": ["variables_json"],
        "properties": {
            "variables_json": {
                "type": "string",
                "description": "JSON object mapping variable names to their values.",
                "example": '{"region": "us-east", "city": "Boston"}',
            },
            "submit": {
                "type": "string",
                "description": "Label of the submit button invoked by the browser.",
            },
        },
        "additionalProperties": True,
    }


__all__ = [
    "variable_record_schema",
    "variable_form_schema",
    "variables_bulk_edit_form_schema",
]
