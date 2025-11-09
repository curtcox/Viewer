"""Core Python code execution and server invocation logic."""

import textwrap
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import logfire
from flask import Response, current_app, has_app_context, has_request_context, jsonify, request

from alias_routing import find_matching_alias
from cid_presenter import cid_path, format_cid
from db_access import get_cid_by_path, get_server_by_name, get_user_secrets, get_user_servers, get_user_variables
from server_execution.error_handling import _handle_execution_exception
from server_execution.function_analysis import FunctionDetails, MissingParameterError, _analyze_server_definition_for_function
from server_execution.invocation_tracking import request_details
from server_execution.request_parsing import (
    _build_missing_parameter_response,
    _build_multi_parameter_error_page,
    _resolve_function_parameters,
)
from server_execution.response_handling import _handle_successful_execution, _log_server_output
from server_execution.variable_resolution import _current_user_id, _resolve_variable_values, _should_skip_variable_prefetch
from text_function_runner import run_text_function

AUTO_MAIN_PARAMS_NAME = "__viewer_auto_main_params__"
AUTO_MAIN_RESULT_NAME = "__viewer_auto_main_result__"


def _normalize_execution_result(result: Any) -> Tuple[Any, str]:
    if isinstance(result, dict):
        return result.get("output", ""), result.get("content_type", "text/html")
    if isinstance(result, tuple) and len(result) == 2:
        return result[0], result[1]
    return result, "text/html"


def _split_path_segments(path: Optional[str]) -> List[str]:
    if not path:
        return []
    return [segment for segment in path.split("/") if segment]


def _remaining_path_segments(server_name: Optional[str]) -> List[str]:
    if not server_name or not has_request_context():
        return []
    segments = _split_path_segments(request.path)
    if not segments or segments[0] != server_name:
        return []
    return segments[1:]


def _auto_main_accepts_additional_path(server: Any) -> bool:
    definition = getattr(server, "definition", "")
    if not isinstance(definition, str):
        return False

    details = _analyze_server_definition_for_function(definition, "main")
    if not details or details.unsupported_reasons:
        return False

    return bool(details.parameter_order)


def _clone_request_context_kwargs(path: str) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {"path": path}
    if has_request_context():
        kwargs["method"] = request.method
        kwargs["query_string"] = request.query_string.decode("utf-8")
        headers = [(k, v) for k, v in request.headers if k.lower() != "cookie"]
        if headers:
            kwargs["headers"] = headers
        json_payload = request.get_json(silent=True)
        if json_payload is not None:
            kwargs["json"] = json_payload
        else:
            data = request.get_data()
            if data:
                kwargs["data"] = data
    else:
        kwargs["method"] = "GET"
        kwargs["query_string"] = ""
    return kwargs


def _execute_nested_server_to_value(
    server: Any, server_name: str, path: str
) -> Any:
    if not has_app_context():
        return None

    kwargs = _clone_request_context_kwargs(path)
    with current_app.test_request_context(**kwargs):
        args = build_request_args()
        prepared = _prepare_invocation(
            server.definition,
            args,
            function_name="main",
            allow_fallback=True,
            server_name=server_name,
        )

        if prepared is None:
            return None

        if isinstance(prepared, tuple):
            code_to_run, args_to_use = prepared
        else:
            return prepared

        try:
            result = run_text_function(code_to_run, args_to_use)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Catch all exceptions from user code execution
            return _handle_execution_exception(exc, code_to_run, args_to_use, server_name)

        output, _ = _normalize_execution_result(result)
        from server_execution.response_handling import _encode_output
        output_bytes = _encode_output(output)
        try:
            return output_bytes.decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            # Handle decoding errors by using replacement characters
            return output_bytes.decode("utf-8", errors="replace")


def _evaluate_nested_path_to_value(path: str, visited: Optional[Set[str]] = None) -> Any:
    """Recursively evaluate a path to produce a value, following servers/aliases/CIDs."""
    normalized = (path or "").strip()
    if not normalized:
        return None

    if not normalized.startswith("/"):
        normalized = f"/{normalized}"

    if visited is None:
        visited = set()

    if normalized in visited:
        return None  # Prevent infinite recursion

    visited.add(normalized)

    segments = _split_path_segments(normalized)
    if not segments:
        return None

    server_name = segments[0]
    user_id = _current_user_id()
    server = get_server_by_name(user_id, server_name) if user_id else None
    if server and not getattr(server, "enabled", True):
        server = None
    if server:
        return _execute_nested_server_to_value(server, server_name, normalized)

    alias_match = find_matching_alias(normalized)
    if alias_match and getattr(alias_match, "route", None):
        target = getattr(alias_match.route, "target_path", None)
        if target:
            return _evaluate_nested_path_to_value(target, visited)

    if len(segments) == 1:
        normalized_cid = format_cid(segments[0])
        cid_record_path = cid_path(normalized_cid)
        if cid_record_path:
            cid_record = get_cid_by_path(cid_record_path)
            if cid_record and getattr(cid_record, "file_data", None) is not None:
                try:
                    return cid_record.file_data.decode("utf-8")
                except (UnicodeDecodeError, AttributeError):
                    # Handle decoding errors by using replacement characters
                    return cid_record.file_data.decode("utf-8", errors="replace")

    return None


