# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
"""Request transform for JSON API gateway.

This is a pass-through transform that doesn't modify requests.
"""


def transform_request(request_details: dict, context: dict) -> dict:
    """Pass through request details unchanged.

    Args:
        request_details: Dict containing path, query_string, method, headers, json, data
        context: Full server execution context

    Returns:
        Unmodified request_details dict
    """
    return request_details
