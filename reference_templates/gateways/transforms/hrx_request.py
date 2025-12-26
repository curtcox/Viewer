# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
"""Request transform for HRX archive gateway.

Transforms incoming gateway requests into /servers/hrx requests.
Path format: /gateway/hrx/{CID}/{file_path}
"""


def transform_request(request_details: dict, context: dict) -> dict:
    """Transform request for HRX server.

    Args:
        request_details: Dict containing path, query_string, method, headers, json, body
        context: Full server execution context

    Returns:
        Dict with url, method, headers, params for the target request
    """
    path = request_details.get("path", "")

    # Parse path: /{CID}/{file_path}
    path_parts = path.strip("/").split("/", 1)

    archive_cid = path_parts[0] if path_parts else ""
    file_path = path_parts[1] if len(path_parts) > 1 else ""

    # Build request to internal hrx server
    params = {}
    if archive_cid:
        params["archive_cid"] = archive_cid
    if file_path:
        params["path"] = file_path

    return {
        "url": "/servers/hrx",
        "method": "GET",
        "headers": {"Accept": "text/html, text/plain, */*"},
        "params": params,
    }
