# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
"""Request transform for man page gateway.

Transforms incoming gateway requests into /servers/man requests.
"""


def transform_request(request_details: dict, context: dict) -> dict:
    """Transform request for man page server.

    Args:
        request_details: Dict containing path, query_string, method, headers, json, body
        context: Full server execution context

    Returns:
        Dict with url, method, headers, params for the target request
    """
    path = request_details.get("path", "")

    # Extract command from path (e.g., "ls" from "/ls" or "ls/section" from "/ls/1")
    command = path.strip("/").split("/")[0] if path.strip("/") else ""

    # Check for section number in path (e.g., /ls/1 for man section 1)
    path_parts = path.strip("/").split("/")
    section = None
    if len(path_parts) > 1 and path_parts[1].isdigit():
        section = path_parts[1]

    # Build request to internal man server
    # The man server is at /servers/man
    params = {}
    if command:
        params["command"] = command
    if section:
        params["section"] = section

    return {
        "url": "/servers/man",
        "method": "GET",
        "headers": {"Accept": "text/plain"},
        "params": params,
    }
