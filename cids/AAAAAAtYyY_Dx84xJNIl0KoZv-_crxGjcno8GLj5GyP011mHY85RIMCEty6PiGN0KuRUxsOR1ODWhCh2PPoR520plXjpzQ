# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
"""JSONPlaceholder API proxy server.

This server proxies requests to https://jsonplaceholder.typicode.com,
a free fake REST API for testing and prototyping.

Usage:
    /jsonplaceholder/posts - Get all posts
    /jsonplaceholder/posts/1 - Get a specific post
    /jsonplaceholder/users - Get all users
    /jsonplaceholder/comments?postId=1 - Get comments for a post
"""

from urllib.parse import urljoin, urlencode

import requests
from flask import request as flask_request


BASE_URL = "https://jsonplaceholder.typicode.com"


def _split_server_path(path: str) -> tuple[str, str]:
    """Return the server mount name and the remainder of the request path."""
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


def _proxy_request(request_info: dict) -> dict:
    """Proxy the incoming request to JSONPlaceholder API."""
    _, path_suffix = _split_server_path(request_info.get("path") or "")

    # Build the target URL
    target_url = BASE_URL.rstrip("/")
    if path_suffix:
        target_url = urljoin(target_url + "/", path_suffix.lstrip("/"))

    # Add query string if present
    query_string = request_info.get("query_string", "")
    if query_string:
        separator = "&" if "?" in target_url else "?"
        target_url = f"{target_url}{separator}{query_string}"

    # Get request parameters
    method = request_info.get("method", "GET")
    headers = request_info.get("headers") or {}

    # Filter headers
    filtered_headers = {}
    for key, value in headers.items():
        if key is None:
            continue
        lower_key = key.lower()
        if lower_key in {"host", "content-length"}:
            continue
        filtered_headers[key] = value

    # Add JSON accept header
    filtered_headers.setdefault("Accept", "application/json")

    # Get body data
    body = flask_request.get_data(cache=False) or None

    # Make the request
    response = requests.request(
        method,
        target_url,
        headers=filtered_headers,
        data=body,
        allow_redirects=True,
        timeout=30,
    )

    content_type = response.headers.get("Content-Type", "application/json")
    return {"output": response.content, "content_type": content_type}


# Main execution
try:
    result = _proxy_request(request)
except requests.RequestException as exc:
    message = f"JSONPlaceholder request failed: {exc}"
    result = {"output": message, "content_type": "text/plain"}

return result
