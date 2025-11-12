"""HTTP request parsing and parameter resolution."""

from typing import Any, Dict, Iterable, List, Optional, Tuple

from flask import Response, has_request_context, jsonify, make_response, render_template, request

# pylint: disable=no-name-in-module  # False positive: function_analysis exists via lazy loading
from server_execution.function_analysis import FunctionDetails, MissingParameterError


def _extract_request_body_values() -> Dict[str, Any]:
    body: Dict[str, Any] = {}

    try:
        json_payload = request.get_json(silent=True)
    except (UnicodeDecodeError, ValueError):  # pragma: no cover - defensive guard for malformed requests
        json_payload = None

    if isinstance(json_payload, dict):
        body.update(json_payload)

    if request.form:
        body.update(request.form.to_dict(flat=True))

    return body


def _extract_context_dicts(base_args: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Extract variables and secrets dictionaries from base_args context."""
    context = base_args.get("context") if isinstance(base_args, dict) else None
    if not isinstance(context, dict):
        return {}, {}

    context_variables = context.get("variables")
    if not isinstance(context_variables, dict):
        context_variables = {}

    context_secrets = context.get("secrets")
    if not isinstance(context_secrets, dict):
        context_secrets = {}

    return context_variables, context_secrets


def _collect_parameter_sources(
    base_args: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Collect all possible parameter sources from the request context."""
    query_values = request.args.to_dict(flat=True) if request.args else {}
    body_values = _extract_request_body_values()
    header_values = {k.lower(): v for k, v in request.headers.items()}
    context_variables, context_secrets = _extract_context_dicts(base_args)

    return query_values, body_values, header_values, context_variables, context_secrets


def _lookup_header_value(header_values: Dict[str, Any], param_name: str) -> Optional[Any]:
    """Look up a header value, trying both underscores and dashes."""
    lowered = param_name.lower()
    if lowered in header_values:
        return header_values[lowered]

    dashed = param_name.replace("_", "-").lower()
    if dashed in header_values:
        return header_values[dashed]

    return None


def _resolve_single_parameter(
    param_name: str,
    query_values: Dict[str, Any],
    body_values: Dict[str, Any],
    header_values: Dict[str, Any],
    base_args: Dict[str, Any],
    context_variables: Dict[str, Any],
    context_secrets: Dict[str, Any],
) -> Tuple[bool, Optional[Any]]:
    """Attempt to resolve a single parameter from available sources.

    Returns (found, value) tuple.
    """
    if param_name in query_values:
        return True, query_values[param_name]

    if param_name in body_values:
        return True, body_values[param_name]

    header_value = _lookup_header_value(header_values, param_name)
    if header_value is not None:
        return True, header_value

    if param_name in base_args:
        return True, base_args[param_name]

    if param_name in context_variables:
        return True, context_variables[param_name]

    if param_name in context_secrets:
        return True, context_secrets[param_name]

    return False, None


def _resolve_function_parameters(
    details: FunctionDetails,
    base_args: Dict[str, Any],
    *,
    allow_partial: bool = False,
) -> Any:
    """Resolve function parameters from request context and user data."""
    required = set(details.required_parameters)
    resolved: Dict[str, Any] = {}
    missing: List[str] = []

    # Collect all parameter sources
    query_values, body_values, header_values, context_variables, context_secrets = (
        _collect_parameter_sources(base_args)
    )

    available = {
        "query_string": sorted(query_values.keys()),
        "request_body": sorted(body_values.keys()),
        "headers": sorted(set(request.headers.keys())),
        "context_variables": sorted(context_variables.keys()),
        "context_secrets": sorted(context_secrets.keys()),
    }

    # Resolve each parameter
    for name in details.parameter_order:
        found, value = _resolve_single_parameter(
            name,
            query_values,
            body_values,
            header_values,
            base_args,
            context_variables,
            context_secrets,
        )

        if found:
            resolved[name] = value
        elif name in required:
            missing.append(name)

    # Handle results based on allow_partial flag
    if missing:
        if allow_partial:
            return resolved, missing, available
        raise MissingParameterError(missing, available)

    return (resolved, [], available) if allow_partial else resolved


def _build_missing_parameter_response(
    function_name: str, error: MissingParameterError
) -> Response:
    payload = {
        "error": f"Missing required parameters for {function_name}()",
        "missing_parameters": [
            {
                "name": name,
                "detail": (
                    "Provide the parameter via the query string, request body, HTTP headers, saved variables, or saved secrets."
                ),
            }
            for name in sorted(error.missing)
        ],
        "available_keys": error.available,
    }
    response = jsonify(payload)
    response.status_code = 400
    return response


def _build_multi_parameter_error_page(
    server_name: Optional[str],
    function_name: str,
    missing: Iterable[str],
    supplied: Iterable[str],
    available: Dict[str, List[str]],
) -> Response:
    request_path = ""
    query_string = ""
    method = ""
    if has_request_context():
        request_path = request.path
        query_string = request.query_string.decode("utf-8")
        method = request.method

    html = render_template(
        "auto_main_multi_parameter_error.html",
        server_name=server_name,
        function_name=function_name,
        missing_parameters=sorted(missing),
        supplied_parameters=sorted(supplied),
        available_sources=available,
        request_path=request_path,
        request_method=method,
        query_string=query_string,
    )

    response = make_response(html)
    response.status_code = 400
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response