def _inject_nested_parameter_value(
    server_name: Optional[str],
    function_name: str,
    resolved: Dict[str, Any],
    missing: List[str],
    available: Dict[str, List[str]],
) -> Any:
    if not missing:
        return {}

    if len(missing) != 1:
        return _build_multi_parameter_error_page(
            server_name,
            function_name,
            missing,
            resolved.keys(),
            available,
        )

    remainder_segments = _remaining_path_segments(server_name)
    if not remainder_segments:
        return None

    nested_path = "/" + "/".join(remainder_segments)
    nested_value = _evaluate_nested_path_to_value(nested_path)
    if isinstance(nested_value, Response):
        return nested_value
    if nested_value is None:
        return None
    return {missing[0]: nested_value}


def _build_unsupported_signature_response(
    function_name: str, details: FunctionDetails
):
    payload = {
        "error": f"Unsupported {function_name}() signature for automatic request mapping",
        "reasons": details.unsupported_reasons,
        "resolution": (
            f"Use only standard positional or keyword parameters, or provide an explicit return outside {function_name}()."
        ),
    }
    response = jsonify(payload)
    response.status_code = 400
    return response


def _build_function_invocation_snippet(function_name: str, code: str) -> str:
    """Generate the code snippet that invokes a function with resolved parameters."""
    snippet = textwrap.dedent(
        f"""
        {AUTO_MAIN_RESULT_NAME} = {function_name}(**{AUTO_MAIN_PARAMS_NAME})
        return {AUTO_MAIN_RESULT_NAME}
        """
    ).strip()

    # Match the indentation of the original code
    base_indent = ""
    for line in code.splitlines():
        stripped = line.lstrip()
        if stripped:
            base_indent = line[: len(line) - len(stripped)]
            break

    if base_indent:
        snippet = textwrap.indent(snippet, base_indent)

    # Combine with original code
    combined = code.rstrip()
    if combined:
        return f"{combined}\n\n{snippet}\n"
    return f"{snippet}\n"


def _handle_missing_parameters_for_main(
    function_name: str,
    server_name: Optional[str],
    base_args: Dict[str, Any],
    details: FunctionDetails,
    resolved: Dict[str, Any],
    missing: List[str],
    available: Dict[str, List[str]],
) -> Tuple[Dict[str, Any], Dict[str, Any], List[str], Dict[str, List[str]], Optional[Response]]:
    """Try to resolve missing main() parameters via nested path evaluation.

    Returns (updated_args, resolved, missing, available, early_response) tuple.
    """
    injected = _inject_nested_parameter_value(
        server_name,
        function_name,
        resolved,
        missing,
        available,
    )

    if isinstance(injected, Response):
        return base_args, resolved, missing, available, injected

    if not injected:
        return base_args, resolved, missing, available, None

    # Re-resolve with the injected parameters
    working_args = dict(base_args)
    working_args.update(injected)
    new_resolved, new_missing, new_available = _resolve_function_parameters(
        details,
        working_args,
        allow_partial=True,
    )

    return working_args, new_resolved, new_missing, new_available, None


def _prepare_invocation(
    code: str,
    base_args: Dict[str, Any],
    *,
    function_name: Optional[str],
    allow_fallback: bool,
    server_name: Optional[str] = None,
) -> Any:
    """Prepare code and arguments for function invocation with parameter resolution."""
    if not function_name:
        return code, base_args

    details = _analyze_server_definition_for_function(code, function_name)
    if not details:
        return (code, base_args) if allow_fallback else None

    if details.unsupported_reasons:
        return _build_unsupported_signature_response(function_name, details)

    # Initial parameter resolution
    resolved, missing, available = _resolve_function_parameters(
        details, base_args, allow_partial=True
    )

    # Track working args (may be updated with injected parameters)
    working_args = dict(base_args)
    working_resolved = dict(resolved)

    # Handle missing parameters
    if missing:
        if function_name != "main":
            return _build_missing_parameter_response(
                function_name, MissingParameterError(missing, available)
            )

        # For main(), try nested path injection
        working_args, working_resolved, missing, available, early_response = _handle_missing_parameters_for_main(
            function_name, server_name, base_args, details, resolved, missing, available
        )

        if early_response:
            return early_response

        if missing:
            return _build_missing_parameter_response(
                function_name, MissingParameterError(missing, available)
            )

    # Build final code with function invocation
    new_args = dict(working_args)
    new_args[AUTO_MAIN_PARAMS_NAME] = working_resolved
    combined_code = _build_function_invocation_snippet(function_name, code)

    return combined_code, new_args


