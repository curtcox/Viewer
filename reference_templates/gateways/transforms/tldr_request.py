# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
"""Request transform for tldr gateway.

Transforms incoming gateway requests into /servers/tldr requests.
"""


def transform_request(request_details: dict, context: dict) -> dict:
    """Transform request for tldr server.

    Args:
        request_details: Dict containing path, query_string, method, headers, json, body
        context: Full server execution context

    Returns:
        Dict with url, method, headers, params for the target request
    """
    path = request_details.get("path", "")

    # Extract command from path (e.g., "ls" from "/ls")
    command = path.strip("/").split("/")[0] if path.strip("/") else ""

    # Build request to internal tldr server
    params = {}
    if command:
        params["command"] = command

    return {
        "url": "/servers/tldr",
        "method": "GET",
        "headers": {"Accept": "text/plain"},
        "params": params,
    }
