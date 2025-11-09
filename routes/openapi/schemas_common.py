"""Common OpenAPI schemas used across multiple endpoints."""
from __future__ import annotations

from typing import Any, Dict


def error_schema() -> Dict[str, Any]:
    """Describe simple error payloads."""

    return {
        "type": "object",
        "required": ["error"],
        "properties": {
            "error": {
                "type": "string",
                "description": "Explanation of why the request failed.",
                "example": "Entity details are required.",
            }
        },
    }


def deletion_form_schema() -> Dict[str, Any]:
    """Schema for delete confirmation submissions."""

    return {
        "type": "object",
        "properties": {
            "confirm": {
                "type": "string",
                "description": "Optional confirmation field used by UI flows.",
            },
        },
        "additionalProperties": True,
    }


def upload_form_schema() -> Dict[str, Any]:
    """Schema describing the CID upload form fields."""

    return {
        "type": "object",
        "required": ["upload_type"],
        "properties": {
            "upload_type": {
                "type": "string",
                "description": "Selected upload mode (file, text, or url).",
                "enum": ["file", "text", "url"],
            },
            "file": {
                "type": "string",
                "format": "binary",
                "description": "File contents when using file upload.",
            },
            "text_content": {
                "type": "string",
                "description": "Raw text content when using text upload.",
            },
            "url": {
                "type": "string",
                "format": "uri",
                "description": "Source URL when requesting remote fetch.",
            },
        },
        "additionalProperties": True,
    }


__all__ = ["error_schema", "deletion_form_schema", "upload_form_schema"]
