# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
"""Request transform for man page gateway.

Transforms incoming gateway requests for the man server.
The gateway automatically routes to /servers/man.
"""


def transform_request(request_details: dict, context: dict) -> dict:
    """Transform request for man page server.

    Args:
        request_details: Dict containing path, query_string, method, headers, json, body
        context: Full server execution context

    Returns:
        Dict with method, headers, params for the target request
    """
    path = request_details.get("path", "")

    # Extract command from path (e.g., "grep" from "/grep")
    command = path.strip("/").split("/")[0] if path.strip("/") else ""

    # Check for section number in path (e.g., /ls/1 for man section 1)
    path_parts = path.strip("/").split("/")
    section = None
    if len(path_parts) > 1 and path_parts[1].isdigit():
        section = path_parts[1]

    # Build request params for man server
    params = {}
    if command:
        params["command"] = command
    if section:
        params["section"] = section

    return {
        "method": "GET",
        "headers": {"Accept": "text/plain"},
        "params": params,
    }
