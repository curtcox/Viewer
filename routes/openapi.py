"""Routes that expose the application's OpenAPI schema and Swagger UI."""
from __future__ import annotations

import re
from typing import Any, Dict, Set
from urllib.parse import urlsplit, urlunsplit

from flask import Flask, Response, jsonify, render_template, request, url_for

from . import main_bp


_PATH_PARAMETER_PATTERN = re.compile(r"{([^}/]+)}")


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


def _html_response(description: str) -> Dict[str, Any]:
    """Describe responses that originate as HTML but support multiple formats."""

    content = _string_media_content()
    content["application/json"] = {
        "schema": {
            "type": "object",
            "required": ["content", "content_type"],
            "properties": {
                "content": {"type": "string"},
                "content_type": {
                    "type": "string",
                    "enum": ["text/html"],
                    "description": "Original media type of the rendered response.",
                },
            },
        }
    }

    return {"description": description, "content": content}


def _string_media_content() -> Dict[str, Any]:
    """Return content descriptors for string-based representations."""

    return {
        "text/html": {"schema": {"type": "string"}},
        "text/plain": {"schema": {"type": "string"}},
        "text/markdown": {"schema": {"type": "string"}},
        "application/xml": {"schema": {"type": "string"}},
        "text/csv": {"schema": {"type": "string"}},
    }


def _entity_collection_response(description: str, schema_ref: str) -> Dict[str, Any]:
    content = _string_media_content()
    content["application/json"] = {
        "schema": {
            "type": "array",
            "items": {"$ref": schema_ref},
        }
    }
    return {"description": description, "content": content}


def _entity_resource_response(description: str, schema_ref: str) -> Dict[str, Any]:
    content = _string_media_content()
    content["application/json"] = {"schema": {"$ref": schema_ref}}
    return {"description": description, "content": content}


def _augment_json_content(paths: Dict[str, Any]) -> None:
    """Ensure JSON responses advertise alternative representations."""

    for path_item in paths.values():
        if not isinstance(path_item, dict):
            continue
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            responses = operation.get("responses", {})
            for response in responses.values():
                content = response.get("content")
                if not isinstance(content, dict):
                    continue
                if "application/json" not in content:
                    continue
                for mimetype, descriptor in _string_media_content().items():
                    content.setdefault(mimetype, descriptor)


def _convert_path_to_rule(path: str) -> str:
    """Translate an OpenAPI path template to a Flask routing rule."""

    return _PATH_PARAMETER_PATTERN.sub(lambda match: f"<{match.group(1)}>", path)


def _redirect_response(description: str) -> Dict[str, Any]:
    """Metadata for routes that redirect after processing."""

    return {
        "description": description,
        "headers": {
            "Location": {
                "description": "Destination URL for the redirect.",
                "schema": {
                    "type": "string",
                    "format": "uri",
                },
            }
        },
    }


def _form_request_body(schema_name: str) -> Dict[str, Any]:
    """Describe an x-www-form-urlencoded request body referencing a schema."""

    return {
        "required": True,
        "content": {
            "application/x-www-form-urlencoded": {
                "schema": {"$ref": f"#/components/schemas/{schema_name}"}
            }
        },
    }


def _multipart_request_body(schema_name: str) -> Dict[str, Any]:
    """Describe a multipart/form-data request body referencing a schema."""

    return {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {"$ref": f"#/components/schemas/{schema_name}"}
            }
        },
    }


def _path_parameter(name: str, description: str) -> Dict[str, Any]:
    """Return a reusable path parameter description."""

    return {
        "name": name,
        "in": "path",
        "required": True,
        "description": description,
        "schema": {"type": "string"},
    }


