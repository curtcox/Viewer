# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
"""Request transform for HRX archive gateway.

Transforms incoming gateway requests for the hrx server.
The gateway automatically routes to /servers/hrx.
Path format: /gateway/hrx/{CID}/{file_path}
"""


from urllib.parse import parse_qs, urlencode


def transform_request(request_details: dict, context: dict) -> dict:
    """Transform request for HRX server.

    Args:
        request_details: Dict containing path, query_string, method, headers, json, body
        context: Full server execution context

    Returns:
        Dict with method, headers, params for the target request
    """
    path = request_details.get("path", "")

    # Parse path: /{CID}/{file_path}
    path_parts = path.strip("/").split("/", 1)

    archive_cid = path_parts[0] if path_parts else ""
    file_path = path_parts[1] if len(path_parts) > 1 else ""

    query_string = request_details.get("query_string") or ""
    params = parse_qs(query_string, keep_blank_values=True)

    if archive_cid:
        params["archive"] = [archive_cid]
    if file_path:
        params["path"] = [file_path]

    return {
        "method": "GET",
        "path": "",
        "query_string": urlencode(params, doseq=True),
        "headers": {"Accept": "text/html, text/plain, */*"},
        "json": None,
        "data": None,
    }
