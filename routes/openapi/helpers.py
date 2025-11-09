"""Helper functions for constructing OpenAPI response and request specifications."""
from __future__ import annotations

import re
from typing import Any, Dict

_PATH_PARAMETER_PATTERN = re.compile(r"{([^}/]+)}")


def html_response(description: str) -> Dict[str, Any]:
    """Describe responses that originate as HTML but support multiple formats."""

    content = string_media_content()
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


def string_media_content() -> Dict[str, Any]:
    """Return content descriptors for string-based representations."""

    return {
        "text/html": {"schema": {"type": "string"}},
        "text/plain": {"schema": {"type": "string"}},
        "text/markdown": {"schema": {"type": "string"}},
        "application/xml": {"schema": {"type": "string"}},
        "text/csv": {"schema": {"type": "string"}},
    }


def entity_collection_response(description: str, schema_ref: str) -> Dict[str, Any]:
    """Describe collection responses with support for multiple media types."""

    content = string_media_content()
    content["application/json"] = {
        "schema": {
            "type": "array",
            "items": {"$ref": schema_ref},
        }
    }
    return {"description": description, "content": content}


def entity_resource_response(description: str, schema_ref: str) -> Dict[str, Any]:
    """Describe single resource responses with support for multiple media types."""

    content = string_media_content()
    content["application/json"] = {"schema": {"$ref": schema_ref}}
    return {"description": description, "content": content}


def redirect_response(description: str) -> Dict[str, Any]:
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


def form_request_body(schema_name: str) -> Dict[str, Any]:
    """Describe an x-www-form-urlencoded request body referencing a schema."""

    return {
        "required": True,
        "content": {
            "application/x-www-form-urlencoded": {
                "schema": {"$ref": f"#/components/schemas/{schema_name}"}
            }
        },
    }


def multipart_request_body(schema_name: str) -> Dict[str, Any]:
    """Describe a multipart/form-data request body referencing a schema."""

    return {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {"$ref": f"#/components/schemas/{schema_name}"}
            }
        },
    }


def path_parameter(name: str, description: str) -> Dict[str, Any]:
    """Return a reusable path parameter description."""

    return {
        "name": name,
        "in": "path",
        "required": True,
        "description": description,
        "schema": {"type": "string"},
    }


def convert_path_to_rule(path: str) -> str:
    """Translate an OpenAPI path template to a Flask routing rule."""

    return _PATH_PARAMETER_PATTERN.sub(lambda match: f"<{match.group(1)}>", path)


def augment_json_content(paths: Dict[str, Any]) -> None:
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
                for mimetype, descriptor in string_media_content().items():
                    content.setdefault(mimetype, descriptor)


__all__ = [
    "html_response",
    "string_media_content",
    "entity_collection_response",
    "entity_resource_response",
    "redirect_response",
    "form_request_body",
    "multipart_request_body",
    "path_parameter",
    "convert_path_to_rule",
    "augment_json_content",
]