def model_as_dict(model_objects: Optional[Iterable[Any]]) -> Dict[str, Any]:
    """Convert SQLAlchemy model objects to a name->definition mapping."""
    if not model_objects:
        return {}

    result: Dict[str, Any] = {}
    for obj in model_objects:
        if not getattr(obj, "enabled", True):
            continue
        if hasattr(obj, "name") and hasattr(obj, "definition"):
            result[obj.name] = obj.definition
        else:
            result[str(obj)] = str(obj)
    return result


def _load_user_context() -> Dict[str, Dict[str, Any]]:
    user_id = _current_user_id()
    if not user_id:
        return {"variables": {}, "secrets": {}, "servers": {}}

    variables = model_as_dict(get_user_variables(user_id))
    if _should_skip_variable_prefetch():
        variables = dict(variables)
    else:
        variables = _resolve_variable_values(variables)
    secrets = model_as_dict(get_user_secrets(user_id))
    servers = model_as_dict(get_user_servers(user_id))
    return {"variables": variables, "secrets": secrets, "servers": servers}


def build_request_args() -> Dict[str, Any]:
    """Build the argument payload supplied to user-defined server code."""
    return {
        "request": request_details(),
        "context": _load_user_context(),
    }


def _execute_server_code_common(
    code: str,
    server_name: str,
    debug_prefix: str,
    error_suffix: str,
    *,
    function_name: Optional[str] = "main",
    allow_fallback: bool = True,
) -> Optional[Response]:
    args = build_request_args()

    prepared = _prepare_invocation(
        code,
        args,
        function_name=function_name,
        allow_fallback=allow_fallback,
        server_name=server_name,
    )
    if prepared is None:
        return None

    if isinstance(prepared, tuple):
        code_to_run, args_to_use = prepared
    else:
        return prepared

    try:
        result = run_text_function(code_to_run, args_to_use)
        if isinstance(result, dict):
            output = result.get("output", "")
            content_type = result.get("content_type", "text/html")
        elif isinstance(result, tuple) and len(result) == 2:
            output, content_type = result
        else:
            output = result
            content_type = "text/html"
        _log_server_output(debug_prefix, error_suffix, output, content_type)
        return _handle_successful_execution(output, content_type, server_name)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        # Top-level exception handler for all user code execution errors
        return _handle_execution_exception(exc, code, args, server_name)


@logfire.instrument("server_execution.execute_server_code({server=}, {server_name=})", extract_args=True, record_return=True)
def execute_server_code(server: Any, server_name: str) -> Optional[Response]:
    """Execute server code and return a redirect to the resulting CID."""
    return _execute_server_code_common(
        server.definition,
        server_name,
        "execute_server_code",
        "",
        function_name="main",
        allow_fallback=True,
    )


@logfire.instrument("server_execution.execute_server_code_from_definition({definition_text=}, {server_name=})", extract_args=True, record_return=True)
def execute_server_code_from_definition(definition_text: str, server_name: str) -> Optional[Response]:
    """Execute server code from a supplied historical definition."""
    return _execute_server_code_common(
        definition_text,
        server_name,
        "execute_server_code_from_definition",
        "in _from_definition",
        function_name="main",
        allow_fallback=True,
    )


@logfire.instrument("server_execution.execute_server_function({server=}, {server_name=}, {function_name=})", extract_args=True, record_return=True)
def execute_server_function(server: Any, server_name: str, function_name: str) -> Optional[Response]:
    """Execute a named helper function within a server definition."""

    return _execute_server_code_common(
        server.definition,
        server_name,
        "execute_server_function",
        f" for {function_name}",
        function_name=function_name,
        allow_fallback=False,
    )


@logfire.instrument("server_execution.execute_server_function_from_definition({definition_text=}, {server_name=}, {function_name=})", extract_args=True, record_return=True)
def execute_server_function_from_definition(
    definition_text: str, server_name: str, function_name: str
) -> Optional[Response]:
    """Execute a helper function from a supplied historical definition."""

    return _execute_server_code_common(
        definition_text,
        server_name,
        "execute_server_function_from_definition",
        f" in _from_definition for {function_name}",
        function_name=function_name,
        allow_fallback=False,
    )
