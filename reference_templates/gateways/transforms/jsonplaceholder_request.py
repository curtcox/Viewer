# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
"""Request transform for JSONPlaceholder API gateway.

Transforms incoming gateway requests into JSONPlaceholder API requests.
"""


def transform_request(request_details: dict, context: dict) -> dict:
    """Transform request for JSONPlaceholder API.

    Args:
        request_details: Dict containing path, query_string, method, headers, json, body
        context: Full server execution context

    Returns:
        Dict with url, method, headers, json, params for the target request
    """
    path = request_details.get("path", "")
    method = request_details.get("method", "GET")

    # Build the target URL
    base_url = "https://jsonplaceholder.typicode.com"
    if path:
        target_url = f"{base_url}/{path.lstrip('/')}"
    else:
        target_url = base_url

    # Pass through headers, filtering out host
    headers = {}
    for key, value in request_details.get("headers", {}).items():
        if key.lower() not in ("host", "content-length"):
            headers[key] = value

    # Add Accept header for JSON
    headers["Accept"] = "application/json"

    result = {
        "url": target_url,
        "method": method,
        "headers": headers,
    }

    # Include JSON body for POST/PUT/PATCH
    if method in ("POST", "PUT", "PATCH"):
        json_body = request_details.get("json")
        if json_body is not None:
            result["json"] = json_body
        elif request_details.get("body"):
            result["data"] = request_details.get("body")

    # Parse query string into params
    query_string = request_details.get("query_string", "")
    if query_string:
        from urllib.parse import parse_qs

        params = {}
        for key, values in parse_qs(query_string).items():
            params[key] = values[0] if len(values) == 1 else values
        result["params"] = params

    return result
