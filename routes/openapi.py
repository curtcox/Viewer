"""Routes that expose the application's OpenAPI schema and Swagger UI."""
from __future__ import annotations

from typing import Any, Dict

from flask import Response, jsonify, render_template, request, url_for

from . import main_bp


def _interaction_request_schema() -> Dict[str, Any]:
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


def _interaction_summary_schema() -> Dict[str, Any]:
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


def _interaction_history_schema() -> Dict[str, Any]:
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


def _error_schema() -> Dict[str, Any]:
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


def _build_openapi_spec() -> Dict[str, Any]:
    """Assemble the OpenAPI schema for the application."""

    server_url = request.host_url.rstrip("/")
    spec: Dict[str, Any] = {
        "openapi": "3.0.3",
        "info": {
            "title": "Viewer API",
            "version": "1.0.0",
            "description": "Programmatic interface for recording entity interactions.",
            "contact": {
                "name": "Viewer Project",
                "url": request.url_root.rstrip("/"),
            },
        },
        "servers": [{"url": server_url}],
        "paths": {
            "/api/interactions": {
                "post": {
                    "tags": ["Interactions"],
                    "summary": "Record entity interaction",
                    "operationId": "createInteraction",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/InteractionRequest"},
                                "examples": {
                                    "interaction": {
                                        "summary": "Record AI assistance for a server",
                                        "value": {
                                            "entity_type": "server",
                                            "entity_name": "example",
                                            "action": "ai",
                                            "message": "Trim trailing spaces",
                                            "content": "print(\"hello world\")",
                                        },
                                    }
                                },
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Interaction persisted and history returned.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/InteractionHistory"},
                                }
                            },
                        },
                        "400": {
                            "description": "Invalid input provided.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"},
                                }
                            },
                        },
                    },
                }
            }
        },
        "components": {
            "schemas": {
                "InteractionRequest": _interaction_request_schema(),
                "InteractionSummary": _interaction_summary_schema(),
                "InteractionHistory": _interaction_history_schema(),
                "Error": _error_schema(),
            }
        },
    }

    return spec


@main_bp.route("/openapi.json")
def openapi_spec() -> Response:
    """Return the OpenAPI specification describing the HTTP API."""

    return jsonify(_build_openapi_spec())


@main_bp.route("/openapi")
def openapi_docs() -> str:
    """Render an interactive Swagger UI configured for the app's schema."""

    spec_url = url_for("main.openapi_spec", _external=False)
    return render_template("swagger.html", title="API Explorer", spec_url=spec_url)


__all__ = ["openapi_spec", "openapi_docs"]
