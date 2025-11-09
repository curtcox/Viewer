"""OpenAPI schemas for interaction tracking endpoints."""
from __future__ import annotations

from typing import Any, Dict


def interaction_request_schema() -> Dict[str, Any]:
    """Describe the payload accepted by the interactions endpoint."""

    return {
        "type": "object",
        "required": ["entity_type", "entity_name"],
        "properties": {
            "entity_type": {
                "type": "string",
                "description": "Entity category such as 'server' or 'alias'.",
                "example": "server",
            },
            "entity_name": {
                "type": "string",
                "description": "Specific entity identifier scoped to the current user.",
                "example": "example-server",
            },
            "action": {
                "type": "string",
                "description": "Type of interaction being recorded.",
                "default": "ai",
                "example": "ai",
            },
            "message": {
                "type": ["string", "null"],
                "description": "Optional free-form description of the interaction.",
                "example": "Requested AI assistance",
            },
            "content": {
                "type": "string",
                "description": "Associated content such as prompt or code snippets.",
                "example": "print(\"hello world\")",
            },
        },
        "additionalProperties": False,
    }


def interaction_summary_schema() -> Dict[str, Any]:
    """Describe the stored representation returned to clients."""

    return {
        "type": "object",
        "required": [
            "id",
            "action",
            "action_display",
            "timestamp",
            "timestamp_iso",
            "message",
            "preview",
            "content",
        ],
        "properties": {
            "id": {
                "type": "integer",
                "format": "int64",
                "description": "Database identifier for the interaction.",
                "example": 42,
            },
            "action": {
                "type": "string",
                "description": "Canonical lowercase action name.",
                "example": "ai",
            },
            "action_display": {
                "type": "string",
                "description": "Human-friendly label for the action.",
                "example": "AI",
            },
            "timestamp": {
                "type": "string",
                "description": "Display-ready timestamp in UTC.",
                "example": "2024-05-01 12:30 UTC",
            },
            "timestamp_iso": {
                "type": "string",
                "description": "ISO-8601 timestamp.",
                "example": "2024-05-01T12:30:00+00:00",
            },
            "message": {
                "type": "string",
                "description": "Original message stored with the interaction.",
                "example": "Requested AI assistance",
            },
            "preview": {
                "type": "string",
                "description": "Truncated preview of the message for listings.",
                "example": "Requested AI assistance",
            },
            "content": {
                "type": "string",
                "description": "Stored content payload.",
                "example": "print(\"hello world\")",
            },
        },
    }


def interaction_history_schema() -> Dict[str, Any]:
    """Describe the shape returned from the interactions endpoint."""

    return {
        "type": "object",
        "required": ["interaction", "interactions"],
        "properties": {
            "interaction": {
                "oneOf": [
                    {"$ref": "#/components/schemas/InteractionSummary"},
                    {"type": "null"},
                ],
                "description": "Summary of the newly recorded interaction.",
            },
            "interactions": {
                "type": "array",
                "description": "Recent interaction history for the entity, newest first.",
                "items": {"$ref": "#/components/schemas/InteractionSummary"},
            },
        },
    }


__all__ = [
    "interaction_request_schema",
    "interaction_summary_schema",
    "interaction_history_schema",
]
