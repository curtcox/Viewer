"""OpenAPI specification builder for the Viewer application."""

from __future__ import annotations

from typing import Any, Dict
from urllib.parse import urlsplit, urlunsplit

from flask import request

from .helpers import (
    augment_json_content,
    entity_collection_response,
    entity_resource_response,
    form_request_body,
    html_response,
    multipart_request_body,
    path_parameter,
    redirect_response,
)
from .schemas_aliases import (
    alias_enabled_update_schema,
    alias_form_schema,
    alias_match_preview_request_schema,
    alias_match_preview_response_schema,
    alias_record_schema,
)
from .schemas_common import (
    deletion_form_schema,
    error_schema,
    upload_form_schema,
)
from .schemas_interactions import (
    interaction_history_schema,
    interaction_request_schema,
    interaction_summary_schema,
)
from .schemas_secrets import (
    secret_form_schema,
    secret_record_schema,
    secrets_bulk_edit_form_schema,
)
from .schemas_servers import (
    server_definition_analysis_schema,
    server_form_schema,
    server_record_schema,
    server_test_upload_response_schema,
)
from .schemas_variables import (
    variable_form_schema,
    variable_record_schema,
    variables_bulk_edit_form_schema,
)


def build_openapi_spec() -> Dict[str, Any]:
    """Assemble the OpenAPI schema for the application."""

    server_url = request.host_url.rstrip("/")
    parsed = urlsplit(server_url)
    hostname = parsed.hostname or ""
    port = parsed.port
    if hostname and port in (None, 80, 443):
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
                            "schema": {
                                "$ref": "#/components/schemas/InteractionRequest"
                            },
                            "examples": {
                                "interaction": {
                                    "summary": "Record AI assistance for a server",
                                    "value": {
                                        "entity_type": "server",
                                        "entity_name": "example",
                                        "action": "ai",
                                        "message": "Trim trailing spaces",
                                        "content": 'print("hello world")',
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
                                "schema": {
                                    "$ref": "#/components/schemas/InteractionHistory"
                                },
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
                    "200": entity_collection_response(
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
                "responses": {"200": html_response("Alias creation form rendered.")},
            },
            "post": {
                "tags": ["Aliases"],
                "summary": "Create alias",
                "requestBody": form_request_body("AliasFormSubmission"),
                "responses": {
                    "302": redirect_response("Alias created and browser redirected."),
                    "200": html_response("Form re-rendered with validation errors."),
                },
            },
        },
        "/aliases/{alias_name}": {
            "parameters": [path_parameter("alias_name", "Alias name to view.")],
            "get": {
                "tags": ["Aliases"],
                "summary": "View alias",
                "responses": {
                    "200": entity_resource_response(
                        "Alias details rendered.",
                        "#/components/schemas/AliasRecord",
                    )
                },
            },
        },
        "/aliases/{alias_name}/edit": {
            "parameters": [path_parameter("alias_name", "Alias name to update.")],
            "get": {
                "tags": ["Aliases"],
                "summary": "Show alias edit form",
                "responses": {"200": html_response("Alias edit form rendered.")},
            },
            "post": {
                "tags": ["Aliases"],
                "summary": "Update alias",
                "requestBody": form_request_body("AliasFormSubmission"),
                "responses": {
                    "302": redirect_response("Alias updated and browser redirected."),
                    "200": html_response("Form re-rendered with validation errors."),
                },
            },
        },
        "/aliases/{alias_name}/enabled": {
            "parameters": [path_parameter("alias_name", "Alias name to toggle.")],
            "post": {
                "tags": ["Aliases"],
                "summary": "Update alias enabled state",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/x-www-form-urlencoded": {
                            "schema": {
                                "$ref": "#/components/schemas/AliasEnabledUpdate"
                            }
                        },
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/AliasEnabledUpdate"
                            }
                        },
                    },
                },
                "responses": {
                    "302": redirect_response(
                        "Alias enabled state updated and browser redirected."
                    ),
                    "200": {
                        "description": "Alias enabled state updated.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["alias", "enabled"],
                                    "properties": {
                                        "alias": {
                                            "type": "string",
                                            "description": "Alias name.",
                                        },
                                        "enabled": {
                                            "type": "boolean",
                                            "description": "Whether the alias is enabled after the update.",
                                        },
                                    },
                                },
                            }
                        },
                    },
                    "400": {
                        "description": "Invalid enabled value supplied.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                    "404": html_response("Alias not found."),
                },
            },
        },
        "/aliases/{alias_name}/delete": {
            "parameters": [path_parameter("alias_name", "Alias name to delete.")],
            "post": {
                "tags": ["Aliases"],
                "summary": "Delete alias",
                "requestBody": form_request_body("DeletionConfirmation"),
                "responses": {
                    "302": redirect_response("Alias deleted and browser redirected."),
                    "404": html_response("Alias not found."),
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
                            "schema": {
                                "$ref": "#/components/schemas/AliasMatchPreviewRequest"
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Alias match evaluation results.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/AliasMatchPreviewResponse"
                                }
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
                    "200": entity_collection_response(
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
                "responses": {"200": html_response("Server creation form rendered.")},
            },
            "post": {
                "tags": ["Servers"],
                "summary": "Create server",
                "requestBody": form_request_body("ServerFormSubmission"),
                "responses": {
                    "302": redirect_response("Server created and browser redirected."),
                    "200": html_response("Form re-rendered with validation errors."),
                },
            },
        },
        "/servers/{server_name}": {
            "parameters": [path_parameter("server_name", "Server name to view.")],
            "get": {
                "tags": ["Servers"],
                "summary": "View server",
                "responses": {
                    "200": entity_resource_response(
                        "Server details rendered.",
                        "#/components/schemas/ServerRecord",
                    )
                },
            },
        },
        "/servers/{server_name}/edit": {
            "parameters": [path_parameter("server_name", "Server name to update.")],
            "get": {
                "tags": ["Servers"],
                "summary": "Show server edit form",
                "responses": {"200": html_response("Server edit form rendered.")},
            },
            "post": {
                "tags": ["Servers"],
                "summary": "Update server",
                "requestBody": form_request_body("ServerFormSubmission"),
                "responses": {
                    "302": redirect_response("Server updated and browser redirected."),
                    "200": html_response("Form re-rendered with validation errors."),
                },
            },
        },
        "/servers/{server_name}/delete": {
            "parameters": [path_parameter("server_name", "Server name to delete.")],
            "post": {
                "tags": ["Servers"],
                "summary": "Delete server",
                "requestBody": form_request_body("DeletionConfirmation"),
                "responses": {
                    "302": redirect_response("Server deleted and browser redirected."),
                    "404": html_response("Server not found."),
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
                                "schema": {
                                    "$ref": "#/components/schemas/ServerDefinitionAnalysis"
                                }
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
            "parameters": [
                path_parameter("server_name", "Server name supplying the test form.")
            ],
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
                                        "additionalProperties": {
                                            "type": [
                                                "string",
                                                "number",
                                                "boolean",
                                                "null",
                                            ]
                                        },
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
                                "schema": {
                                    "$ref": "#/components/schemas/ServerTestUploadResponse"
                                }
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
                    "404": html_response("Server or test configuration not available."),
                },
            },
        },
        "/variables": {
            "get": {
                "tags": ["Variables"],
                "summary": "List variables",
                "responses": {
                    "200": entity_collection_response(
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
                "responses": {"200": html_response("Variable creation form rendered.")},
            },
            "post": {
                "tags": ["Variables"],
                "summary": "Create variable",
                "requestBody": form_request_body("VariableFormSubmission"),
                "responses": {
                    "302": redirect_response(
                        "Variable created and browser redirected."
                    ),
                    "200": html_response("Form re-rendered with validation errors."),
                },
            },
        },
        "/variables/_/edit": {
            "get": {
                "tags": ["Variables"],
                "summary": "Show bulk variable editor",
                "responses": {"200": html_response("Bulk variable editor rendered.")},
            },
            "post": {
                "tags": ["Variables"],
                "summary": "Replace variables from JSON",
                "requestBody": form_request_body("VariablesBulkEditFormSubmission"),
                "responses": {
                    "302": redirect_response(
                        "Variables updated and browser redirected."
                    ),
                    "200": html_response(
                        "Bulk editor re-rendered with validation errors."
                    ),
                },
            },
        },
        "/variables/{variable_name}": {
            "parameters": [path_parameter("variable_name", "Variable name to view.")],
            "get": {
                "tags": ["Variables"],
                "summary": "View variable",
                "responses": {
                    "200": entity_resource_response(
                        "Variable details rendered.",
                        "#/components/schemas/VariableRecord",
                    )
                },
            },
        },
        "/variables/{variable_name}/edit": {
            "parameters": [path_parameter("variable_name", "Variable name to update.")],
            "get": {
                "tags": ["Variables"],
                "summary": "Show variable edit form",
                "responses": {"200": html_response("Variable edit form rendered.")},
            },
            "post": {
                "tags": ["Variables"],
                "summary": "Update variable",
                "requestBody": form_request_body("VariableFormSubmission"),
                "responses": {
                    "302": redirect_response(
                        "Variable updated and browser redirected."
                    ),
                    "200": html_response("Form re-rendered with validation errors."),
                },
            },
        },
        "/variables/{variable_name}/delete": {
            "parameters": [path_parameter("variable_name", "Variable name to delete.")],
            "post": {
                "tags": ["Variables"],
                "summary": "Delete variable",
                "requestBody": form_request_body("DeletionConfirmation"),
                "responses": {
                    "302": redirect_response(
                        "Variable deleted and browser redirected."
                    ),
                    "404": html_response("Variable not found."),
                },
            },
        },
        "/secrets": {
            "get": {
                "tags": ["Secrets"],
                "summary": "List secrets",
                "responses": {
                    "200": entity_collection_response(
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
                "responses": {"200": html_response("Secret creation form rendered.")},
            },
            "post": {
                "tags": ["Secrets"],
                "summary": "Create secret",
                "requestBody": form_request_body("SecretFormSubmission"),
                "responses": {
                    "302": redirect_response("Secret created and browser redirected."),
                    "200": html_response("Form re-rendered with validation errors."),
                },
            },
        },
        "/secrets/_/edit": {
            "get": {
                "tags": ["Secrets"],
                "summary": "Show bulk secret editor",
                "responses": {"200": html_response("Bulk secret editor rendered.")},
            },
            "post": {
                "tags": ["Secrets"],
                "summary": "Replace secrets from JSON",
                "requestBody": form_request_body("SecretsBulkEditFormSubmission"),
                "responses": {
                    "302": redirect_response("Secrets updated and browser redirected."),
                    "200": html_response(
                        "Bulk editor re-rendered with validation errors."
                    ),
                },
            },
        },
        "/secrets/{secret_name}": {
            "parameters": [path_parameter("secret_name", "Secret name to view.")],
            "get": {
                "tags": ["Secrets"],
                "summary": "View secret",
                "responses": {
                    "200": entity_resource_response(
                        "Secret details rendered.",
                        "#/components/schemas/SecretRecord",
                    )
                },
            },
        },
        "/secrets/{secret_name}/edit": {
            "parameters": [path_parameter("secret_name", "Secret name to update.")],
            "get": {
                "tags": ["Secrets"],
                "summary": "Show secret edit form",
                "responses": {"200": html_response("Secret edit form rendered.")},
            },
            "post": {
                "tags": ["Secrets"],
                "summary": "Update secret",
                "requestBody": form_request_body("SecretFormSubmission"),
                "responses": {
                    "302": redirect_response("Secret updated and browser redirected."),
                    "200": html_response("Form re-rendered with validation errors."),
                },
            },
        },
        "/secrets/{secret_name}/delete": {
            "parameters": [path_parameter("secret_name", "Secret name to delete.")],
            "post": {
                "tags": ["Secrets"],
                "summary": "Delete secret",
                "requestBody": form_request_body("DeletionConfirmation"),
                "responses": {
                    "302": redirect_response("Secret deleted and browser redirected."),
                    "404": html_response("Secret not found."),
                },
            },
        },
        "/upload": {
            "get": {
                "tags": ["Uploads"],
                "summary": "Show CID upload form",
                "responses": {"200": html_response("Upload form rendered.")},
            },
            "post": {
                "tags": ["Uploads"],
                "summary": "Upload CID content",
                "requestBody": multipart_request_body("UploadFormSubmission"),
                "responses": {
                    "302": redirect_response(
                        "Upload processed and browser redirected to the success page."
                    ),
                    "200": html_response("Form re-rendered with validation errors."),
                },
            },
        },
        "/uploads": {
            "get": {
                "tags": ["Uploads"],
                "summary": "List uploaded CID content",
                "responses": {"200": html_response("Uploads listing rendered.")},
            }
        },
    }

    augment_json_content(paths)

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
                "InteractionRequest": interaction_request_schema(),
                "InteractionSummary": interaction_summary_schema(),
                "InteractionHistory": interaction_history_schema(),
                "Error": error_schema(),
                "AliasRecord": alias_record_schema(),
                "ServerRecord": server_record_schema(),
                "VariableRecord": variable_record_schema(),
                "SecretRecord": secret_record_schema(),
                "AliasFormSubmission": alias_form_schema(),
                "AliasEnabledUpdate": alias_enabled_update_schema(),
                "ServerFormSubmission": server_form_schema(),
                "VariableFormSubmission": variable_form_schema(),
                "VariablesBulkEditFormSubmission": variables_bulk_edit_form_schema(),
                "SecretsBulkEditFormSubmission": secrets_bulk_edit_form_schema(),
                "SecretFormSubmission": secret_form_schema(),
                "DeletionConfirmation": deletion_form_schema(),
                "AliasMatchPreviewRequest": alias_match_preview_request_schema(),
                "AliasMatchPreviewResponse": alias_match_preview_response_schema(),
                "ServerDefinitionAnalysis": server_definition_analysis_schema(),
                "ServerTestUploadResponse": server_test_upload_response_schema(),
                "UploadFormSubmission": upload_form_schema(),
            }
        },
    }

    return spec


__all__ = ["build_openapi_spec"]
