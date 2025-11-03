"""Helper functions for executing user-defined servers."""

import ast
import json
import textwrap
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlsplit

import logfire
from flask import (
    Response,
    current_app,
    has_app_context,
    has_request_context,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from alias_routing import find_matching_alias
from cid_presenter import cid_path, format_cid
from cid_utils import (
    generate_cid,
    get_current_secret_definitions_cid,
    get_current_server_definitions_cid,
    get_current_variable_definitions_cid,
    get_extension_from_mime_type,
)
from db_access import (
    ServerInvocationInput,
    create_cid_record,
    create_server_invocation,
    get_cid_by_path,
    get_server_by_name,
    get_user_secrets,
    get_user_servers,
    get_user_variables,
    save_entity,
)
from identity import current_user
from models import ServerInvocation
from syntax_highlighting import highlight_source
from text_function_runner import run_text_function

AUTO_MAIN_PARAMS_NAME = "__viewer_auto_main_params__"
AUTO_MAIN_RESULT_NAME = "__viewer_auto_main_result__"

VARIABLE_PREFETCH_SESSION_KEY = "__viewer_variable_prefetch__"
_MAX_VARIABLE_REDIRECTS = 5
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}


def _normalize_variable_path(value: Any) -> Optional[str]:
    """Normalize a variable value to an absolute path, or return None if invalid."""
    if not isinstance(value, str):
        return None

    trimmed = value.strip()
    return trimmed if trimmed.startswith("/") else None


def _should_skip_variable_prefetch() -> bool:
    """Check if we should skip variable prefetching (to prevent recursive fetching)."""
    if not has_request_context():
        return False

    try:
        return bool(session.get(VARIABLE_PREFETCH_SESSION_KEY))
    except Exception:
        return False


def _resolve_redirect_target(location: str, current_path: str) -> Optional[str]:
    """Resolve a redirect Location header to an absolute path, or None if external."""
    if not location:
        return None

    parsed = urlsplit(location)
    # Reject external redirects
    if parsed.scheme or parsed.netloc:
        return None

    candidate = parsed.path or ""
    if not candidate:
        return None

    # Make relative paths absolute
    if not candidate.startswith("/"):
        candidate = urljoin(current_path, candidate)

    # Preserve query string
    if parsed.query:
        candidate = f"{candidate}?{parsed.query}"

    return candidate


def _current_user_id() -> Optional[Any]:
    """Extract the current user ID, handling callable and non-callable forms."""
    user_id = getattr(current_user, "id", None)
    if callable(user_id):
        try:
            user_id = user_id()
        except TypeError:
            user_id = None

    if user_id:
        return user_id

    # Fallback to get_id() method
    getter = getattr(current_user, "get_id", None)
    return getter() if callable(getter) else None


def _fetch_variable_via_client(client: Any, start_path: str) -> Optional[str]:
    """Fetch content from a path via test client, following redirects up to a limit."""
    visited: set[str] = set()
    target = start_path

    for _ in range(_MAX_VARIABLE_REDIRECTS):
        if target in visited:
            break  # Prevent redirect loops
        visited.add(target)

        response = client.get(target, follow_redirects=False)
        status = getattr(response, "status_code", None) or 0

        if status in _REDIRECT_STATUSES:
            next_target = _resolve_redirect_target(
                response.headers.get("Location", ""), target
            )
            if not next_target:
                break
            target = next_target
            continue

        if status != 200:
            break

        try:
            return response.get_data(as_text=True)
        except Exception:
            return None

    return None


def _fetch_variable_content(path: str) -> Optional[str]:
    """Fetch the content at a path by executing it as the current user."""
    normalized = _normalize_variable_path(path)
    if not normalized or not has_app_context():
        return None

    # Avoid infinite recursion by not fetching the current request path
    if has_request_context() and normalized == request.path:
        return None

    user_id = _current_user_id()
    if not user_id:
        return None

    client = current_app.test_client()
    try:
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user_id)
            sess["_fresh"] = True
            sess[VARIABLE_PREFETCH_SESSION_KEY] = True

        return _fetch_variable_via_client(client, normalized)
    except Exception:
        return None
    finally:
        try:
            with client.session_transaction() as sess:
                sess.pop(VARIABLE_PREFETCH_SESSION_KEY, None)
        except Exception:
            pass

    return None


