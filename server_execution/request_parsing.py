"""HTTP request parsing and parameter resolution."""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from flask import (
    Response,
    has_request_context,
    jsonify,
    make_response,
    render_template,
    request,
)

# pylint: disable=no-name-in-module  # False positive: function_analysis exists via lazy loading
from server_execution.function_analysis import FunctionDetails, MissingParameterError


def _extract_request_body_values() -> Dict[str, Any]:
    body: Dict[str, Any] = {}

    try:
        json_payload = request.get_json(silent=True)
    except (
        UnicodeDecodeError,
        ValueError,
    ):  # pragma: no cover - defensive guard for malformed requests
        json_payload = None

    if isinstance(json_payload, dict):
        body.update(json_payload)

    if request.form:
        body.update(request.form.to_dict(flat=True))

    return body


def _extract_context_dicts(
    base_args: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
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
    base_args: Dict[str, Any],
) -> Tuple[
    Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]
]:
    """Collect all possible parameter sources from the request context."""
    query_values = request.args.to_dict(flat=True) if request.args else {}
    body_values = _extract_request_body_values()
    header_values = {k.lower(): v for k, v in request.headers.items()}
    context_variables, context_secrets = _extract_context_dicts(base_args)

    return query_values, body_values, header_values, context_variables, context_secrets


def _lookup_header_value(
    header_values: Dict[str, Any], param_name: str
) -> Optional[Any]:
    """Look up a header value, trying both underscores and dashes."""
    lowered = param_name.lower()
    if lowered in header_values:
        return header_values[lowered]

    dashed = param_name.replace("_", "-").lower()
    if dashed in header_values:
        return header_values[dashed]

    return None


@dataclass(frozen=True)
class NamedValueResolver:
    """Resolve named parameters from request and context sources.

    The resolver encapsulates the standard priority order used by Viewer:
    query string, request body, headers, explicit invocation arguments,
    saved variables, then saved secrets.
    """

    base_args: Dict[str, Any]

    def __post_init__(self):
        (
            query_values,
            body_values,
            header_values,
            context_variables,
            context_secrets,
        ) = _collect_parameter_sources(self.base_args)
        object.__setattr__(self, "query_values", query_values)
        object.__setattr__(self, "body_values", body_values)
        object.__setattr__(self, "header_values", header_values)
        object.__setattr__(self, "context_variables", context_variables)
        object.__setattr__(self, "context_secrets", context_secrets)

    def resolve(self, param_name: str) -> Tuple[bool, Optional[Any]]:
        """Resolve a single named parameter from known sources."""
        if param_name in self.query_values:
            return True, self.query_values[param_name]

        if param_name in self.body_values:
            return True, self.body_values[param_name]

        header_value = _lookup_header_value(self.header_values, param_name)
        if header_value is not None:
            return True, header_value

        if param_name in self.base_args:
            return True, self.base_args[param_name]

        if param_name in self.context_variables:
            return True, self.context_variables[param_name]

        if param_name in self.context_secrets:
            return True, self.context_secrets[param_name]

        return False, None

    def resolve_many(self, names: Iterable[str]) -> Dict[str, Any]:
        """Resolve many parameters at once, skipping missing values."""
        resolved: Dict[str, Any] = {}
        for name in names:
            found, value = self.resolve(name)
            if found:
                resolved[name] = value
        return resolved

    def available_sources(self) -> Dict[str, List[str]]:
        """Report available keys by source for diagnostics."""
        return {
            "query_string": sorted(self.query_values.keys()),
            "request_body": sorted(self.body_values.keys()),
            "headers": sorted(set(request.headers.keys())),
            "context_variables": sorted(self.context_variables.keys()),
            "context_secrets": sorted(self.context_secrets.keys()),
        }


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

    resolver = NamedValueResolver(base_args)
    available = resolver.available_sources()

    # Resolve each parameter
    for name in details.parameter_order:
        found, value = resolver.resolve(name)

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


def resolve_named_value(param_name: str, base_args: Dict[str, Any]) -> Optional[Any]:
    """Resolve a single parameter using the shared named-value logic."""

    found, value = NamedValueResolver(base_args).resolve(param_name)
    return value if found else None


def resolve_named_values(
    param_names: Iterable[str], base_args: Dict[str, Any]
) -> Dict[str, Any]:
    """Resolve multiple parameters using the shared named-value logic."""

    return NamedValueResolver(base_args).resolve_many(param_names)


def _build_missing_parameter_response(function_name: str, error: MissingParameterError):
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
