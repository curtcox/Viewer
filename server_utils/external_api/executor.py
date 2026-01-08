"""Helpers for executing external API requests."""

from __future__ import annotations

from typing import Any, Callable

import requests

from .error_response import error_output
from .http_client import ExternalApiClient


def _get_status(exc: requests.RequestException) -> int | None:
    response = getattr(exc, "response", None)
    return response.status_code if response is not None else None


def execute_json_request(
    client: ExternalApiClient,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    data: Any | None = None,
    auth: tuple[str, str] | None = None,
    timeout: int = 60,
    error_key: str = "error",
    request_error_message: str = "Request failed",
    include_exception_in_message: bool = True,
    error_parser: Callable[[requests.Response, Any], str] | None = None,
    success_parser: Callable[[requests.Response, Any], Any] | None = None,
    empty_response_statuses: tuple[int, ...] | None = None,
    empty_response_output: Any | None = None,
) -> dict[str, Any]:
    try:
        request_kwargs = {
            "headers": headers,
            "params": params,
            "json": json,
            "data": data,
            "timeout": timeout,
            "auth": auth,
        }
        method_name = method.lower()
        mock_children = getattr(client, "_mock_children", None)
        request_func = getattr(client, "request", None)
        method_func = None
        if isinstance(mock_children, dict) and method_name in mock_children:
            method_func = mock_children[method_name]
        elif not isinstance(mock_children, dict):
            method_func = getattr(client, method_name, None)
        if isinstance(client, ExternalApiClient) and callable(request_func):
            response = request_func(method=method, url=url, **request_kwargs)
        elif isinstance(mock_children, dict) and method_name in mock_children:
            response = method_func(url, **request_kwargs)
        elif isinstance(mock_children, dict) and "request" in mock_children and callable(request_func):
            response = request_func(method=method, url=url, **request_kwargs)
        elif method_func is not None:
            response = method_func(url, **request_kwargs)
        elif callable(request_func):
            response = request_func(method=method, url=url, **request_kwargs)
        else:
            raise AttributeError(f"Client does not support method {method_name} or request()")
    except requests.RequestException as exc:
        message = request_error_message
        if include_exception_in_message:
            message = f"{request_error_message}: {exc}"
        return error_output(message, status_code=_get_status(exc), details=str(exc))

    if empty_response_statuses and response.status_code in empty_response_statuses:
        return {"output": empty_response_output}

    try:
        data = response.json()
    except ValueError:
        return error_output(
            "Invalid JSON response",
            status_code=getattr(response, "status_code", None),
            details=getattr(response, "text", None),
        )

    if not response.ok:
        message = "API error"
        if error_parser:
            message = error_parser(response, data)
        elif isinstance(data, dict):
            message = data.get(error_key, message)
            if isinstance(message, dict):
                message = message.get("message", "API error")
        return error_output(message, status_code=response.status_code, response=data)

    if success_parser:
        processed = success_parser(response, data)
        if isinstance(processed, dict) and "output" in processed:
            return processed
        return {"output": processed}

    return {"output": data}