def _resolve_variable_values(variable_map: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve variable values, prefetching paths that look like server references."""
    if not variable_map:
        return {}

    if _should_skip_variable_prefetch():
        return dict(variable_map)

    resolved: Dict[str, Any] = {}
    for name, value in variable_map.items():
        candidate = _normalize_variable_path(value)
        if candidate:
            fetched = _fetch_variable_content(candidate)
            if fetched is not None:
                resolved[name] = fetched
                continue

        resolved[name] = value

    return resolved


@dataclass
class FunctionDetails:
    """Extracted metadata about an auto-invoked function."""

    parameter_order: List[str]
    required_parameters: List[str]
    optional_parameters: List[str]
    unsupported_reasons: List[str]


class _FunctionAnalyzer(ast.NodeVisitor):
    """Inspect a wrapped server definition for function compatibility."""

    def __init__(self, target_name: str):
        self.function_depth = 0
        self.target_name = target_name
        self.target_node: Optional[ast.FunctionDef] = None
        self.has_outer_return = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # pragma: no cover - exercised indirectly
        self.function_depth += 1
        try:
            if self.function_depth == 2 and node.name == self.target_name:
                self.target_node = node
            self.generic_visit(node)
        finally:
            self.function_depth -= 1

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Return(self, node: ast.Return) -> None:  # pragma: no cover - exercised indirectly
        if self.function_depth == 1:
            self.has_outer_return = True
        self.generic_visit(node)


class MissingParameterError(Exception):
    """Raised when a required parameter cannot be resolved from the request."""

    def __init__(self, missing: List[str], available: Dict[str, List[str]]):
        message = ", ".join(sorted(missing))
        super().__init__(f"Missing required parameters: {message}")
        self.missing = missing
        self.available = available


def _parse_function_details(node: ast.FunctionDef) -> FunctionDetails:
    positional = [arg.arg for arg in node.args.args]
    defaults = list(node.args.defaults) if node.args.defaults else []
    num_required = len(positional) - len(defaults)
    required_params = positional[:num_required]
    optional_params = positional[num_required:]

    kwonly_args = [arg.arg for arg in node.args.kwonlyargs]
    kw_defaults = node.args.kw_defaults or []
    for index, arg in enumerate(kwonly_args):
        default_value = kw_defaults[index] if index < len(kw_defaults) else None
        if default_value is None:
            required_params.append(arg)
        else:
            optional_params.append(arg)

    parameter_order = positional + kwonly_args

    unsupported: List[str] = []
    if getattr(node.args, "posonlyargs", []):
        unsupported.append("positional-only parameters are not supported")
    if node.args.vararg is not None:
        unsupported.append("var positional parameters (*args) are not supported")
    if node.args.kwarg is not None:
        unsupported.append("arbitrary keyword parameters (**kwargs) are not supported")

    return FunctionDetails(
        parameter_order=parameter_order,
        required_parameters=required_params,
        optional_parameters=optional_params,
        unsupported_reasons=unsupported,
    )


def _analyze_server_definition_for_function(
    code: str, function_name: str
) -> Optional[FunctionDetails]:
    wrapper_src = "def __viewer_wrapper__():\n" + textwrap.indent(code, "    ")
    try:
        tree = ast.parse(wrapper_src)
    except SyntaxError:
        return None

    wrapper_fn = tree.body[0]
    if not isinstance(wrapper_fn, ast.FunctionDef):  # pragma: no cover - defensive
        return None

    analyzer = _FunctionAnalyzer(function_name)
    analyzer.visit(wrapper_fn)

    if analyzer.target_node is None or analyzer.has_outer_return:
        return None

    return _parse_function_details(analyzer.target_node)


def describe_function_parameters(
    code: str, function_name: str
) -> Optional[Dict[str, Any]]:
    """Return a simplified description of function parameters for UI helpers."""

    details = _analyze_server_definition_for_function(code or "", function_name)
    if not details or details.unsupported_reasons:
        return None

    required = set(details.required_parameters)
    parameters = [
        {"name": name, "required": name in required}
        for name in details.parameter_order
    ]

    return {
        "parameters": parameters,
        "required_parameters": details.required_parameters,
        "optional_parameters": details.optional_parameters,
    }


def describe_main_function_parameters(code: str) -> Optional[Dict[str, Any]]:
    """Return a simplified description of ``main`` parameters for UI helpers."""

    return describe_function_parameters(code, "main")


def analyze_server_definition(code: str) -> Dict[str, Any]:
    """Inspect a server definition and summarise auto main compatibility."""

    result: Dict[str, Any] = {
        "is_valid": True,
        "errors": [],
        "auto_main": False,
        "auto_main_errors": [],
        "parameters": [],
        "has_main": False,
        "mode": "query",
    }

    try:
        ast.parse(code or "", mode="exec")
    except SyntaxError as exc:
        result["is_valid"] = False
        message = exc.msg or "Invalid syntax"
        error_info = {
            "message": message,
            "line": exc.lineno,
            "column": exc.offset,
        }
        if isinstance(exc.text, str):
            error_info["text"] = exc.text.strip()
        result["errors"].append(error_info)
        return result

    details = _analyze_server_definition_for_function(code or "", "main")
    if details is None:
        return result

    result["has_main"] = True
    if details.unsupported_reasons:
        result["auto_main_errors"] = list(details.unsupported_reasons)
        return result

    result["auto_main"] = True
    result["parameters"] = [
        {"name": name, "required": name in set(details.required_parameters)}
        for name in details.parameter_order
    ]
    result["mode"] = "main"
    return result


def _extract_request_body_values() -> Dict[str, Any]:
    body: Dict[str, Any] = {}

    try:
        json_payload = request.get_json(silent=True)
    except Exception:  # pragma: no cover - defensive
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
        "headers": sorted({k for k in request.headers.keys()}),
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
):
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
        except Exception as exc:
            return _handle_execution_exception(exc, code_to_run, args_to_use, server_name)

        output, _ = _normalize_execution_result(result)
        output_bytes = _encode_output(output)
        try:
            return output_bytes.decode("utf-8")
        except Exception:
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
                except Exception:
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
) -> Tuple[Dict[str, Any], List[str], Dict[str, List[str]], Optional[Response]]:
    """Try to resolve missing main() parameters via nested path evaluation.

    Returns (resolved, missing, available, early_response) tuple.
    """
    injected = _inject_nested_parameter_value(
        server_name,
        function_name,
        resolved,
        missing,
        available,
    )

    if isinstance(injected, Response):
        return resolved, missing, available, injected

    if not injected:
        return resolved, missing, available, None

    # Re-resolve with the injected parameters
    working_args = dict(base_args)
    working_args.update(injected)
    new_resolved, new_missing, new_available = _resolve_function_parameters(
        details,
        working_args,
        allow_partial=True,
    )

    return new_resolved, new_missing, new_available, None


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

    # Handle missing parameters
    if missing:
        if function_name != "main":
            return _build_missing_parameter_response(
                function_name, MissingParameterError(missing, available)
            )

        # For main(), try nested path injection
        resolved, missing, available, early_response = _handle_missing_parameters_for_main(
            function_name, server_name, base_args, details, resolved, missing, available
        )

        if early_response:
            return early_response

        if missing:
            return _build_missing_parameter_response(
                function_name, MissingParameterError(missing, available)
            )

    # Build final code with function invocation
    new_args = dict(base_args)
    new_args[AUTO_MAIN_PARAMS_NAME] = resolved
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


def request_details() -> Dict[str, Any]:
    """Collect request details for server execution context."""
    return {
        "path": request.path,
        "query_string": request.query_string.decode("utf-8"),
        "remote_addr": request.remote_addr,
        "user_agent": request.user_agent.string,
        "headers": {k: v for k, v in request.headers if k.lower() != "cookie"},
        "form_data": dict(request.form) if request.form else {},
        "args": dict(request.args) if request.args else {},
        "endpoint": request.endpoint,
        "scheme": request.scheme,
        "host": request.host,
        "method": request.method,
    }


def _load_user_context() -> Dict[str, Dict[str, Any]]:
    user_id = getattr(current_user, "id", None)
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


def create_server_invocation_record(user_id: str, server_name: str, result_cid: str) -> Optional[ServerInvocation]:
    """Create a ServerInvocation record and persist related metadata."""
    servers_cid = get_current_server_definitions_cid(user_id)
    variables_cid = get_current_variable_definitions_cid(user_id)
    secrets_cid = get_current_secret_definitions_cid(user_id)

    try:
        req_json = json.dumps(request_details(), indent=2, sort_keys=True)
        req_bytes = req_json.encode("utf-8")
        req_cid_value = format_cid(generate_cid(req_bytes))
        req_cid_path = cid_path(req_cid_value)
        if req_cid_path and not get_cid_by_path(req_cid_path):
            create_cid_record(req_cid_value, req_bytes, user_id)
        req_cid = req_cid_value if req_cid_path else None
    except Exception:
        req_cid = None

    invocation = create_server_invocation(
        user_id,
        server_name,
        result_cid,
        ServerInvocationInput(
            servers_cid=servers_cid,
            variables_cid=variables_cid,
            secrets_cid=secrets_cid,
            request_details_cid=req_cid,
        ),
    )

    try:
        inv_payload = {
            "user_id": user_id,
            "server_name": server_name,
            "result_cid": result_cid,
            "servers_cid": servers_cid,
            "variables_cid": variables_cid,
            "secrets_cid": secrets_cid,
            "request_details_cid": req_cid,
            "invoked_at": invocation.invoked_at.isoformat() if invocation.invoked_at else None,
        }
        inv_json = json.dumps(inv_payload, indent=2, sort_keys=True)
        inv_bytes = inv_json.encode("utf-8")
        inv_cid_value = format_cid(generate_cid(inv_bytes))
        inv_cid_path = cid_path(inv_cid_value)
        if inv_cid_path and not get_cid_by_path(inv_cid_path):
            create_cid_record(inv_cid_value, inv_bytes, user_id)

        invocation.invocation_cid = inv_cid_value if inv_cid_path else None
        save_entity(invocation)
    except Exception:
        pass

    return invocation


def _encode_output(output: Any) -> bytes:
    if isinstance(output, bytes):
        return output
    if isinstance(output, str):
        return output.encode("utf-8")
    # Dicts -> JSON for human-friendly output instead of concatenated keys
    if isinstance(output, dict):
        try:
            return json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        except Exception:
            return str(output).encode("utf-8")
    # If it's an iterable, try to handle common patterns gracefully
    try:
        from collections.abc import Iterable as _Iterable  # local import to avoid top changes
        if isinstance(output, _Iterable):
            items = list(output)
            # If elements look JSON-serializable (e.g., list of dicts), prefer JSON
            try:
                if items and any(isinstance(x, (dict, list, tuple)) for x in items):
                    return json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
            except Exception as json_err:
                print(f"[server_execution] JSON encoding attempt failed: {type(json_err).__name__}: {json_err}")
                print(f"[server_execution] Output type: {type(output).__name__}")
                print(f"[server_execution] Items types: {[type(x).__name__ for x in items[:5]]}...")
                traceback.print_exc()
                # Continue to try other encodings
            # List of ints -> bytes directly
            if all(isinstance(x, int) for x in items):
                return bytes(items)
            # List of bytes -> concatenate
            if all(isinstance(x, bytes) for x in items):
                return b"".join(items)
            # List of strings -> join then encode
            if all(isinstance(x, str) for x in items):
                return "".join(items).encode("utf-8")
    except Exception:
        # fall back below
        pass

    # Fallback: encode the string representation
    return str(output).encode("utf-8")


def _log_server_output(debug_prefix: str, error_suffix: str, output: Any, content_type: str) -> None:
    """Log execution details while tolerating logging failures."""
    try:
        sample = repr(output)
        if sample and len(sample) > 300:
            sample = sample[:300] + "…"
        print(
            f"[server_execution] {debug_prefix}: output_type={type(output).__name__}, "
            f"content_type={content_type}, sample={sample}"
        )
    except Exception as debug_err:
        suffix = f" {error_suffix}" if error_suffix else ""
        print(
            f"[server_execution] Debug output failed{suffix}: "
            f"{type(debug_err).__name__}: {debug_err}"
        )
        traceback.print_exc()


def _handle_successful_execution(output: Any, content_type: str, server_name: str) -> Response:
    output_bytes = _encode_output(output)
    cid_value = format_cid(generate_cid(output_bytes))

    cid_record_path = cid_path(cid_value)
    existing = get_cid_by_path(cid_record_path) if cid_record_path else None
    if not existing and cid_record_path:
        create_cid_record(cid_value, output_bytes, current_user.id)

    create_server_invocation_record(current_user.id, server_name, cid_value)

    extension = get_extension_from_mime_type(content_type)
    if extension and cid_record_path:
        redirect_path = cid_path(cid_value, extension)
        if redirect_path:
            return redirect(redirect_path)
    if cid_record_path:
        return redirect(cid_record_path)
    return redirect('/')


def _render_execution_error_html(
    exc: Exception,
    code: str,
    args: Dict[str, Any],
    server_name: Optional[str],
) -> str:
    """Render an HTML error page for exceptions raised during server execution."""

    from routes.core import _build_stack_trace, _extract_exception

    exception = _extract_exception(exc)
    exception_type = type(exception).__name__
    raw_message = str(exception)
    message = raw_message if raw_message else "No error message available"
    stack_trace = _build_stack_trace(exc)

    code_text = code if isinstance(code, str) else ""
    highlighted_code = None
    syntax_css = None
    if code_text:
        highlighted_code, syntax_css = highlight_source(
            code_text,
            filename=f"{server_name or 'server'}.py",
            fallback_lexer="python",
        )

    server_definition_url: Optional[str]
    if server_name:
        try:
            server_definition_url = url_for("main.view_server", server_name=server_name)
        except Exception:
            server_definition_url = None
    else:
        server_definition_url = None

    def _stringify(value: Any) -> str:
        try:
            return str(value)
        except Exception:
            return repr(value)

    try:
        args_json = json.dumps(
            args,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=_stringify,
        )
    except Exception:
        args_json = _stringify(args)

    return render_template(
        "500.html",
        stack_trace=stack_trace,
        exception_type=exception_type,
        exception_message=message,
        highlighted_server_code=highlighted_code,
        server_definition=code_text,
        syntax_css=syntax_css,
        server_args_json=args_json,
        server_name=server_name,
        server_definition_url=server_definition_url,
    )


def _handle_execution_exception(
    exc: Exception, code: str, args: Dict[str, Any], server_name: Optional[str]
) -> Response:
    try:
        html_content = _render_execution_error_html(exc, code, args, server_name)
        response = make_response(html_content)
        response.headers["Content-Type"] = "text/html; charset=utf-8"
    except Exception:
        text = (
            str(exc)
            + "\n\n"
            + traceback.format_exc()
            + "\n\n"
            + code
            + "\n\n"
            + str(args)
        )
        response = make_response(text)
        response.headers["Content-Type"] = "text/plain"

    response.status_code = 500
    return response


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
    except Exception as exc:
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


def is_potential_versioned_server_path(path: str, existing_routes: Iterable[str]) -> bool:
    """Return True if path could represent /{server}/{partial_cid}[/function]."""
    if not path or not path.startswith("/"):
        return False
    parts = [segment for segment in path.split("/") if segment]
    if len(parts) not in {2, 3}:
        return False
    if f"/{parts[0]}" in existing_routes:
        return False
    return True


def try_server_execution_with_partial(
    path: str,
    history_fetcher: Callable[[str, str], Iterable[Dict[str, Any]]],
) -> Optional[Any]:
    """Execute a server version referenced by a partial CID."""
    parts = [segment for segment in path.split("/") if segment]
    if len(parts) not in {2, 3}:
        return None
    server_name, partial = parts[0], parts[1]
    function_name = parts[2] if len(parts) == 3 else None

    server = get_server_by_name(current_user.id, server_name)
    if server and not getattr(server, "enabled", True):
        server = None
    if not server:
        return None

    history = history_fetcher(current_user.id, server_name)
    matches = [h for h in history if h.get("definition_cid", "").startswith(partial)]

    if not matches:
        return render_template("404.html", path=path), 404

    if len(matches) > 1:
        payload = {
            "error": "Multiple matching server versions",
            "server": server_name,
            "partial": partial,
            "matches": [
                {
                    "definition_cid": m.get("definition_cid"),
                    "snapshot_cid": m.get("snapshot_cid"),
                    "created_at": m.get("created_at").isoformat() if m.get("created_at") else None,
                }
                for m in matches
            ],
        }
        return jsonify(payload), 400

    definition_text = matches[0].get("definition", "")
    if function_name:
        return execute_server_function_from_definition(
            definition_text, server_name, function_name
        )
    return execute_server_code_from_definition(definition_text, server_name)


def is_potential_server_path(path: str, existing_routes: Iterable[str]) -> bool:
    """Return True if path could map to a server name or helper function."""

    if not path or not path.startswith("/"):
        return False

    if path in existing_routes:
        return False

    parts = [segment for segment in path.split("/") if segment]
    if not parts:
        return False

    if f"/{parts[0]}" in existing_routes:
        return False

    return True


def try_server_execution(path: str) -> Optional[Response]:
    """Execute the server whose name matches the request path."""
    parts = [segment for segment in path.split("/") if segment]
    if not parts:
        return None

    server_name = parts[0]
    server = get_server_by_name(current_user.id, server_name)
    if server and not getattr(server, "enabled", True):
        server = None
    if not server:
        return None

    if len(parts) == 1:
        return execute_server_code(server, server_name)

    if len(parts) > 2:
        return execute_server_code(server, server_name)

    function_name = parts[1]
    if not function_name.isidentifier():
        return execute_server_code(server, server_name)

    result = execute_server_function(server, server_name, function_name)
    if result is None:
        if _auto_main_accepts_additional_path(server):
            return execute_server_code(server, server_name)
        return None

    return result
