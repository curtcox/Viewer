# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
"""Request transform for man page gateway.

Transforms incoming gateway requests for the man server.
The gateway automatically routes to /servers/man.
"""

from urllib.parse import quote


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

    # Internal gateway requests do not use query params; they build the internal
    # URL as /{server}/{path}. The man server is a bash command server that reads
    # its first positional argument ($1) from the first path segment after /man.
    #
    # To support an optional numeric section, we encode a single $1 value like
    # "1 ls" as a single path segment "1%20ls".
    internal_path = ""
    if section and command:
        internal_path = quote(f"{section} {command}")
    elif command:
        internal_path = command

    return {
        "method": "GET",
        "headers": {"Accept": "text/plain"},
        "path": internal_path,
    }
