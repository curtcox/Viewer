# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
"""JSON API server.

This server is intended to be accessed via the gateway and supports arbitrary
HTTP requests to a configured target REST API.

Configuration:
- BASE_URL: The upstream API base URL.

Usage:
- /json_api/<path>

The gateway is responsible for request/response transformation.
"""

from __future__ import annotations

from urllib.parse import urljoin

import requests
from flask import request as flask_request

from server_utils.external_api import auto_decode_response


BASE_URL = "https://jsonplaceholder.typicode.com"


def _split_server_path(path: str) -> tuple[str, str]:
    if not isinstance(path, str):
        return "", ""

    stripped = path.lstrip("/")
    if not stripped:
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


def _proxy_request(req) -> dict:
    full_path = getattr(req, "path", "") or ""
    _, suffix = _split_server_path(full_path)

    target_url = BASE_URL.rstrip("/")
    if suffix:
        target_url = urljoin(target_url + "/", suffix.lstrip("/"))

    query_string_bytes = getattr(req, "query_string", b"") or b""
    query_string = (
        query_string_bytes.decode("utf-8", errors="replace")
        if isinstance(query_string_bytes, (bytes, bytearray))
        else str(query_string_bytes)
    )
    if query_string:
        separator = "&" if "?" in target_url else "?"
        target_url = f"{target_url}{separator}{query_string}"

    method = getattr(req, "method", "GET") or "GET"
    headers = dict(getattr(req, "headers", {}) or {})

    filtered_headers = {}
    for key, value in headers.items():
        if key is None:
            continue
        lower_key = key.lower()
        if lower_key in {"host", "content-length"}:
            continue
        filtered_headers[key] = value

    filtered_headers.setdefault("Accept", "application/json")
    filtered_headers["Accept-Encoding"] = "identity"

    body = req.get_data(cache=False) if hasattr(req, "get_data") else None
    body = body or None

    response = requests.request(
        method,
        target_url,
        headers=filtered_headers,
        data=body,
        allow_redirects=True,
        timeout=30,
    )

    content_type = response.headers.get("Content-Type", "application/json")
    output = auto_decode_response(response)
    return {"output": output, "content_type": content_type}


def main(context=None):
    try:
        result = _proxy_request(flask_request)
    except requests.RequestException as exc:
        message = f"JSON API request failed: {exc}"
        result = {"output": message, "content_type": "text/plain"}

    return result