def _alias_record_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "required": [
            "id",
            "name",
            "user_id",
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
            "user_id": {
                "type": "string",
                "description": "Owner identifier",
                "example": "default-user",
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


def _server_record_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "required": [
            "id",
            "name",
            "definition",
            "user_id",
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
            "user_id": {
                "type": "string",
                "description": "Owner identifier",
                "example": "default-user",
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


def _variable_record_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "required": [
            "id",
            "name",
            "definition",
            "user_id",
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
            "user_id": {
                "type": "string",
                "description": "Owner identifier",
                "example": "default-user",
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


def _secret_record_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "required": [
            "id",
            "name",
            "definition",
            "user_id",
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
            "user_id": {
                "type": "string",
                "description": "Owner identifier",
                "example": "default-user",
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
            "enabled": {"type": "boolean", "description": "Whether the secret is active."},
        },
        "additionalProperties": False,
    }


def _alias_form_schema() -> Dict[str, Any]:
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


def _server_form_schema() -> Dict[str, Any]:
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


def _variable_form_schema() -> Dict[str, Any]:
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


def _variables_bulk_edit_form_schema() -> Dict[str, Any]:
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


def _secret_form_schema() -> Dict[str, Any]:
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


def _deletion_form_schema() -> Dict[str, Any]:
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


def _alias_match_preview_request_schema() -> Dict[str, Any]:
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


def _alias_match_preview_response_schema() -> Dict[str, Any]:
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


def _server_definition_analysis_schema() -> Dict[str, Any]:
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


def _server_test_upload_response_schema() -> Dict[str, Any]:
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


def _upload_form_schema() -> Dict[str, Any]:
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


def _build_openapi_spec() -> Dict[str, Any]:
    """Assemble the OpenAPI schema for the application."""

    server_url = request.host_url.rstrip("/")
    parsed = urlsplit(server_url)
    hostname = parsed.hostname or ""
    port = parsed.port
    if hostname and (port in (None, 80, 443) or (hostname == "localhost" and port == 5000)):
        netloc = hostname
    else:
        netloc = parsed.netloc
    server_url = urlunsplit((parsed.scheme, netloc, "", "", ""))
    paths: Dict[str, Any] = {
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
        },
        "/aliases": {
            "get": {
                "tags": ["Aliases"],
                "summary": "List aliases",
                "description": "Render the HTML workspace page that lists the current user's aliases.",
                "responses": {
                    "200": _entity_collection_response(
                        "Aliases listing rendered.",
                        "#/components/schemas/AliasRecord",
                    )
                },
            }
        },
        "/aliases/new": {
            "get": {
                "tags": ["Aliases"],
                "summary": "Show alias creation form",
                "responses": {"200": _html_response("Alias creation form rendered.")},
            },
            "post": {
                "tags": ["Aliases"],
                "summary": "Create alias",
                "requestBody": _form_request_body("AliasFormSubmission"),
                "responses": {
                    "302": _redirect_response("Alias created and browser redirected."),
                    "200": _html_response("Form re-rendered with validation errors."),
                },
            },
        },
        "/aliases/{alias_name}": {
            "parameters": [_path_parameter("alias_name", "Alias name to view.")],
            "get": {
                "tags": ["Aliases"],
                "summary": "View alias",
                "responses": {
                    "200": _entity_resource_response(
                        "Alias details rendered.",
                        "#/components/schemas/AliasRecord",
                    )
                },
            },
        },
        "/aliases/{alias_name}/edit": {
            "parameters": [_path_parameter("alias_name", "Alias name to update.")],
            "get": {
                "tags": ["Aliases"],
                "summary": "Show alias edit form",
                "responses": {"200": _html_response("Alias edit form rendered.")},
            },
            "post": {
                "tags": ["Aliases"],
                "summary": "Update alias",
                "requestBody": _form_request_body("AliasFormSubmission"),
                "responses": {
                    "302": _redirect_response("Alias updated and browser redirected."),
                    "200": _html_response("Form re-rendered with validation errors."),
                },
            },
        },
        "/aliases/{alias_name}/delete": {
            "parameters": [_path_parameter("alias_name", "Alias name to delete.")],
            "post": {
                "tags": ["Aliases"],
                "summary": "Delete alias",
                "requestBody": _form_request_body("DeletionConfirmation"),
                "responses": {
                    "302": _redirect_response("Alias deleted and browser redirected."),
                    "404": _html_response("Alias not found."),
                },
            },
        },
        "/aliases/match-preview": {
            "post": {
                "tags": ["Aliases"],
                "summary": "Preview alias matches",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/AliasMatchPreviewRequest"}
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Alias match evaluation results.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/AliasMatchPreviewResponse"}
                            }
                        },
                    },
                    "400": {
                        "description": "Validation failure while parsing the alias definition.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"},
                            }
                        },
                    },
                    "401": {
                        "description": "Authentication required to preview alias matches.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            }
        },
        "/servers": {
            "get": {
                "tags": ["Servers"],
                "summary": "List servers",
                "responses": {
                    "200": _entity_collection_response(
                        "Servers listing rendered.",
                        "#/components/schemas/ServerRecord",
                    )
                },
            }
        },
        "/servers/new": {
            "get": {
                "tags": ["Servers"],
                "summary": "Show server creation form",
                "responses": {"200": _html_response("Server creation form rendered.")},
            },
            "post": {
                "tags": ["Servers"],
                "summary": "Create server",
                "requestBody": _form_request_body("ServerFormSubmission"),
                "responses": {
                    "302": _redirect_response("Server created and browser redirected."),
                    "200": _html_response("Form re-rendered with validation errors."),
                },
            },
        },
        "/servers/{server_name}": {
            "parameters": [_path_parameter("server_name", "Server name to view.")],
            "get": {
                "tags": ["Servers"],
                "summary": "View server",
                "responses": {
                    "200": _entity_resource_response(
                        "Server details rendered.",
                        "#/components/schemas/ServerRecord",
                    )
                },
            },
        },
        "/servers/{server_name}/edit": {
            "parameters": [_path_parameter("server_name", "Server name to update.")],
            "get": {
                "tags": ["Servers"],
                "summary": "Show server edit form",
                "responses": {"200": _html_response("Server edit form rendered.")},
            },
            "post": {
                "tags": ["Servers"],
                "summary": "Update server",
                "requestBody": _form_request_body("ServerFormSubmission"),
                "responses": {
                    "302": _redirect_response("Server updated and browser redirected."),
                    "200": _html_response("Form re-rendered with validation errors."),
                },
            },
        },
        "/servers/{server_name}/delete": {
            "parameters": [_path_parameter("server_name", "Server name to delete.")],
            "post": {
                "tags": ["Servers"],
                "summary": "Delete server",
                "requestBody": _form_request_body("DeletionConfirmation"),
                "responses": {
                    "302": _redirect_response("Server deleted and browser redirected."),
                    "404": _html_response("Server not found."),
                },
            },
        },
        "/servers/validate-definition": {
            "post": {
                "tags": ["Servers"],
                "summary": "Validate server definition",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["definition"],
                                "properties": {
                                    "definition": {
                                        "type": "string",
                                        "description": "Server definition to analyze.",
                                    }
                                },
                                "additionalProperties": False,
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Analysis results describing auto-main compatibility.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ServerDefinitionAnalysis"}
                            }
                        },
                    },
                    "400": {
                        "description": "Payload was not JSON or missing a definition field.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"},
                            }
                        },
                    },
                },
            }
        },
        "/servers/{server_name}/upload-test-page": {
            "parameters": [_path_parameter("server_name", "Server name supplying the test form.")],
            "post": {
                "tags": ["Servers"],
                "summary": "Upload server test page",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "values": {
                                        "type": "object",
                                        "description": "Default values used to pre-populate the generated form.",
                                        "additionalProperties": {"type": ["string", "number", "boolean", "null"]},
                                    }
                                },
                                "additionalProperties": False,
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Generated Formdown document persisted as a CID-backed upload.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ServerTestUploadResponse"}
                            }
                        },
                    },
                    "400": {
                        "description": "Validation failure while creating the upload.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"},
                            }
                        },
                    },
                    "404": _html_response("Server or test configuration not available."),
                },
            },
        },
        "/variables": {
            "get": {
                "tags": ["Variables"],
                "summary": "List variables",
                "responses": {
                    "200": _entity_collection_response(
                        "Variables listing rendered.",
                        "#/components/schemas/VariableRecord",
                    )
                },
            }
        },
        "/variables/new": {
            "get": {
                "tags": ["Variables"],
                "summary": "Show variable creation form",
                "responses": {"200": _html_response("Variable creation form rendered.")},
            },
            "post": {
                "tags": ["Variables"],
                "summary": "Create variable",
                "requestBody": _form_request_body("VariableFormSubmission"),
                "responses": {
                    "302": _redirect_response("Variable created and browser redirected."),
                    "200": _html_response("Form re-rendered with validation errors."),
                },
            },
        },
        "/variables/./edit": {
            "get": {
                "tags": ["Variables"],
                "summary": "Show bulk variable editor",
                "responses": {"200": _html_response("Bulk variable editor rendered.")},
            },
            "post": {
                "tags": ["Variables"],
                "summary": "Replace variables from JSON",
                "requestBody": _form_request_body("VariablesBulkEditFormSubmission"),
                "responses": {
                    "302": _redirect_response("Variables updated and browser redirected."),
                    "200": _html_response("Bulk editor re-rendered with validation errors."),
                },
            },
        },
        "/variables/{variable_name}": {
            "parameters": [_path_parameter("variable_name", "Variable name to view.")],
            "get": {
                "tags": ["Variables"],
                "summary": "View variable",
                "responses": {
                    "200": _entity_resource_response(
                        "Variable details rendered.",
                        "#/components/schemas/VariableRecord",
                    )
                },
            },
        },
        "/variables/{variable_name}/edit": {
            "parameters": [_path_parameter("variable_name", "Variable name to update.")],
            "get": {
                "tags": ["Variables"],
                "summary": "Show variable edit form",
                "responses": {"200": _html_response("Variable edit form rendered.")},
            },
            "post": {
                "tags": ["Variables"],
                "summary": "Update variable",
                "requestBody": _form_request_body("VariableFormSubmission"),
                "responses": {
                    "302": _redirect_response("Variable updated and browser redirected."),
                    "200": _html_response("Form re-rendered with validation errors."),
                },
            },
        },
        "/variables/{variable_name}/delete": {
            "parameters": [_path_parameter("variable_name", "Variable name to delete.")],
            "post": {
                "tags": ["Variables"],
                "summary": "Delete variable",
                "requestBody": _form_request_body("DeletionConfirmation"),
                "responses": {
                    "302": _redirect_response("Variable deleted and browser redirected."),
                    "404": _html_response("Variable not found."),
                },
            },
        },
        "/secrets": {
            "get": {
                "tags": ["Secrets"],
                "summary": "List secrets",
                "responses": {
                    "200": _entity_collection_response(
                        "Secrets listing rendered.",
                        "#/components/schemas/SecretRecord",
                    )
                },
            }
        },
        "/secrets/new": {
            "get": {
                "tags": ["Secrets"],
                "summary": "Show secret creation form",
                "responses": {"200": _html_response("Secret creation form rendered.")},
            },
            "post": {
                "tags": ["Secrets"],
                "summary": "Create secret",
                "requestBody": _form_request_body("SecretFormSubmission"),
                "responses": {
                    "302": _redirect_response("Secret created and browser redirected."),
                    "200": _html_response("Form re-rendered with validation errors."),
                },
            },
        },
        "/secrets/{secret_name}": {
            "parameters": [_path_parameter("secret_name", "Secret name to view.")],
            "get": {
                "tags": ["Secrets"],
                "summary": "View secret",
                "responses": {
                    "200": _entity_resource_response(
                        "Secret details rendered.",
                        "#/components/schemas/SecretRecord",
                    )
                },
            },
        },
        "/secrets/{secret_name}/edit": {
            "parameters": [_path_parameter("secret_name", "Secret name to update.")],
            "get": {
                "tags": ["Secrets"],
                "summary": "Show secret edit form",
                "responses": {"200": _html_response("Secret edit form rendered.")},
            },
            "post": {
                "tags": ["Secrets"],
                "summary": "Update secret",
                "requestBody": _form_request_body("SecretFormSubmission"),
                "responses": {
                    "302": _redirect_response("Secret updated and browser redirected."),
                    "200": _html_response("Form re-rendered with validation errors."),
                },
            },
        },
        "/secrets/{secret_name}/delete": {
            "parameters": [_path_parameter("secret_name", "Secret name to delete.")],
            "post": {
                "tags": ["Secrets"],
                "summary": "Delete secret",
                "requestBody": _form_request_body("DeletionConfirmation"),
                "responses": {
                    "302": _redirect_response("Secret deleted and browser redirected."),
                    "404": _html_response("Secret not found."),
                },
            },
        },
        "/upload": {
            "get": {
                "tags": ["Uploads"],
                "summary": "Show CID upload form",
                "responses": {"200": _html_response("Upload form rendered.")},
            },
            "post": {
                "tags": ["Uploads"],
                "summary": "Upload CID content",
                "requestBody": _multipart_request_body("UploadFormSubmission"),
                "responses": {
                    "302": _redirect_response("Upload processed and browser redirected to the success page."),
                    "200": _html_response("Form re-rendered with validation errors."),
                },
            },
        },
        "/uploads": {
            "get": {
                "tags": ["Uploads"],
                "summary": "List uploaded CID content",
                "responses": {"200": _html_response("Uploads listing rendered.")},
            }
        },
    }

    _augment_json_content(paths)

    spec: Dict[str, Any] = {
        "openapi": "3.0.3",
        "info": {
            "title": "Viewer API",
            "version": "1.0.0",
            "description": (
                "Endpoints that power the Viewer workspace, including the HTML forms "
                "and JSON APIs used to manage aliases, servers, variables, secrets, "
                "and uploads."
            ),
            "contact": {
                "name": "Viewer Project",
                "url": request.url_root.rstrip("/"),
            },
        },
        "servers": [{"url": server_url}],
        "paths": paths,
        "components": {
            "schemas": {
                "InteractionRequest": _interaction_request_schema(),
                "InteractionSummary": _interaction_summary_schema(),
                "InteractionHistory": _interaction_history_schema(),
                "Error": _error_schema(),
                "AliasRecord": _alias_record_schema(),
                "ServerRecord": _server_record_schema(),
                "VariableRecord": _variable_record_schema(),
                "SecretRecord": _secret_record_schema(),
                "AliasFormSubmission": _alias_form_schema(),
                "ServerFormSubmission": _server_form_schema(),
                "VariableFormSubmission": _variable_form_schema(),
                "VariablesBulkEditFormSubmission": _variables_bulk_edit_form_schema(),
                "SecretFormSubmission": _secret_form_schema(),
                "DeletionConfirmation": _deletion_form_schema(),
                "AliasMatchPreviewRequest": _alias_match_preview_request_schema(),
                "AliasMatchPreviewResponse": _alias_match_preview_response_schema(),
                "ServerDefinitionAnalysis": _server_definition_analysis_schema(),
                "ServerTestUploadResponse": _server_test_upload_response_schema(),
                "UploadFormSubmission": _upload_form_schema(),
            }
        },
    }

    return spec


def openapi_route_rules(app: Flask) -> Set[str]:
    """Return the Flask routing rules documented in the OpenAPI schema."""

    with app.test_request_context("/"):
        spec = _build_openapi_spec()
    return {_convert_path_to_rule(path) for path in spec["paths"].keys()}


@main_bp.route("/openapi.json")
def openapi_spec() -> Response:
    """Return the OpenAPI specification describing the HTTP API."""

    return jsonify(_build_openapi_spec())


@main_bp.route("/openapi")
def openapi_docs() -> str:
    """Render an interactive Swagger UI configured for the app's schema."""

    spec_url = url_for("main.openapi_spec", _external=False)
    return render_template("swagger.html", title="API Explorer", spec_url=spec_url)


__all__ = ["openapi_spec", "openapi_docs", "openapi_route_rules"]
