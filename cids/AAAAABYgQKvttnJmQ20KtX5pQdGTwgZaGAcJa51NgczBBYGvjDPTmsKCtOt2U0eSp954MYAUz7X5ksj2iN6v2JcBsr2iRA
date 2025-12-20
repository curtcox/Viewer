# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
# This template executes inside the Viewer runtime where `request` and `context` are provided.
from urllib.parse import urlsplit, urlunsplit

import requests
from flask import request as flask_request

PLACEHOLDER_TARGET_URL = "https://example.com/replace-me"
# Update this value to point at the upstream service you want to proxy to when
# you do not plan to use Viewer variables or secrets for configuration.
BASE_TARGET_URL = PLACEHOLDER_TARGET_URL


def _split_server_path(path: str) -> tuple[str, str]:
    """Return the server mount name and the remainder of the request path."""

    if not isinstance(path, str):
        return "", ""

    stripped = path.lstrip("/")
    if not stripped:
        # Preserve a trailing slash when the request is just the mount point.
        return "", "/" if path.endswith("/") else ""

    if "/" in stripped:
        server_name, remainder = stripped.split("/", 1)
        suffix = f"/{remainder}"
    else:
        server_name = stripped
        suffix = ""

    if not suffix and path.endswith("/"):
        suffix = "/"

    return server_name, suffix


def _build_target_url(base_url: str, path: str, query_string: str) -> str:
    """Combine the base target URL with the incoming path and query string."""

    parsed = urlsplit(base_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(
            "BASE_TARGET_URL must include a scheme (https://) and hostname"
        )

    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError("BASE_TARGET_URL must start with http:// or https://")

    _, suffix = _split_server_path(path or "")

    base_path = parsed.path.rstrip("/")
    if suffix == "/":
        combined_path = f"{base_path}/"
    elif suffix:
        combined_path = f"{base_path}{suffix}"
    else:
        combined_path = base_path

    if combined_path:
        normalized_path = (
            combined_path if combined_path.startswith("/") else f"/{combined_path}"
        )
    else:
        normalized_path = parsed.path or ""

    incoming_query = (query_string or "").lstrip("?")
    if parsed.query and incoming_query:
        combined_query = f"{parsed.query}&{incoming_query}"
    elif incoming_query:
        combined_query = incoming_query
    else:
        combined_query = parsed.query

    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            normalized_path,
            combined_query,
            parsed.fragment,
        )
    )


def _proxy_request(base_url: str, request_info: dict) -> dict:
    """Proxy the incoming request to the configured base URL."""

    headers = request_info.get("headers") or {}
    filtered_headers = {}
    for key, value in headers.items():
        if key is None:
            continue
        lower_key = key.lower()
        if lower_key in {"host", "content-length"}:
            continue
        filtered_headers[key] = value

    body = flask_request.get_data(cache=False) or None

    target_url = _build_target_url(
        base_url,
        request_info.get("path") or "",
        request_info.get("query_string") or "",
    )

    response = requests.request(
        request_info.get("method", "GET"),
        target_url,
        headers=filtered_headers,
        data=body,
        allow_redirects=False,
        timeout=60,
    )

    content_type = response.headers.get("Content-Type", "application/octet-stream")
    return {"output": response.content, "content_type": content_type}


def _normalize_server_token(server_name: str) -> str:
    if not isinstance(server_name, str):
        return ""

    sanitized = []
    for character in server_name:
        if character.isalnum():
            sanitized.append(character.upper())
        else:
            if sanitized and sanitized[-1] != "_":
                sanitized.append("_")
    token = "".join(sanitized).strip("_")
    return token


def _coalesce_config_value(source: dict, keys: list[str]) -> str:
    if not isinstance(source, dict):
        return ""

    for key in keys:
        if key not in source:
            continue
        value = source.get(key)
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed:
                return trimmed
    return ""


def _resolve_base_target_url(
    default_url: str, request_info: dict, context_info: dict
) -> str:
    request_info = request_info or {}
    context_info = context_info or {}

    server_name, _ = _split_server_path(request_info.get("path") or "")
    lookup_keys = ["BASE_TARGET_URL"]

    normalized = _normalize_server_token(server_name)
    if normalized:
        lookup_keys.insert(0, f"{normalized}_BASE_TARGET_URL")

    for source_name in ("variables", "secrets"):
        candidate = _coalesce_config_value(context_info.get(source_name), lookup_keys)
        if candidate:
            return candidate

    return default_url.strip()


resolved_base_url = _resolve_base_target_url(BASE_TARGET_URL, request, context)

if not resolved_base_url or resolved_base_url == PLACEHOLDER_TARGET_URL:
    return {
        "output": "Configure BASE_TARGET_URL via the template, a variable, or a secret to enable proxying.",
        "content_type": "text/plain",
    }

try:
    result = _proxy_request(resolved_base_url, request)
except ValueError as exc:
    return {"output": str(exc), "content_type": "text/plain"}
except requests.RequestException as exc:
    message = f"Proxy request failed: {exc}"
    return {"output": message, "content_type": "text/plain"}

return result
