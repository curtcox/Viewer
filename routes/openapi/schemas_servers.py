"""OpenAPI schemas for server management endpoints."""
from __future__ import annotations

from typing import Any, Dict


def server_record_schema() -> Dict[str, Any]:
    """Schema describing a server record."""

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
                "description": "Server name",
                "example": "echo",
            },
            "definition": {
                "type": "string",
                "description": "Python source code defining the server.",
            },
            "definition_cid": {
                "type": ["string", "null"],
                "description": "CID referencing the stored definition, when available.",
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
            "enabled": {"type": "boolean", "description": "Whether the server is active."},
        },
        "additionalProperties": False,
    }


def server_form_schema() -> Dict[str, Any]:
    """Schema for server create/edit submissions."""

    return {
        "type": "object",
        "required": ["name", "definition"],
        "properties": {
            "name": {
                "type": "string",
                "description": "Unique server name.",
                "example": "echo",
            },
            "definition": {
                "type": "string",
                "description": "Python source code defining the server.",
                "example": "def main(query):\n    return query",
            },
            "enabled": {
                "type": "boolean",
                "description": "Whether the server is active.",
            },
            "submit_action": {
                "type": "string",
                "description": "Optional alternate submission action such as save-as.",
                "example": "save-as",
            },
            "change_message": {
                "type": "string",
                "description": "Optional note recorded with the change history entry.",
            },
        },
        "additionalProperties": True,
    }


def server_definition_analysis_schema() -> Dict[str, Any]:
    """Schema for the server definition analysis endpoint."""

    return {
        "type": "object",
        "required": [
            "is_valid",
            "errors",
            "auto_main",
            "auto_main_errors",
            "parameters",
            "has_main",
            "mode",
        ],
        "properties": {
            "is_valid": {"type": "boolean"},
            "errors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "line": {"type": "integer"},
                        "column": {"type": "integer"},
                        "text": {"type": "string"},
                    },
                },
            },
            "auto_main": {"type": "boolean"},
            "auto_main_errors": {
                "type": "array",
                "items": {"type": "string"},
            },
            "parameters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "required": {"type": "boolean"},
                    },
                },
            },
            "has_main": {"type": "boolean"},
            "mode": {"type": "string", "example": "query"},
        },
    }


def server_test_upload_response_schema() -> Dict[str, Any]:
    """Schema describing the payload returned when uploading server test pages."""

    return {
        "type": "object",
        "required": ["redirect_url", "cid"],
        "properties": {
            "redirect_url": {
                "type": "string",
                "format": "uri",
                "description": "URL that renders the generated Formdown document.",
            },
            "cid": {
                "type": "string",
                "description": "Content identifier associated with the uploaded page.",
                "example": "bafybeigdyrzt",
            },
        },
    }


__all__ = [
    "server_record_schema",
    "server_form_schema",
    "server_definition_analysis_schema",
    "server_test_upload_response_schema",
]
