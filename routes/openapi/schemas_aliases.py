"""OpenAPI schemas for alias management endpoints."""
from __future__ import annotations

from typing import Any, Dict


def alias_record_schema() -> Dict[str, Any]:
    """Schema describing an alias record."""

    return {
        "type": "object",
        "required": [
            "id",
            "name",
            "enabled",
            "match_type",
            "match_pattern",
            "ignore_case",
        ],
        "properties": {
            "id": {"type": "integer", "format": "int64", "example": 1},
            "name": {
                "type": "string",
                "description": "Alias name",
                "example": "docs",
            },
            "definition": {
                "type": ["string", "null"],
                "description": "Stored alias definition text.",
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
            "enabled": {"type": "boolean", "description": "Whether the alias is active."},
            "match_type": {
                "type": "string",
                "description": "Primary route match type.",
                "example": "literal",
            },
            "match_pattern": {
                "type": "string",
                "description": "Pattern matched by the primary alias rule.",
                "example": "/docs",
            },
            "target_path": {
                "type": ["string", "null"],
                "description": "Primary target path resolved by the alias.",
                "example": "/documentation",
            },
            "ignore_case": {
                "type": "boolean",
                "description": "Whether the alias ignores case when matching.",
            },
        },
        "additionalProperties": False,
    }


def alias_form_schema() -> Dict[str, Any]:
    """Schema for alias create/edit submissions."""

    return {
        "type": "object",
        "required": ["name"],
        "properties": {
            "name": {
                "type": "string",
                "description": "Unique path-friendly name for the alias.",
                "example": "docs",
            },
            "definition": {
                "type": "string",
                "description": "Primary alias definition text.",
                "example": "docs -> /documentation",
            },
            "enabled": {
                "type": "boolean",
                "description": "When true the alias actively routes traffic.",
            },
            "submit_action": {
                "type": "string",
                "description": "Optional control for alternate save actions such as Save As.",
                "example": "save-as",
            },
            "change_message": {
                "type": "string",
                "description": "Optional note stored alongside the change history entry.",
            },
        },
        "additionalProperties": True,
    }


def alias_enabled_update_schema() -> Dict[str, Any]:
    """Schema describing alias enabled state updates."""

    return {
        "type": "object",
        "required": ["enabled"],
        "properties": {
            "enabled": {
                "type": "boolean",
                "description": "Whether the alias should be active after the update.",
            }
        },
        "additionalProperties": False,
    }


def alias_match_preview_request_schema() -> Dict[str, Any]:
    """Schema describing the alias matcher preview request body."""

    return {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Alias name under construction.",
                "example": "docs",
            },
            "definition": {
                "type": "string",
                "description": "Candidate alias definition text.",
                "example": "docs -> /documentation",
            },
            "paths": {
                "type": "array",
                "description": "Paths to evaluate against the alias definition.",
                "items": {
                    "type": "string",
                    "example": "/docs/api",
                },
            },
        },
        "additionalProperties": False,
    }


def alias_match_preview_response_schema() -> Dict[str, Any]:
    """Schema describing the alias matcher preview response."""

    return {
        "type": "object",
        "required": ["ok", "results", "definition"],
        "properties": {
            "ok": {
                "type": "boolean",
                "description": "Indicates whether the definition parsed successfully.",
            },
            "pattern": {
                "type": "string",
                "description": "Primary match pattern derived from the definition.",
                "example": "/docs/*",
            },
            "results": {
                "type": "array",
                "description": "Evaluation results for each supplied path.",
                "items": {
                    "type": "object",
                    "required": ["value", "matches"],
                    "properties": {
                        "value": {
                            "type": "string",
                            "example": "/docs/api",
                        },
                        "matches": {
                            "type": "boolean",
                        },
                    },
                },
            },
            "definition": {
                "type": "object",
                "properties": {
                    "has_active_paths": {
                        "type": "boolean",
                    },
                    "lines": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "number": {"type": "integer"},
                                "text": {"type": "string"},
                                "is_mapping": {"type": "boolean"},
                                "matches_any": {"type": "boolean"},
                                "has_error": {"type": "boolean"},
                                "parse_error": {"type": ["string", "null"]},
                            },
                        },
                    },
                },
            },
            "error": {
                "type": "string",
                "description": "Present when parsing fails.",
            },
        },
    }


__all__ = [
    "alias_record_schema",
    "alias_form_schema",
    "alias_enabled_update_schema",
    "alias_match_preview_request_schema",
    "alias_match_preview_response_schema",
]
